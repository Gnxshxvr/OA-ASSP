"""Selector generalization experiments on already-recorded benchmark data.

Two protocols, both using only recorded solver runtimes (no new benchmarking):

* **Leave-one-cell-out (LOCO).** A *cell* is ``(graph_family, V, target_D)``. Each
  fold trains on every graph outside one cell and evaluates on the two graphs of that
  held-out cell. This measures whether the selector has learned structural
  relationships or only the identity of generator configurations.
* **Leave-one-family-out (LOOF).** Each fold trains on two graph families and is
  evaluated on the third.

For every fold the following are reported: exact accuracy, near-best accuracy
(within ``epsilon`` of the per-instance oracle), the majority-label accuracy computed
on the same held-out queries (the "learns nothing" reference), the training-derived
SBS policy, and the solver-only capture rate on the held-out graphs.
"""

from __future__ import annotations
import csv
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from oa_assp.benchmark.oracle import OracleInstance
from oa_assp.features.extractor import FeatureExtractor
from oa_assp.features.schema import get_feature_names_for_tier
from oa_assp.graphs.base import Graph
from oa_assp.graphs.queries import Query
from oa_assp.selector.decision_tree import DecisionTreeSelector, _solver_cost_for_prediction
from oa_assp.selector.baselines import MajorityPolicySelector

GAP_EPSILON = 1e-12


@dataclass
class FoldResult:
    """Result of a single generalization fold."""

    protocol: str
    tier: int
    feature_count: int
    fold: str
    held_out_graph_ids: str
    train_graph_ids: str
    num_train_instances: int
    num_test_instances: int

    exact_accuracy: float
    near_best_accuracy: float
    majority_label: str
    majority_exact_accuracy: float
    majority_near_best_accuracy: float
    accuracy_lift_over_majority: float

    train_sbs_policy: str
    test_sbs_cost: float
    test_vbs_cost: float
    oracle_gap: float
    predicted_solver_cost: float
    solver_only_capture: float
    predicted_distribution: str
    held_out_label_distribution: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_instance_records(
    graphs: Dict[str, Graph],
    queries_by_graph: Dict[str, List[Query]],
    oracle_map: Dict[Tuple[str, str], OracleInstance],
    tier: int,
    feature_names: Sequence[str],
) -> List[Dict[str, Any]]:
    """Extract features once for every query and attach its oracle instance."""
    extractor = FeatureExtractor(default_tier=tier)
    records: List[Dict[str, Any]] = []

    for gid, graph in graphs.items():
        g_features, g_time = extractor.extract_graph_features(graph, tier=tier)
        meta = graph.metadata
        for q in queries_by_graph.get(gid, []):
            key = (gid, q.query_id)
            inst = oracle_map.get(key)
            if inst is None or inst.vbs_algorithm == "none":
                continue
            q_features, q_time = extractor.extract_query_features(graph, q, tier=tier)
            combined = dict(g_features)
            combined.update(q_features)
            records.append({
                "graph_id": gid,
                "query_id": q.query_id,
                "family": str(meta.get("graph_family", "unknown")),
                "V": int(graph.num_nodes),
                "target_D": float(meta.get("target_average_degree", 0.0)),
                "features": [float(combined.get(name, 0.0)) for name in feature_names],
                "y": inst.vbs_algorithm,
                "oracle_instance": inst,
                "graph_feature_time": g_time,
                "query_feature_time": q_time,
            })
    return records


def make_cells(records: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, int, float], List[str]]:
    """Group graph IDs by (family, V, target_D)."""
    cells: Dict[Tuple[str, int, float], List[str]] = {}
    for r in records:
        key = (str(r["family"]), int(r["V"]), float(r["target_D"]))
        gid = str(r["graph_id"])
        if gid not in cells.setdefault(key, []):
            cells[key].append(gid)
    return {k: sorted(v) for k, v in cells.items()}


def _evaluate_fold(
    protocol: str,
    fold_name: str,
    train_records: List[Dict[str, Any]],
    test_records: List[Dict[str, Any]],
    feature_names: Sequence[str],
    hyperparams: Dict[str, Any],
    epsilon: float,
    tier: int = -1,
) -> FoldResult:
    if not train_records or not test_records:
        raise ValueError(f"Fold {fold_name} has empty train or test records.")

    X_tr = np.array([r["features"] for r in train_records], dtype=float)
    y_tr = [str(r["y"]) for r in train_records]
    X_te = np.array([r["features"] for r in test_records], dtype=float)

    selector = DecisionTreeSelector(
        max_depth=int(hyperparams.get("max_depth", 4)),
        min_samples_leaf=int(hyperparams.get("min_samples_leaf", 3)),
        random_state=int(hyperparams.get("random_state", 42)),
        criterion=str(hyperparams.get("criterion", "gini")),
    )
    selector.fit_arrays(X_tr, y_tr, list(feature_names))
    preds, _ = selector.predict(X_te)

    majority = MajorityPolicySelector().fit_labels(y_tr)

    # Training-derived SBS policy for this fold.
    train_policy_totals = {
        "Always-Dijkstra": 0.0,
        "Always-Bidirectional-Dijkstra": 0.0,
        "Always-A*": 0.0,
    }
    for r in train_records:
        inst: OracleInstance = r["oracle_instance"]
        train_policy_totals["Always-Dijkstra"] += inst.always_dijkstra_cost
        train_policy_totals["Always-Bidirectional-Dijkstra"] += inst.always_bidi_cost
        train_policy_totals["Always-A*"] += inst.always_astar_cost
    sbs_policy = min(train_policy_totals, key=train_policy_totals.get)

    def _sbs_cost(inst: OracleInstance) -> float:
        if sbs_policy == "Always-Dijkstra":
            return inst.always_dijkstra_cost
        if sbs_policy == "Always-Bidirectional-Dijkstra":
            return inst.always_bidi_cost
        return inst.always_astar_cost

    exact = 0
    near = 0
    pred_cost = 0.0
    sbs_cost = 0.0
    vbs_cost = 0.0
    maj_exact = 0
    maj_near = 0
    label_dist: Dict[str, int] = {}
    pred_dist: Dict[str, int] = {}

    for i, r in enumerate(test_records):
        inst: OracleInstance = r["oracle_instance"]
        pred = str(preds[i])
        c = _solver_cost_for_prediction(pred, inst)
        pred_cost += c
        sbs_cost += _sbs_cost(inst)
        vbs_cost += inst.vbs_cost
        if pred == inst.vbs_algorithm:
            exact += 1
        if c <= (1.0 + epsilon) * inst.vbs_cost + 1e-12:
            near += 1

        maj = majority.policy or "Dijkstra"
        mc = _solver_cost_for_prediction(maj, inst)
        if maj == inst.vbs_algorithm:
            maj_exact += 1
        if mc <= (1.0 + epsilon) * inst.vbs_cost + 1e-12:
            maj_near += 1

        label_dist[str(r["y"])] = label_dist.get(str(r["y"]), 0) + 1
        pred_dist[pred] = pred_dist.get(pred, 0) + 1

    n = len(test_records)
    gap = sbs_cost - vbs_cost
    capture = (sbs_cost - pred_cost) / gap if gap > GAP_EPSILON else math.nan

    return FoldResult(
        protocol=protocol,
        tier=int(tier),
        feature_count=len(feature_names),
        fold=fold_name,
        held_out_graph_ids="|".join(sorted({str(r["graph_id"]) for r in test_records})),
        train_graph_ids="|".join(sorted({str(r["graph_id"]) for r in train_records})),
        num_train_instances=len(train_records),
        num_test_instances=n,
        exact_accuracy=exact / n,
        near_best_accuracy=near / n,
        majority_label=str(majority.policy),
        majority_exact_accuracy=maj_exact / n,
        majority_near_best_accuracy=maj_near / n,
        accuracy_lift_over_majority=(exact - maj_exact) / n,
        train_sbs_policy=sbs_policy,
        test_sbs_cost=sbs_cost,
        test_vbs_cost=vbs_cost,
        oracle_gap=gap,
        predicted_solver_cost=pred_cost,
        solver_only_capture=capture,
        predicted_distribution=";".join(f"{k}={v}" for k, v in sorted(pred_dist.items())),
        held_out_label_distribution=";".join(f"{k}={v}" for k, v in sorted(label_dist.items())),
    )


def evaluate_standard_split(
    records: Sequence[Dict[str, Any]],
    train_graph_ids: Sequence[str],
    test_graph_ids: Sequence[str],
    feature_names: Sequence[str],
    hyperparams: Dict[str, Any],
    epsilon: float = 0.05,
    tier: int = -1,
) -> FoldResult:
    """Evaluate the frozen 32/8 held-out split with the same metric set as the folds."""
    train_set = set(str(g) for g in train_graph_ids)
    test_set = set(str(g) for g in test_graph_ids)
    if train_set & test_set:
        raise ValueError(f"Train/test graph overlap: {sorted(train_set & test_set)}")
    train_records = [r for r in records if str(r["graph_id"]) in train_set]
    test_records = [r for r in records if str(r["graph_id"]) in test_set]
    return _evaluate_fold(
        protocol="standard_held_out",
        fold_name="train32_test8",
        train_records=train_records,
        test_records=test_records,
        feature_names=feature_names,
        hyperparams=hyperparams,
        epsilon=epsilon,
        tier=tier,
    )


def leave_one_cell_out(
    records: Sequence[Dict[str, Any]],
    feature_names: Sequence[str],
    hyperparams: Dict[str, Any],
    epsilon: float = 0.05,
    tier: int = -1,
) -> List[FoldResult]:
    """Train on all cells but one; evaluate on the held-out cell."""
    cells = make_cells(records)
    results: List[FoldResult] = []
    for (family, V, D), held_ids in sorted(cells.items()):
        held = set(held_ids)
        train_records = [r for r in records if str(r["graph_id"]) not in held]
        test_records = [r for r in records if str(r["graph_id"]) in held]
        results.append(
            _evaluate_fold(
                protocol="leave_one_cell_out",
                fold_name=f"{family}_V{V}_D{int(D)}",
                train_records=train_records,
                test_records=test_records,
                feature_names=feature_names,
                hyperparams=hyperparams,
                epsilon=epsilon,
                tier=tier,
            )
        )
    return results


def leave_one_family_out(
    records: Sequence[Dict[str, Any]],
    feature_names: Sequence[str],
    hyperparams: Dict[str, Any],
    epsilon: float = 0.05,
    tier: int = -1,
) -> List[FoldResult]:
    """Train on two families; evaluate on the third."""
    families = sorted({str(r["family"]) for r in records})
    results: List[FoldResult] = []
    for fam in families:
        train_records = [r for r in records if str(r["family"]) != fam]
        test_records = [r for r in records if str(r["family"]) == fam]
        results.append(
            _evaluate_fold(
                protocol="leave_one_family_out",
                fold_name=fam,
                train_records=train_records,
                test_records=test_records,
                feature_names=feature_names,
                hyperparams=hyperparams,
                epsilon=epsilon,
                tier=tier,
            )
        )
    return results


def fold_results_to_csv(results: Sequence[FoldResult], output_path: Union[str, Path]) -> str:
    """Write fold results to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not results:
        return str(path)
    field_names = list(results[0].to_dict().keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())
    return str(path)
