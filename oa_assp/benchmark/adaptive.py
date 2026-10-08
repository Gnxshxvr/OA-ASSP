"""Real end-to-end adaptive execution path.

This module answers "what does the adaptive path actually cost?" by *executing* it
and timing the whole thing, instead of summing separately measured microbenchmarks.

Each pass over one graph consists of two adjacent loops on the same query list:

Loop A -- the adaptive path, measured end to end
    1. graph-level feature preparation (once per workload),
    2. per query: query-level feature extraction,
    3. per query: selector inference on a single instance (what an online dispatcher
       pays; no batch amortization is used),
    4. per query: the selected solver, timed single-shot.
    The wall-clock time of this loop IS ``T_adaptive_end_to_end``. Nothing that is not
    part of the adaptive path is executed inside it.

Loop B -- paired references on the same queries in the same order
    5. per query: the SBS policy's solver, timed single-shot,
    6. per query: the VBS winner's solver, timed single-shot.

Because Loop A and Loop B run back to back in the same process on the same ordered
queries, ``C_Adaptive - C_SBS`` is a paired difference measured in one modality,
which is what makes a sub-percent comparison meaningful at all. Loop B is deliberately
outside the end-to-end window so it cannot contaminate ``T_adaptive_end_to_end``.

The component sum (step 1 + per-query steps 2--4) is compared against the measured
end-to-end total; the difference is the loop-body cost (loop control plus three
``perf_counter`` calls per query) and is reported rather than hidden.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from oa_assp.benchmark.oracle import OracleInstance
from oa_assp.benchmark.timing import time_solver_single_shot
from oa_assp.features.extractor import FeatureExtractor
from oa_assp.graphs.base import Graph
from oa_assp.graphs.queries import Query
from oa_assp.selector.decision_tree import DecisionTreeSelector

POLICY_TO_ALGORITHM = {
    "Always-Dijkstra": "Dijkstra",
    "Always-Bidirectional-Dijkstra": "Bidirectional Dijkstra",
    "Always-A*": "A*",
}


@dataclass
class AdaptiveQueryRecord:
    """One query executed through the real adaptive path."""

    experiment_id: str
    graph_id: str
    graph_family: str
    V: int
    target_D: float
    tier: int
    selection_mode: str
    pass_index: int
    query_index: int
    query_id: str

    selected_algorithm: str
    sbs_policy: str
    sbs_algorithm: str
    vbs_algorithm: str

    graph_feature_time: float
    query_feature_time: float
    feature_vector_time: float
    selection_time: float
    solver_time: float
    sbs_solver_time: float
    vbs_solver_time: float
    bookkeeping_time: float

    solver_success: bool
    solver_timeout: bool
    solver_error: str
    solver_distance: float
    solver_distance_matches: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdaptiveWorkloadResult:
    """Result of one end-to-end adaptive workload pass."""

    graph_id: str
    pass_index: int
    num_queries: int
    adaptive_wall_clock: float
    sum_graph_feature: float
    sum_query_feature: float
    sum_feature_vector: float
    sum_selection: float
    sum_solver: float
    component_sum: float
    unaccounted: float
    sum_sbs_solver: float
    sum_vbs_solver: float
    records: List[AdaptiveQueryRecord]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("records")
        d["num_records"] = len(self.records)
        return d


def run_adaptive_workload(
    graph: Graph,
    queries: Sequence[Query],
    selector: DecisionTreeSelector,
    feature_extractor: FeatureExtractor,
    tier: int,
    feature_names: Sequence[str],
    oracle_map: Dict[Tuple[str, str], OracleInstance],
    sbs_policy: str,
    solver_set: Dict[str, Tuple[Callable[..., Any], Dict[str, Any], bool]],
    experiment_id: str,
    pass_index: int = 0,
    timeout_seconds: Optional[float] = 30.0,
    return_path: bool = True,
    verify_distances: bool = False,
    selection_mode: str = "library",
) -> AdaptiveWorkloadResult:
    """Execute one full adaptive workload pass and measure it end to end.

    ``selection_mode`` selects how the fitted decision tree is evaluated:
    ``"library"`` uses the model library's general-purpose predict call, ``"compiled"``
    walks the tree as nested conditionals (the deployment form that interpretability
    actually allows). Both are honest representations; they are reported separately
    because they differ by orders of magnitude in per-query cost.
    """
    if selection_mode not in ("library", "compiled"):
        raise ValueError(f"Unknown selection_mode: {selection_mode}")
    if not selector.is_fitted:
        raise RuntimeError("Selector must be fitted before running the adaptive workload.")

    sbs_algorithm = POLICY_TO_ALGORITHM.get(sbs_policy)
    if sbs_algorithm is None:
        raise ValueError(f"Unknown SBS policy: {sbs_policy}")
    for algo in (sbs_algorithm, "Dijkstra"):
        if algo not in solver_set:
            raise ValueError(f"Algorithm {algo} not present in the solver set.")

    meta = graph.metadata
    graph_family = str(meta.get("graph_family", "unknown"))
    target_D = float(meta.get("target_average_degree", 0.0))

    records: List[AdaptiveQueryRecord] = []

    # ---------------------------------------------------------------- Loop A
    t_wall_start = time.perf_counter()

    graph_features, graph_feature_time = feature_extractor.extract_graph_features(graph, tier=tier)

    adaptive: List[Tuple[int, str, str, float, float, float, float, bool, bool, str, float, dict]] = []
    sum_qfeat = 0.0
    sum_sel = 0.0
    sum_solver = 0.0
    sum_vec = 0.0

    for idx, query in enumerate(queries):
        key = (graph.graph_id, query.query_id)
        inst = oracle_map.get(key)
        if inst is None:
            continue

        q_features, q_time = feature_extractor.extract_query_features(graph, query, tier=tier)

        # Feature-vector assembly (merge graph+query features, order them for the model).
        # Timed explicitly because it is a real per-query cost of the adaptive path.
        t_vec = time.perf_counter()
        combined = dict(graph_features)
        combined.update(q_features)
        x = [float(combined.get(name, 0.0)) for name in feature_names]
        vec_time = time.perf_counter() - t_vec

        if selection_mode == "compiled":
            selected_algo, sel_time = selector.predict_compiled(x)
        else:
            selected_algo, sel_time = selector.predict_one(x)

        fn, kwargs, _eligible = solver_set[selected_algo]
        solver_time, solver_res, solver_timeout, solver_error = time_solver_single_shot(
            fn, graph, query.source, query.target,
            timeout_seconds=timeout_seconds, return_path=return_path, **kwargs,
        )

        sum_qfeat += q_time
        sum_sel += sel_time
        sum_solver += solver_time
        sum_vec += vec_time

        adaptive.append(
            (
                idx,
                query.query_id,
                selected_algo,
                q_time,
                vec_time,
                sel_time,
                solver_time,
                bool(solver_error is None and not solver_timeout and solver_res is not None),
                bool(solver_timeout),
                str(solver_error or ""),
                float(solver_res.distance) if solver_res is not None else float("nan"),
                solver_res,
            )
        )

    adaptive_wall_clock = time.perf_counter() - t_wall_start
    component_sum = graph_feature_time + sum_qfeat + sum_vec + sum_sel + sum_solver

    # ---------------------------------------------------------------- Loop B
    # Paired references, measured outside the end-to-end adaptive window.
    sbs_fn, sbs_kwargs, _ = solver_set[sbs_algorithm]
    vbs_keys: Dict[str, Tuple[Callable[..., Any], Dict[str, Any]]] = {}
    for algo, (fnx, kwx, _e) in solver_set.items():
        vbs_keys[algo] = (fnx, kwx)

    sum_sbs = 0.0
    sum_vbs = 0.0
    paired: List[Tuple[float, float, str]] = []

    for idx, query in enumerate(queries):
        key = (graph.graph_id, query.query_id)
        inst = oracle_map.get(key)
        if inst is None:
            continue

        sbs_time, _, _, _ = time_solver_single_shot(
            sbs_fn, graph, query.source, query.target,
            timeout_seconds=timeout_seconds, return_path=False, **sbs_kwargs,
        )
        vbs_algo = inst.vbs_algorithm
        if vbs_algo in vbs_keys and vbs_algo != "none":
            vfn, vkw = vbs_keys[vbs_algo]
            vbs_time, _, _, _ = time_solver_single_shot(
                vfn, graph, query.source, query.target,
                timeout_seconds=timeout_seconds, return_path=False, **vkw,
            )
        else:
            vbs_time = math.nan
        sum_sbs += sbs_time
        if not math.isnan(vbs_time):
            sum_vbs += vbs_time
        paired.append((sbs_time, vbs_time, vbs_algo))

    # -------------------------------------------------- optional verification
    # Correctness cross-check, deliberately outside every timing region.
    distance_matches: Dict[str, bool] = {}
    if verify_distances:
        ref_fn, ref_kwargs, _ = solver_set["Dijkstra"]
        queries_by_id = {q.query_id: q for q in queries}
        for entry in adaptive:
            qid = entry[1]
            selected = entry[2]
            query = queries_by_id.get(qid)
            if query is None:
                continue
            sel_fn, sel_kwargs, _ = solver_set[selected]
            _, sel_res, _, _ = time_solver_single_shot(
                sel_fn, graph, query.source, query.target,
                timeout_seconds=timeout_seconds, return_path=True, **sel_kwargs,
            )
            _, ref_res, _, _ = time_solver_single_shot(
                ref_fn, graph, query.source, query.target,
                timeout_seconds=timeout_seconds, return_path=False, **ref_kwargs,
            )
            if sel_res is None or ref_res is None:
                distance_matches[qid] = False
            else:
                d_sel, d_ref = float(sel_res.distance), float(ref_res.distance)
                distance_matches[qid] = bool(
                    sel_res.reachable == ref_res.reachable
                    and (math.isinf(d_sel) and math.isinf(d_ref) or abs(d_sel - d_ref) < 1e-9)
                )

    # Per-query loop/bookkeeping cost: everything in the adaptive path that is not one
    # of the five explicitly timed components, split evenly across the queries.
    n_records = max(1, len(adaptive))
    bookkeeping_per_query = max(0.0, (adaptive_wall_clock - component_sum) / n_records)

    for (idx, qid, selected_algo, q_time, vec_time, sel_time, solver_time, ok, to, err, dist, _res) in adaptive:
        sbs_time, vbs_time, vbs_algo = paired[idx] if idx < len(paired) else (math.nan, math.nan, "none")
        records.append(
            AdaptiveQueryRecord(
                experiment_id=experiment_id,
                graph_id=graph.graph_id,
                graph_family=graph_family,
                V=graph.num_nodes,
                target_D=target_D,
                tier=tier,
                selection_mode=selection_mode,
                pass_index=pass_index,
                query_index=idx,
                query_id=qid,
                selected_algorithm=selected_algo,
                sbs_policy=sbs_policy,
                sbs_algorithm=sbs_algorithm,
                vbs_algorithm=vbs_algo,
                graph_feature_time=graph_feature_time,
                query_feature_time=q_time,
                feature_vector_time=vec_time,
                selection_time=sel_time,
                solver_time=solver_time,
                sbs_solver_time=sbs_time,
                vbs_solver_time=vbs_time,
                bookkeeping_time=bookkeeping_per_query,
                solver_success=bool(ok),
                solver_timeout=bool(to),
                solver_error=err,
                solver_distance=dist,
                solver_distance_matches=bool(distance_matches.get(qid, False)) if verify_distances else False,
            )
        )

    return AdaptiveWorkloadResult(
        graph_id=graph.graph_id,
        pass_index=pass_index,
        num_queries=len(records),
        adaptive_wall_clock=adaptive_wall_clock,
        sum_graph_feature=graph_feature_time,
        sum_query_feature=sum_qfeat,
        sum_feature_vector=sum_vec,
        sum_selection=sum_sel,
        sum_solver=sum_solver,
        component_sum=component_sum,
        unaccounted=adaptive_wall_clock - component_sum,
        sum_sbs_solver=sum_sbs,
        sum_vbs_solver=sum_vbs,
        records=records,
    )
