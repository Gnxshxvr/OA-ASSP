"""Feature-tier trade-off evaluation comparing Tier 0, Tier 0+1, and Tier 0+1+2."""

from __future__ import annotations
import csv
from dataclasses import dataclass, asdict
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from oa_assp.benchmark.oracle import OracleSummary
from oa_assp.graphs.base import Graph
from oa_assp.graphs.queries import Query
from oa_assp.selector.dataset import prepare_selector_dataset, SplitData
from oa_assp.selector.decision_tree import DecisionTreeSelector, SelectorEvaluationResult


@dataclass
class TierEvaluationSummary:
    """Summary of performance and cost metrics for a specific feature tier."""

    tier: int
    tier_name: str
    feature_count: int
    features_used: List[str]

    mean_graph_feature_time: float
    mean_query_feature_time: float
    mean_selection_time: float

    exact_accuracy: float
    near_best_accuracy: float

    total_solver_cost: float
    total_adaptive_cost: float
    total_sbs_cost: float
    total_vbs_cost: float
    gap_closed: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TierWorkloadSummary:
    """Summary of a specific feature tier at a specific workload Q."""

    tier: int
    tier_name: str
    feature_count: int
    Q: int

    feature_cost: float        # C_graph_feature (once per test graph) + sum(C_query_feature)
    selection_cost: float      # sum(C_selection)
    solver_cost: float         # sum(C_solver)
    total_adaptive_cost: float # feature_cost + selection_cost + solver_cost
    total_sbs_cost: float
    total_vbs_cost: float

    exact_accuracy: float
    near_best_accuracy: float
    gap_closed: float
    adaptive_ratio_to_sbs: float
    adaptive_minus_sbs: float
    break_even_status: str     # 'yes' if total_adaptive_cost < total_sbs_cost else 'not_observed'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_feature_tiers(
    graphs: Dict[str, Graph],
    queries_by_graph: Dict[str, List[Query]],
    oracle_summary: OracleSummary,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    tree_max_depth: int = 4,
    tree_min_samples_leaf: int = 2,
    epsilon: float = 0.05,
    q_checkpoints: Optional[List[int]] = None,
    split_data_tier1: Optional[SplitData] = None,
    eval_res_tier1: Optional[SelectorEvaluationResult] = None,
    train_graph_ids: Optional[List[str]] = None,
    val_graph_ids: Optional[List[str]] = None,
    test_graph_ids: Optional[List[str]] = None,
) -> Tuple[List[TierEvaluationSummary], List[TierWorkloadSummary]]:
    """Evaluate selector across Tier 0, Tier 0+1, and Tier 0+1+2 across Q checkpoints.

    Uses the exact same graph split and deterministic query sequence prefix across all tiers.
    Reuses authoritative Tier 1 dataset and evaluation results when provided to ensure cross-artifact consistency.
    """
    if q_checkpoints is None:
        q_checkpoints = [1, 10, 50, 100, 500]

    tier_configs = [
        (0, "Tier 0: O(1)"),
        (1, "Tier 0+1: O(V+E)"),
        (2, "Tier 0+1+2: Structural"),
    ]

    summaries: List[TierEvaluationSummary] = []
    workload_summaries: List[TierWorkloadSummary] = []

    for tier, name in tier_configs:
        if tier == 1 and split_data_tier1 is not None and eval_res_tier1 is not None:
            split_data = split_data_tier1
            eval_res = eval_res_tier1
        else:
            # Prepare dataset for tier using exact same split
            split_data = prepare_selector_dataset(
                graphs=graphs,
                queries_by_graph=queries_by_graph,
                oracle_summary=oracle_summary,
                tier=tier,
                train_ratio=train_ratio,
                val_ratio=val_ratio,
                test_ratio=test_ratio,
                seed=seed,
                stratified=True,
                train_graph_ids=train_graph_ids,
                val_graph_ids=val_graph_ids,
                test_graph_ids=test_graph_ids,
            )

            # Train selector
            selector = DecisionTreeSelector(
                max_depth=tree_max_depth,
                min_samples_leaf=tree_min_samples_leaf,
                random_state=seed,
            )
            selector.fit(split_data.train)

            # Evaluate on unseen test graphs
            eval_res = selector.evaluate(split_data.test, epsilon=epsilon)

        # Graph-level feature times for test graphs (paid ONCE per graph)
        g_feat_by_gid = {m["graph_id"]: m["graph_feature_time"] for m in split_data.test.metadata}
        tot_test_graph_feat = sum(g_feat_by_gid.values())

        # Group test query results by graph_id preserving deterministic prefix order
        by_test_graph: Dict[str, List[Any]] = {}
        for qr in eval_res.query_results:
            by_test_graph.setdefault(qr.graph_id, []).append(qr)

        oracle_map: Dict[Tuple[str, str], Any] = {
            (inst.graph_id, inst.query_id): inst for inst in oracle_summary.instances
        }

        # Evaluate across each Q in q_checkpoints
        for Q in q_checkpoints:
            q_queries = []
            for gid, qrs in by_test_graph.items():
                q_queries.extend(qrs[:min(Q, len(qrs))])

            if not q_queries:
                continue

            q_feat_cost = tot_test_graph_feat + sum(qr.query_feature_time for qr in q_queries)
            q_sel_cost = sum(qr.selection_time for qr in q_queries)
            q_solv_cost = sum(qr.selected_solver_runtime for qr in q_queries)
            q_adapt_cost = q_feat_cost + q_sel_cost + q_solv_cost

            q_sbs_cost = 0.0
            q_vbs_cost = 0.0
            for qr in q_queries:
                inst = oracle_map.get((qr.graph_id, qr.query_id))
                if inst is not None:
                    if oracle_summary.sbs_policy == "Always-Dijkstra":
                        q_sbs_cost += inst.always_dijkstra_cost
                    elif oracle_summary.sbs_policy == "Always-Bidirectional-Dijkstra":
                        q_sbs_cost += inst.always_bidi_cost
                    else:
                        q_sbs_cost += inst.always_astar_cost
                    q_vbs_cost += inst.vbs_cost

            exact_acc = float(sum(1 for qr in q_queries if qr.exact_correct) / len(q_queries))
            near_acc = float(sum(1 for qr in q_queries if qr.near_best) / len(q_queries))

            gap = q_sbs_cost - q_vbs_cost
            gap_closed = (q_sbs_cost - q_adapt_cost) / gap if abs(gap) > 1e-12 else math.nan
            diff = q_adapt_cost - q_sbs_cost
            ratio = (q_adapt_cost / q_sbs_cost) if q_sbs_cost > 0 else 1.0
            brk = "yes" if q_adapt_cost < q_sbs_cost else "not_observed"

            workload_summaries.append(
                TierWorkloadSummary(
                    tier=tier,
                    tier_name=name,
                    feature_count=len(split_data.all_feature_names),
                    Q=Q,
                    feature_cost=q_feat_cost,
                    selection_cost=q_sel_cost,
                    solver_cost=q_solv_cost,
                    total_adaptive_cost=q_adapt_cost,
                    total_sbs_cost=q_sbs_cost,
                    total_vbs_cost=q_vbs_cost,
                    exact_accuracy=exact_acc,
                    near_best_accuracy=near_acc,
                    gap_closed=gap_closed,
                    adaptive_ratio_to_sbs=ratio,
                    adaptive_minus_sbs=diff,
                    break_even_status=brk,
                )
            )

        # Overall summary across all test queries
        tot_solver = sum(qr.selected_solver_runtime for qr in eval_res.query_results)
        tot_sel = sum(qr.selection_time for qr in eval_res.query_results)
        tot_q_feat = sum(qr.query_feature_time for qr in eval_res.query_results)
        tot_adaptive = tot_test_graph_feat + tot_q_feat + tot_sel + tot_solver

        tot_sbs = 0.0
        tot_vbs = 0.0
        for qr in eval_res.query_results:
            inst = oracle_map.get((qr.graph_id, qr.query_id))
            if inst is not None:
                if oracle_summary.sbs_policy == "Always-Dijkstra":
                    tot_sbs += inst.always_dijkstra_cost
                elif oracle_summary.sbs_policy == "Always-Bidirectional-Dijkstra":
                    tot_sbs += inst.always_bidi_cost
                else:
                    tot_sbs += inst.always_astar_cost
                tot_vbs += inst.vbs_cost

        oracle_gap = tot_sbs - tot_vbs
        gap_closed = (tot_sbs - tot_adaptive) / oracle_gap if abs(oracle_gap) > 1e-12 else math.nan

        # Graph vs query feature timing breakdown
        g_feat_times = list(g_feat_by_gid.values())
        q_feat_times = [qr.query_feature_time for qr in eval_res.query_results]

        summary = TierEvaluationSummary(
            tier=tier,
            tier_name=name,
            feature_count=len(split_data.all_feature_names),
            features_used=split_data.all_feature_names,
            mean_graph_feature_time=float(sum(g_feat_times) / max(1, len(g_feat_times))),
            mean_query_feature_time=float(sum(q_feat_times) / max(1, len(q_feat_times))),
            mean_selection_time=eval_res.mean_selection_time,
            exact_accuracy=eval_res.exact_accuracy,
            near_best_accuracy=eval_res.near_best_accuracy,
            total_solver_cost=tot_solver,
            total_adaptive_cost=tot_adaptive,
            total_sbs_cost=tot_sbs,
            total_vbs_cost=tot_vbs,
            gap_closed=gap_closed,
        )
        summaries.append(summary)

    return summaries, workload_summaries


def save_feature_tier_results(
    summaries: List[TierEvaluationSummary],
    output_csv: Union[str, Path],
) -> str:
    """Save feature-tier trade-off evaluation results to CSV."""
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not summaries:
        return str(path)

    field_names = [
        "tier",
        "tier_name",
        "feature_count",
        "mean_graph_feature_time",
        "mean_query_feature_time",
        "mean_selection_time",
        "exact_accuracy",
        "near_best_accuracy",
        "total_solver_cost",
        "total_adaptive_cost",
        "total_sbs_cost",
        "total_vbs_cost",
        "gap_closed",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        for s in summaries:
            row = s.to_dict()
            # Remove features_used list for clean CSV
            row.pop("features_used", None)
            writer.writerow(row)

    return str(path)


def save_tier_workload_results(
    workload_summaries: List[TierWorkloadSummary],
    output_csv: Union[str, Path],
) -> str:
    """Save tier workload evaluation results across Q checkpoints to CSV."""
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not workload_summaries:
        return str(path)

    field_names = list(workload_summaries[0].to_dict().keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        for s in workload_summaries:
            writer.writerow(s.to_dict())

    return str(path)

