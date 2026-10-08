"""Query workload analysis and cumulative break-even crossover computation."""

from __future__ import annotations
import csv
from dataclasses import dataclass, asdict
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from oa_assp.benchmark.oracle import OracleInstance, OracleSummary
from oa_assp.selector.decision_tree import QuerySelectionResult


@dataclass
class WorkloadPoint:
    """Cumulative cost and evaluation metrics at a specific workload size Q."""

    graph_id: str
    Q: int
    effective_q: int

    C_Dijkstra: float
    C_Bidirectional: float
    C_Astar: float
    C_SBS: float
    C_Adaptive: float
    C_VBS: float

    C_graph_feature: float
    C_query_feature: float
    C_selection: float
    C_solver: float

    adaptive_minus_SBS: float
    adaptive_ratio_to_SBS: float
    gap_closed: float
    gap_status: str  # 'normal', 'zero_oracle_gap', 'negative_gap'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkloadAnalysisResult:
    """Aggregate and per-graph workload analysis results."""

    graph_points: List[WorkloadPoint]
    aggregate_points: Dict[int, Dict[str, float]]
    break_even_Q_per_graph: Dict[str, Optional[int]]
    aggregate_break_even_Q: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_points": self.aggregate_points,
            "break_even_Q_per_graph": self.break_even_Q_per_graph,
            "aggregate_break_even_Q": self.aggregate_break_even_Q,
            "num_graph_points": len(self.graph_points),
        }


def compute_workload_analysis(
    query_results: List[QuerySelectionResult],
    oracle_summary: OracleSummary,
    graph_feature_times: Dict[str, float],
    q_checkpoints: Optional[List[int]] = None,
) -> WorkloadAnalysisResult:
    """Compute cumulative workload curves across Q checkpoints.

    Parameters
    ----------
    query_results : List[QuerySelectionResult]
        Per-query selector predictions and runtimes.
    oracle_summary : OracleSummary
        Ground-truth oracles and SBS policy definition.
    graph_feature_times : Dict[str, float]
        One-time feature extraction wall-clock time for each graph.
    q_checkpoints : Optional[List[int]]
        Checkpoints for Q (default: [1, 10, 50, 100, 500]).
    """
    if q_checkpoints is None:
        q_checkpoints = [1, 10, 50, 100, 500]

    # Group query results by graph_id preserving sequence order
    by_graph: Dict[str, List[QuerySelectionResult]] = {}
    for r in query_results:
        by_graph.setdefault(r.graph_id, []).append(r)

    # Map oracle instances by (graph_id, query_id)
    oracle_map: Dict[Tuple[str, str], OracleInstance] = {
        (inst.graph_id, inst.query_id): inst for inst in oracle_summary.instances
    }

    graph_points: List[WorkloadPoint] = []
    break_even_per_graph: Dict[str, Optional[int]] = {}

    for gid, q_res_list in by_graph.items():
        g_feat_time = graph_feature_times.get(gid, 0.0)
        n_queries = len(q_res_list)
        first_break_even = None

        for Q in q_checkpoints:
            eff_q = min(Q, n_queries)
            if eff_q == 0:
                continue

            sub_queries = q_res_list[:eff_q]

            c_dijk = 0.0
            c_bidi = 0.0
            c_astar = 0.0
            c_sbs = 0.0
            c_vbs = 0.0

            c_query_feat = 0.0
            c_selection = 0.0
            c_solver = 0.0

            for q_res in sub_queries:
                inst = oracle_map.get((gid, q_res.query_id))
                if inst is not None:
                    c_dijk += inst.dijkstra_cost
                    c_bidi += inst.bidirectional_cost
                    c_astar += inst.always_astar_cost
                    if oracle_summary.sbs_policy == "Always-Dijkstra":
                        c_sbs += inst.always_dijkstra_cost
                    elif oracle_summary.sbs_policy == "Always-Bidirectional-Dijkstra":
                        c_sbs += inst.always_bidi_cost
                    else:
                        c_sbs += inst.always_astar_cost
                    c_vbs += inst.vbs_cost

                c_query_feat += q_res.feature_time
                c_selection += q_res.selection_time
                c_solver += q_res.selected_solver_runtime

            # Total adaptive cost: paid graph feature cost once + cumulative query features, selection, and solver
            c_adaptive = g_feat_time + c_query_feat + c_selection + c_solver

            # Break-even check
            if c_adaptive < c_sbs and first_break_even is None:
                first_break_even = Q

            diff = c_adaptive - c_sbs
            ratio = (c_adaptive / c_sbs) if c_sbs > 0 else 1.0

            # GapClosed calculation
            oracle_gap = c_sbs - c_vbs
            if abs(oracle_gap) < 1e-12:
                gap_closed = math.nan
                gap_status = "zero_oracle_gap"
            else:
                gap_closed = (c_sbs - c_adaptive) / oracle_gap
                gap_status = "normal" if gap_closed >= 0 else "negative_gap"

            pt = WorkloadPoint(
                graph_id=gid,
                Q=Q,
                effective_q=eff_q,
                C_Dijkstra=c_dijk,
                C_Bidirectional=c_bidi,
                C_Astar=c_astar,
                C_SBS=c_sbs,
                C_Adaptive=c_adaptive,
                C_VBS=c_vbs,
                C_graph_feature=g_feat_time,
                C_query_feature=c_query_feat,
                C_selection=c_selection,
                C_solver=c_solver,
                adaptive_minus_SBS=diff,
                adaptive_ratio_to_SBS=ratio,
                gap_closed=gap_closed,
                gap_status=gap_status,
            )
            graph_points.append(pt)

        break_even_per_graph[gid] = first_break_even

    # Aggregate calculation across all graphs
    agg_points: Dict[int, Dict[str, float]] = {}
    agg_break_even = None

    for Q in q_checkpoints:
        pts_q = [pt for pt in graph_points if pt.Q == Q]
        if not pts_q:
            continue

        tot_sbs = sum(pt.C_SBS for pt in pts_q)
        tot_adaptive = sum(pt.C_Adaptive for pt in pts_q)
        tot_vbs = sum(pt.C_VBS for pt in pts_q)
        tot_dijk = sum(pt.C_Dijkstra for pt in pts_q)
        tot_bidi = sum(pt.C_Bidirectional for pt in pts_q)
        tot_astar = sum(pt.C_Astar for pt in pts_q)

        tot_g_feat = sum(pt.C_graph_feature for pt in pts_q)
        tot_q_feat = sum(pt.C_query_feature for pt in pts_q)
        tot_sel = sum(pt.C_selection for pt in pts_q)
        tot_solv = sum(pt.C_solver for pt in pts_q)

        if tot_adaptive < tot_sbs and agg_break_even is None:
            agg_break_even = Q

        gap = tot_sbs - tot_vbs
        if abs(gap) < 1e-12:
            agg_gap_closed = math.nan
        else:
            agg_gap_closed = (tot_sbs - tot_adaptive) / gap

        agg_points[Q] = {
            "Q": Q,
            "total_SBS": tot_sbs,
            "total_Adaptive": tot_adaptive,
            "total_VBS": tot_vbs,
            "total_Dijkstra": tot_dijk,
            "total_Bidirectional": tot_bidi,
            "total_Astar": tot_astar,
            "total_graph_feature": tot_g_feat,
            "total_query_feature": tot_q_feat,
            "total_selection": tot_sel,
            "total_solver": tot_solv,
            "adaptive_minus_SBS": tot_adaptive - tot_sbs,
            "adaptive_ratio_to_SBS": (tot_adaptive / tot_sbs) if tot_sbs > 0 else 1.0,
            "gap_closed": agg_gap_closed,
        }

    return WorkloadAnalysisResult(
        graph_points=graph_points,
        aggregate_points=agg_points,
        break_even_Q_per_graph=break_even_per_graph,
        aggregate_break_even_Q=agg_break_even,
    )


def save_workload_results(result: WorkloadAnalysisResult, output_csv: Union[str, Path]) -> str:
    """Save workload points to CSV."""
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not result.graph_points:
        return str(path)

    field_names = list(result.graph_points[0].to_dict().keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        for pt in result.graph_points:
            writer.writerow(pt.to_dict())

    return str(path)
