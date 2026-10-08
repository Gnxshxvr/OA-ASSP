"""Validation-based selector hyperparameter selection.

The validation split exists to make exactly one decision: which selector
configuration to freeze before the single test evaluation. Nothing else may look at
the test split.

Objective (economic, not accuracy-based)
----------------------------------------
For each candidate configuration the selector is fitted on the training graphs and
applied to the validation graphs. The objective is the total **validation cost of the
decision**, i.e. the sum of the executed solver's cost for every validation query plus
a per-query selector-inference charge measured on the validation instances:

    objective(cfg) = sum_over_val_queries( cost(predicted solver) )
                     + n_val * median_single_row_inference_latency(cfg)

Including the inference latency keeps the selection honest: a deeper tree that buys a
little accuracy but costs more per query is not automatically preferred. Accuracy and
near-best rate are reported alongside so the trade-off is visible.

Ties are broken by (1) lower objective, (2) smaller depth, (3) fewer leaves.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from oa_assp.benchmark.oracle import OracleInstance
from oa_assp.selector.decision_tree import DecisionTreeSelector, _solver_cost_for_prediction

DEFAULT_GRID: List[Dict[str, Any]] = [
    {"criterion": "gini", "max_depth": d, "min_samples_leaf": leaf}
    for d in (2, 3, 4, 5, 6)
    for leaf in (1, 2, 3, 5, 10)
]

LATENCY_SAMPLE_SIZE = 200


@dataclass
class TuningRow:
    """One candidate configuration evaluated on the validation split."""

    criterion: str
    max_depth: int
    min_samples_leaf: int
    num_leaves: int
    tree_depth: int

    val_exact_accuracy: float
    val_near_best_accuracy: float
    val_solver_cost: float
    val_selection_latency: float
    val_objective: float
    is_selected: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _select_rows(
    records: Sequence[Dict[str, Any]], graph_ids: Sequence[str]
) -> List[Dict[str, Any]]:
    wanted = set(str(g) for g in graph_ids)
    return [r for r in records if str(r["graph_id"]) in wanted]


def select_hyperparameters(
    records: Sequence[Dict[str, Any]],
    train_graph_ids: Sequence[str],
    val_graph_ids: Sequence[str],
    feature_names: Sequence[str],
    grid: Optional[Sequence[Dict[str, Any]]] = None,
    epsilon: float = 0.05,
    random_state: int = 42,
    latency_sample_size: int = LATENCY_SAMPLE_SIZE,
) -> Tuple[Dict[str, Any], List[TuningRow]]:
    """Select selector hyperparameters using the validation split only.

    Returns the selected configuration and the full grid table for auditability.
    """
    if grid is None:
        grid = DEFAULT_GRID

    train_set = set(str(g) for g in train_graph_ids)
    val_set = set(str(g) for g in val_graph_ids)
    if train_set & val_set:
        raise ValueError(f"Train/validation graph overlap: {sorted(train_set & val_set)}")

    train_records = _select_rows(records, train_graph_ids)
    val_records = _select_rows(records, val_graph_ids)
    if not train_records or not val_records:
        raise ValueError("Hyperparameter selection requires non-empty train and validation sets.")

    X_tr = np.array([r["features"] for r in train_records], dtype=float)
    y_tr = [str(r["y"]) for r in train_records]
    X_va = np.array([r["features"] for r in val_records], dtype=float)

    rows: List[TuningRow] = []
    best: Optional[Tuple[Tuple[float, int, int], Dict[str, Any]]] = None

    sample_idx = list(range(min(latency_sample_size, len(val_records))))

    for cfg in grid:
        selector = DecisionTreeSelector(
            max_depth=int(cfg["max_depth"]),
            min_samples_leaf=int(cfg["min_samples_leaf"]),
            random_state=random_state,
            criterion=str(cfg.get("criterion", "gini")),
        )
        selector.fit_arrays(X_tr, y_tr, list(feature_names))
        preds, _ = selector.predict(X_va)

        solver_cost = 0.0
        exact = 0
        near = 0
        for i, r in enumerate(val_records):
            inst: OracleInstance = r["oracle_instance"]
            pred = str(preds[i])
            c = _solver_cost_for_prediction(pred, inst)
            solver_cost += c
            if pred == inst.vbs_algorithm:
                exact += 1
            if c <= (1.0 + epsilon) * inst.vbs_cost + 1e-12:
                near += 1

        # Measure single-row inference latency on a bounded validation sample.
        latencies = [
            selector.predict_one(X_va[i])[1] for i in sample_idx
        ]
        latency = float(np.median(latencies)) if latencies else 0.0

        objective = solver_cost + len(val_records) * latency
        n = len(val_records)

        tree = selector.model.tree_
        rows.append(
            TuningRow(
                criterion=str(cfg.get("criterion", "gini")),
                max_depth=int(cfg["max_depth"]),
                min_samples_leaf=int(cfg["min_samples_leaf"]),
                num_leaves=int(tree.n_leaves),
                tree_depth=int(tree.max_depth),
                val_exact_accuracy=exact / n,
                val_near_best_accuracy=near / n,
                val_solver_cost=solver_cost,
                val_selection_latency=latency,
                val_objective=objective,
                is_selected=False,
            )
        )

        key = (objective, int(cfg["max_depth"]), int(cfg["min_samples_leaf"]))
        if best is None or key < best[0]:
            best = (key, dict(cfg))

    assert best is not None
    selected = best[1]
    for row in rows:
        if (
            row.max_depth == int(selected["max_depth"])
            and row.min_samples_leaf == int(selected["min_samples_leaf"])
            and row.criterion == str(selected.get("criterion", "gini"))
        ):
            row.is_selected = True

    return selected, rows
