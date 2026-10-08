"""Capture-rate analysis: when does adaptive selection pay for its own overhead?

Definitions (all cumulative over a workload of ``Q`` queries for one graph)
--------------------------------------------------------------------------
``C_SBS(Q)``       cost of the training-derived single best solver policy
``C_VBS(Q)``       per-instance oracle cost (min over oracle-eligible solvers)
``C_Adaptive(Q)``  cost of the real adaptive path (features + selection + solver)

``OracleGap(Q)``       = C_SBS(Q) - C_VBS(Q)
``AdaptiveSavings(Q)`` = C_SBS(Q) - C_Adaptive(Q)
``CaptureRate(Q)``     = AdaptiveSavings(Q) / OracleGap(Q)      (NaN if gap <= 0)
``SelectionOverhead(Q)`` = C_graph_feature + sum(C_query_feature) + sum(C_selection)
``SolverOnlyCapture(Q)`` = (C_SBS(Q) - C_selected_solver(Q)) / OracleGap(Q)
``RequiredCapture(Q)`` = SelectionOverhead(Q) / OracleGap(Q)

Three accounting levels are reported and never conflated
-------------------------------------------------------
* ``*`` (narrow): graph features + query features + selector inference. The irreducible
  cost of deciding.
* ``*_task`` (headline): the narrow level plus per-query feature-vector assembly -- i.e.
  every operation the adaptive path really performs apart from the solver itself.
* ``*_e2e`` (pessimistic): the task level plus the instrumented loop's residual, obtained
  as ``measured_wall_clock - sum(measured components)``. The residual is measurement
  machinery (loop control, ``perf_counter`` calls, tuple construction) that a deployment
  would not pay for, so charging it to the adaptive path overstates its cost. It is
  reported rather than hidden, and the ``*_e2e`` variant is therefore an upper bound.

Adaptive selection pays for itself at workload ``Q`` exactly when
``AdaptiveSavings >= SelectionOverhead``, equivalently
``CaptureRate >= RequiredCapture``.

Degenerate cases are labelled rather than patched: when the oracle gap is at or
below the numerical tolerance the ratios are undefined and are reported as NaN with
``gap_status`` describing the case. No value is ever substituted to make the
comparison look favourable.
"""

from __future__ import annotations
import csv
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

GAP_EPSILON = 1e-12


@dataclass
class CapturePoint:
    """Capture analysis for one graph at one workload size."""

    graph_id: str
    family: str
    V: int
    target_D: float
    Q: int
    effective_q: int

    C_SBS: float
    C_VBS: float
    C_Adaptive: float
    C_graph_feature: float
    C_query_feature: float
    C_selection: float
    C_selected_solver: float
    SelectionOverhead: float

    # The real adaptive path additionally pays feature-vector assembly and loop
    # bookkeeping per query. These are measured, not modelled.
    C_feature_vector: float
    C_bookkeeping: float
    AdditionalOverhead_e2e: float
    SelectionOverhead_e2e: float
    C_Adaptive_e2e: float

    # Headline accounting: all real work of the adaptive path except the solver.
    SelectionOverhead_task: float
    C_Adaptive_task: float
    AdaptiveMinusSBS_task: float
    AdaptiveSavings_task: float
    CaptureRate_task: float
    RequiredCapture_task: float
    Pays_for_itself_task: bool

    OracleGap: float
    AdaptiveSavings: float
    CaptureRate: float
    SolverOnlyCapture: float
    RequiredCapture: float
    AdaptiveMinusSBS: float
    AdaptiveRatioSBS: float
    GapClosed: float
    Pays_for_itself: bool
    Pays_for_itself_components_only: bool
    CaptureRate_e2e: float
    RequiredCapture_e2e: float
    AdaptiveSavings_e2e: float
    AdaptiveMinusSBS_e2e: float
    gap_status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CaptureAnalysisResult:
    """Per-graph and aggregate capture analysis."""

    graph_points: List[CapturePoint]
    aggregate_points: Dict[int, Dict[str, Any]]
    break_even_Q_per_graph: Dict[str, Optional[int]]
    aggregate_break_even_Q: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_points": self.aggregate_points,
            "break_even_Q_per_graph": self.break_even_Q_per_graph,
            "aggregate_break_even_Q": self.aggregate_break_even_Q,
            "num_graph_points": len(self.graph_points),
        }


def _ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= GAP_EPSILON:
        return math.nan
    return numerator / denominator


def compute_capture_analysis(
    per_graph_queries: Dict[str, List[Dict[str, Any]]],
    graph_feature_times: Dict[str, float],
    graph_meta: Dict[str, Dict[str, Any]],
    q_checkpoints: Optional[Sequence[int]] = None,
) -> CaptureAnalysisResult:
    """Compute per-graph and aggregate capture analysis.

    Parameters
    ----------
    per_graph_queries
        ``graph_id -> ordered list of per-query records``. Each record must provide
        ``query_feature_time``, ``selection_time``, ``solver_time`` (the selected
        solver), ``sbs_solver_time`` (the SBS policy's solver on the same query) and
        ``vbs_solver_time`` (the VBS winner's solver on the same query). All three
        solver times must be measured in the same modality so the differences are
        paired.
    graph_feature_times
        One-time graph-level feature cost per graph (charged once per workload).
    graph_meta
        ``graph_id -> {family, V, target_D}``.
    """
    if q_checkpoints is None:
        q_checkpoints = [1, 10, 50, 100, 500]

    graph_points: List[CapturePoint] = []
    break_even_per_graph: Dict[str, Optional[int]] = {}

    for gid, records in per_graph_queries.items():
        g_feat = float(graph_feature_times.get(gid, 0.0))
        meta = graph_meta.get(gid, {})
        n_queries = len(records)
        first_break_even: Optional[int] = None

        for Q in q_checkpoints:
            eff_q = min(int(Q), n_queries)
            if eff_q <= 0:
                continue
            sub = records[:eff_q]

            c_qfeat = sum(float(r["query_feature_time"]) for r in sub)
            c_vec = sum(float(r.get("feature_vector_time", 0.0)) for r in sub)
            c_book = sum(float(r.get("bookkeeping_time", 0.0)) for r in sub)
            c_sel = sum(float(r["selection_time"]) for r in sub)
            c_solver = sum(float(r["solver_time"]) for r in sub)
            c_sbs = sum(float(r["sbs_solver_time"]) for r in sub)
            c_vbs = sum(float(r["vbs_solver_time"]) for r in sub)

            overhead = g_feat + c_qfeat + c_sel
            c_adaptive = overhead + c_solver

            additional = c_vec + c_book
            overhead_e2e = overhead + additional
            c_adaptive_e2e = c_adaptive + additional
            overhead_task = overhead + c_vec
            c_adaptive_task = c_adaptive + c_vec

            oracle_gap = c_sbs - c_vbs
            savings = c_sbs - c_adaptive
            savings_e2e = c_sbs - c_adaptive_e2e
            savings_task = c_sbs - c_adaptive_task

            if oracle_gap > GAP_EPSILON:
                capture_rate = savings / oracle_gap
                solver_capture = (c_sbs - c_solver) / oracle_gap
                required = overhead / oracle_gap
                capture_rate_e2e = savings_e2e / oracle_gap
                required_e2e = overhead_e2e / oracle_gap
                capture_rate_task = savings_task / oracle_gap
                required_task = overhead_task / oracle_gap
                gap_status = "positive_gap"
            elif oracle_gap < -GAP_EPSILON:
                capture_rate = math.nan
                solver_capture = math.nan
                required = math.nan
                capture_rate_e2e = math.nan
                required_e2e = math.nan
                capture_rate_task = math.nan
                required_task = math.nan
                gap_status = "negative_gap"
            else:
                capture_rate = math.nan
                solver_capture = math.nan
                required = math.nan
                capture_rate_e2e = math.nan
                required_e2e = math.nan
                capture_rate_task = math.nan
                required_task = math.nan
                gap_status = "zero_oracle_gap"

            pays = bool(c_adaptive_e2e < c_sbs)
            if pays and first_break_even is None:
                first_break_even = int(Q)

            graph_points.append(
                CapturePoint(
                    graph_id=gid,
                    family=str(meta.get("family", "unknown")),
                    V=int(meta.get("V", 0)),
                    target_D=float(meta.get("target_D", 0.0)),
                    Q=int(Q),
                    effective_q=eff_q,
                    C_SBS=c_sbs,
                    C_VBS=c_vbs,
                    C_Adaptive=c_adaptive,
                    C_graph_feature=g_feat,
                    C_query_feature=c_qfeat,
                    C_selection=c_sel,
                    C_selected_solver=c_solver,
                    SelectionOverhead=overhead,
                    C_feature_vector=c_vec,
                    C_bookkeeping=c_book,
                    AdditionalOverhead_e2e=additional,
                    SelectionOverhead_e2e=overhead_e2e,
                    C_Adaptive_e2e=c_adaptive_e2e,
                    SelectionOverhead_task=overhead_task,
                    C_Adaptive_task=c_adaptive_task,
                    AdaptiveMinusSBS_task=c_adaptive_task - c_sbs,
                    AdaptiveSavings_task=savings_task,
                    CaptureRate_task=capture_rate_task,
                    RequiredCapture_task=required_task,
                    Pays_for_itself_task=bool(c_adaptive_task < c_sbs),
                    OracleGap=oracle_gap,
                    AdaptiveSavings=savings,
                    CaptureRate=capture_rate,
                    SolverOnlyCapture=solver_capture,
                    RequiredCapture=required,
                    AdaptiveMinusSBS=c_adaptive - c_sbs,
                    AdaptiveRatioSBS=(c_adaptive / c_sbs) if c_sbs > 0 else math.nan,
                    GapClosed=(-savings / oracle_gap) if oracle_gap > GAP_EPSILON else math.nan,
                    Pays_for_itself=pays,
                    Pays_for_itself_components_only=bool(c_adaptive < c_sbs),
                    CaptureRate_e2e=capture_rate_e2e,
                    RequiredCapture_e2e=required_e2e,
                    AdaptiveSavings_e2e=savings_e2e,
                    AdaptiveMinusSBS_e2e=c_adaptive_e2e - c_sbs,
                    gap_status=gap_status,
                )
            )

        break_even_per_graph[gid] = first_break_even

    # Aggregate over graphs: sums of paired quantities, then ratios of sums.
    agg_points: Dict[int, Dict[str, Any]] = {}
    agg_break_even: Optional[int] = None

    for Q in q_checkpoints:
        pts = [p for p in graph_points if p.Q == int(Q)]
        if not pts:
            continue
        tot_sbs = sum(p.C_SBS for p in pts)
        tot_vbs = sum(p.C_VBS for p in pts)
        tot_adaptive = sum(p.C_Adaptive for p in pts)
        tot_overhead = sum(p.SelectionOverhead for p in pts)
        tot_g = sum(p.C_graph_feature for p in pts)
        tot_q = sum(p.C_query_feature for p in pts)
        tot_sel = sum(p.C_selection for p in pts)
        tot_solver = sum(p.C_selected_solver for p in pts)
        tot_vec = sum(p.C_feature_vector for p in pts)
        tot_book = sum(p.C_bookkeeping for p in pts)
        tot_additional = tot_vec + tot_book
        tot_overhead_e2e = tot_overhead + tot_additional
        tot_adaptive_e2e = tot_adaptive + tot_additional
        tot_overhead_task = tot_overhead + tot_vec
        tot_adaptive_task = tot_adaptive + tot_vec

        gap = tot_sbs - tot_vbs
        savings = tot_sbs - tot_adaptive
        savings_e2e = tot_sbs - tot_adaptive_e2e
        savings_task = tot_sbs - tot_adaptive_task
        status = "positive_gap" if gap > GAP_EPSILON else ("negative_gap" if gap < -GAP_EPSILON else "zero_oracle_gap")

        pays = bool(tot_adaptive_e2e < tot_sbs)
        if pays and agg_break_even is None:
            agg_break_even = int(Q)

        agg_points[int(Q)] = {
            "Q": int(Q),
            "num_graphs": len(pts),
            "num_queries": sum(p.effective_q for p in pts),
            "total_SBS": tot_sbs,
            "total_VBS": tot_vbs,
            "total_Adaptive": tot_adaptive,
            "total_Adaptive_e2e": tot_adaptive_e2e,
            "total_graph_feature": tot_g,
            "total_query_feature": tot_q,
            "total_feature_vector": tot_vec,
            "total_selection": tot_sel,
            "total_bookkeeping": tot_book,
            "total_selected_solver": tot_solver,
            "SelectionOverhead": tot_overhead,
            "SelectionOverhead_e2e": tot_overhead_e2e,
            "SelectionOverhead_task": tot_overhead_task,
            "total_Adaptive_task": tot_adaptive_task,
            "OracleGap": gap,
            "AdaptiveSavings": savings,
            "AdaptiveSavings_e2e": savings_e2e,
            "AdaptiveSavings_task": savings_task,
            "CaptureRate": _ratio(savings, gap),
            "CaptureRate_e2e": _ratio(savings_e2e, gap),
            "CaptureRate_task": _ratio(savings_task, gap),
            "SolverOnlyCapture": _ratio(tot_sbs - tot_solver, gap),
            "RequiredCapture": _ratio(tot_overhead, gap),
            "RequiredCapture_e2e": _ratio(tot_overhead_e2e, gap),
            "RequiredCapture_task": _ratio(tot_overhead_task, gap),
            "Pays_for_itself_task": bool(tot_adaptive_task < tot_sbs),
            "AdaptiveMinusSBS": tot_adaptive - tot_sbs,
            "AdaptiveMinusSBS_e2e": tot_adaptive_e2e - tot_sbs,
            "AdaptiveMinusSBS_task": tot_adaptive_task - tot_sbs,
            "AdaptiveRatioSBS": (tot_adaptive / tot_sbs) if tot_sbs > 0 else math.nan,
            "AdaptiveRatioSBS_e2e": (tot_adaptive_e2e / tot_sbs) if tot_sbs > 0 else math.nan,
            "GapClosed": _ratio(-savings, gap) if gap > GAP_EPSILON else math.nan,
            "GapClosed_e2e": _ratio(-savings_e2e, gap) if gap > GAP_EPSILON else math.nan,
            "Pays_for_itself": pays,
            "Pays_for_itself_components_only": bool(tot_adaptive < tot_sbs),
            "gap_status": status,
        }

    return CaptureAnalysisResult(
        graph_points=graph_points,
        aggregate_points=agg_points,
        break_even_Q_per_graph=break_even_per_graph,
        aggregate_break_even_Q=agg_break_even,
    )


POLICY_TO_ALGORITHM = {
    "Always-Dijkstra": "Dijkstra",
    "Always-Bidirectional-Dijkstra": "Bidirectional Dijkstra",
    "Always-A*": "A*",
}


def build_benchmark_cost_table(
    benchmark_rows: Sequence[Dict[str, Any]],
) -> Dict[Tuple[str, str], Dict[str, Tuple[float, bool]]]:
    """Index the benchmark's repeated-median runtimes by (graph, query) and algorithm."""
    table: Dict[Tuple[str, str], Dict[str, Tuple[float, bool]]] = {}
    for row in benchmark_rows:
        gid = str(row["graph_id"])
        qid = str(row["query_id"])
        algo = str(row["algorithm"])
        try:
            cost = float(row["runtime_median"])
        except (TypeError, ValueError):
            continue
        if "oracle_eligible" in row:
            raw = row["oracle_eligible"]
            eligible = raw.strip().lower() == "true" if isinstance(raw, str) else bool(raw)
        else:
            eligible = True
        table.setdefault((gid, qid), {})[algo] = (cost, eligible)
    return table


def substitute_benchmark_solver_costs(
    adaptive_series: Sequence[Dict[str, Any]],
    benchmark_table: Dict[Tuple[str, str], Dict[str, Tuple[float, bool]]],
    graph_id: str,
    fallback_algorithm: str = "Dijkstra",
) -> List[Dict[str, Any]]:
    """Replace single-shot solver times with the benchmark's repeated-median times.

    The adaptive passes measure the *selected*, SBS and VBS solver calls single-shot,
    because repeating them would change the workload being measured. Single-shot solver
    timings are noisy (tens of microseconds), so the reported oracle gap is recomputed
    here from the benchmark runtimes, which are medians of five repetitions measured
    under the standard protocol. Everything else in the record (the measured per-query
    feature, vector-assembly, selection and bookkeeping costs) is left untouched, so
    ``C_Adaptive`` remains overhead-as-measured plus a better estimate of the solver.

    Queries missing from the benchmark table are dropped; the number dropped is
    reported by the caller through the returned records. Records whose recorded
    algorithm was not oracle-eligible (or was recorded as ``none``) fall back to
    ``fallback_algorithm``, mirroring what a real dispatcher would execute.
    """
    out: List[Dict[str, Any]] = []
    for rec in adaptive_series:
        qid = str(rec["query_id"])
        entry = benchmark_table.get((graph_id, qid))
        if not entry:
            continue

        def _cost(algo: Any) -> float:
            algo_name = str(algo)
            got = entry.get(algo_name)
            if got is not None and got[1]:
                return got[0]
            fb = entry.get(fallback_algorithm)
            return fb[0] if fb is not None else math.nan

        candidates = [c for c, ok in entry.values() if ok and c < float("inf")]
        new = dict(rec)
        new["solver_time"] = _cost(rec.get("selected_algorithm", fallback_algorithm))
        new["sbs_solver_time"] = _cost(rec.get("sbs_algorithm", fallback_algorithm))
        # VBS is the minimum over oracle-eligible algorithms on this query.
        new["vbs_solver_time"] = min(candidates) if candidates else math.nan
        new["solver_cost_source"] = "benchmark_repeated_median"
        out.append(new)
    return out


def oracle_gap_crosscheck(
    benchmark_rows: Sequence[Dict[str, Any]],
    sbs_policy: str,
    query_order: Dict[str, Sequence[str]],
    q_checkpoints: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    """Recompute the oracle gap from the benchmark's repeated-median runtimes.

    The paired adaptive loop measures SBS and VBS solver calls single-shot, which is
    the only modality in which ``C_Adaptive - C_SBS`` is a legitimate paired difference.
    Single-shot solver timings at tens of microseconds are noisy, so the resulting gap
    is cross-checked here against the *same* quantity computed from the benchmark's
    warm-up-plus-repetitions median runtimes, which are far less noisy but were not
    measured in the adaptive modality.

    The two are not expected to agree exactly. Large disagreement is informative: it
    means the measured gap is dominated by timing noise, and the capture analysis
    should be read as bounded rather than precise.

    Returns a dict with ``aggregate`` (per Q) and ``per_graph`` (at the largest Q).
    """
    if q_checkpoints is None:
        q_checkpoints = [1, 10, 50, 100, 500]

    sbs_algo = POLICY_TO_ALGORITHM.get(sbs_policy, "Dijkstra")
    table = build_benchmark_cost_table(benchmark_rows)

    def _costs(gid: str, qid: str) -> Optional[Tuple[float, float]]:
        algos = table.get((gid, qid))
        if not algos:
            return None
        sbs_entry = algos.get(sbs_algo)
        if sbs_entry is None or not sbs_entry[1]:
            # A* policy falls back to Dijkstra when no admissible heuristic exists.
            sbs_entry = algos.get("Dijkstra")
        if sbs_entry is None:
            return None
        candidate = [c for a, (c, ok) in algos.items() if ok and c < float("inf")]
        if not candidate:
            return None
        return sbs_entry[0], min(candidate)

    per_graph: Dict[str, Dict[str, Any]] = {}
    aggregate: Dict[int, Dict[str, Any]] = {}

    for gid, order in query_order.items():
        rows: List[Tuple[float, float]] = []
        for qid in order:
            got = _costs(gid, qid)
            if got is not None:
                rows.append(got)
        if not rows:
            continue

        per_graph[gid] = {}
        for Q in q_checkpoints:
            sub = rows[: min(int(Q), len(rows))]
            if not sub:
                continue
            sbs = sum(r[0] for r in sub)
            vbs = sum(r[1] for r in sub)
            per_graph[gid][int(Q)] = {
                "graph_id": gid,
                "Q": int(Q),
                "effective_q": len(sub),
                "SBS_benchmark": sbs,
                "VBS_benchmark": vbs,
                "OracleGap_benchmark": sbs - vbs,
            }
            slot = aggregate.setdefault(int(Q), {"Q": int(Q), "num_graphs": 0, "SBS_benchmark": 0.0,
                                                "VBS_benchmark": 0.0, "OracleGap_benchmark": 0.0})
            slot["num_graphs"] += 1
            slot["SBS_benchmark"] += sbs
            slot["VBS_benchmark"] += vbs
            slot["OracleGap_benchmark"] += sbs - vbs

    return {"aggregate": aggregate, "per_graph": per_graph}


def capture_points_to_csv(result: CaptureAnalysisResult, output_path: Union[str, Path]) -> str:
    """Write per-graph capture points to CSV."""
    path = Path(output_path)
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


def aggregate_points_to_csv(result: CaptureAnalysisResult, output_path: Union[str, Path]) -> str:
    """Write aggregate capture points to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not result.aggregate_points:
        return str(path)
    field_names = list(next(iter(result.aggregate_points.values())).keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        for Q in sorted(result.aggregate_points):
            writer.writerow(result.aggregate_points[Q])
    return str(path)
