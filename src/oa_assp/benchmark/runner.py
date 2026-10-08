"""Master benchmark runner and raw result schema for OA-ASSP (corrected).

Corrected relative to the historical implementation:

* Validity is **derived from actual execution** -- there is no hard-coded
  ``valid=True``. ``valid`` is ``success and correct`` where ``success`` means the
  solver returned a result without exception and without exceeding the timeout,
  and ``correct`` means the returned distance agrees with every other successful
  solver on the same query and the reconstructed path was independently verified.
* ``timeout`` is an explicit field and a timed-out run is never a success.
* ``oracle_eligible`` is derived from execution *and* from the graph's declared
  heuristic admissibility (recorded in graph metadata by the weight assignment),
  rather than from a hard-coded family string.
* A* is timed with a memoized Euclidean heuristic whose per-query memo cost is
  charged inside the timed call (the closure is rebuilt per timed invocation).
"""

from __future__ import annotations
import csv
from dataclasses import dataclass, asdict, fields
import datetime
import math
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import yaml

from oa_assp.algorithms.astar import astar, euclidean_heuristic, zero_heuristic
from oa_assp.algorithms.bellman_ford import bellman_ford
from oa_assp.algorithms.bidirectional_dijkstra import bidirectional_dijkstra
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.algorithms.base import SearchResult
from oa_assp.benchmark.correctness import validate_results
from oa_assp.benchmark.timing import time_solver, TimingResult
from oa_assp.graphs.base import Graph
from oa_assp.graphs.geometric import generate_geometric_graph
from oa_assp.graphs.queries import Query, generate_query_workload
from oa_assp.graphs.random import generate_random_graph
from oa_assp.graphs.scale_free import generate_scale_free_graph
from oa_assp.graphs.weights import (
    assign_geometric_weights,
    assign_positive_random_weights,
)


@dataclass
class BenchmarkRow:
    """Standardized schema for raw benchmark rows (corrected schema)."""

    experiment_id: str
    graph_id: str
    graph_family: str
    graph_seed: int

    V: int
    E: int
    target_average_degree: float
    actual_average_degree: float

    weight_model: str
    weight_parameter: Optional[float]
    epsilon: float

    query_id: str
    query_seed: int
    source: Any
    target: Any
    query_distance_value: float
    query_distance_category: str

    algorithm: str

    # Derived-from-execution status fields (never hard-coded)
    valid: bool
    success: bool
    reachable: bool
    correct: bool
    timeout: bool
    oracle_eligible: bool
    heuristic_admissible: bool
    failure_reason: str

    distance: float

    runtime_median: float
    runtime_mean: float
    runtime_std: float
    runtime_iqr: float
    runtime_min: float
    runtime_max: float

    warmup_runs: int
    timing_repetitions: int

    edges_examined: int
    relaxations: int
    heap_pushes: int
    heap_pops: int
    nodes_expanded: int

    forward_expansions: int
    backward_expansions: int

    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_config(config_path: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """Load configuration from a YAML file path or return dict directly."""
    if isinstance(config_path, dict):
        return config_path
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_graph(
    family: str,
    num_vertices: int,
    average_degree: float,
    seed: int,
    weight_model: str = "geometric",
    weight_c: float = 1.0,
    weight_eps: float = 0.1,
    directed: bool = False,
    weight_min: float = 1.0,
    weight_max: float = 100.0,
    geometric_mechanism: str = "knn",
) -> Graph:
    """Generate and weight a graph according to configuration.

    Generation is unchanged from the historical implementation when called with the
    historical parameters, so graph instances are bit-identical across experiments.
    """
    if family == "random":
        g = generate_random_graph(num_vertices, average_degree, seed, directed=directed)
        assign_positive_random_weights(g, min_weight=weight_min, max_weight=weight_max, seed=seed)
    elif family == "geometric":
        g = generate_geometric_graph(
            num_vertices, average_degree, seed, directed=directed, mechanism=geometric_mechanism
        )
        assign_geometric_weights(g, c=weight_c, epsilon=weight_eps, seed=seed)
    elif family == "scale_free":
        g = generate_scale_free_graph(num_vertices, average_degree, seed, directed=directed)
        assign_positive_random_weights(g, min_weight=weight_min, max_weight=weight_max, seed=seed)
    else:
        raise ValueError(f"Unsupported graph family: {family}")
    return g


def build_solver_set(graph: Graph) -> Dict[str, Tuple[Callable[..., SearchResult], Dict[str, Any], bool]]:
    """Return the candidate solvers for a graph.

    Each entry maps algorithm name to ``(callable, kwargs, oracle_eligible)``.

    * Dijkstra / Bidirectional Dijkstra are always oracle-eligible (exact, and the
      benchmark graphs are verified to have non-negative weights).
    * A* is oracle-eligible only when the graph provides an admissible heuristic.
      Admissibility comes from the graph metadata written by the weight assignment,
      not from a hard-coded family name. A* with the zero heuristic is still
      *executed and measured* (it is a legitimate exact solver, equivalent to
      Dijkstra), but it is excluded from the oracle because a zero-heuristic A*
      cannot add a distinct competitive option.

    The A* entry rebuilds its memoized heuristic inside each timed invocation so the
    per-query heuristic memoization cost is charged to A*.
    """
    heuristic_admissible = bool(graph.metadata.get("heuristic_admissible", False)) and bool(graph.coords)

    if heuristic_admissible:
        def astar_runner(
            g: Graph, s: Any, t: Any, return_path: bool = True
        ) -> SearchResult:
            return astar(g, s, t, heuristic=euclidean_heuristic(g), return_path=return_path)
    else:
        def astar_runner(  # type: ignore[misc]
            g: Graph, s: Any, t: Any, return_path: bool = True
        ) -> SearchResult:
            return astar(g, s, t, heuristic=zero_heuristic, return_path=return_path)

    return {
        "Dijkstra": (dijkstra, {}, True),
        "Bidirectional Dijkstra": (bidirectional_dijkstra, {}, True),
        "A*": (astar_runner, {}, heuristic_admissible),
    }


def run_single_query(
    graph: Graph,
    query: Query,
    experiment_id: str,
    warmup_runs: int = 1,
    repetitions: int = 5,
    timeout_seconds: Optional[float] = 30.0,
    include_bellman_ford: bool = False,
    return_path: bool = True,
    enforce_timeout: bool = False,
) -> List[BenchmarkRow]:
    """Execute all candidate algorithms for a query and record execution-derived status."""
    source = query.source
    target = query.target
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    solver_set = build_solver_set(graph)
    if include_bellman_ford:
        solver_set["Bellman-Ford"] = (bellman_ford, {}, True)

    heuristic_admissible = bool(graph.metadata.get("heuristic_admissible", False)) and bool(graph.coords)

    timing_results: Dict[str, TimingResult] = {}
    search_results: Dict[str, SearchResult] = {}

    for name, (fn, extra_kwargs, _eligible) in solver_set.items():
        t_res = time_solver(
            solver_fn=fn,
            graph=graph,
            source=source,
            target=target,
            warmup_runs=warmup_runs,
            repetitions=repetitions,
            timeout_seconds=timeout_seconds,
            return_path=return_path,
            enforce_timeout=enforce_timeout,
            **extra_kwargs,
        )
        timing_results[name] = t_res
        if t_res.search_result is not None:
            search_results[name] = t_res.search_result

    validation = validate_results(
        graph=graph,
        source=source,
        target=target,
        results=search_results,
    )

    rows: List[BenchmarkRow] = []
    meta = graph.metadata

    for name, (fn, extra_kwargs, eligible) in solver_set.items():
        t_res = timing_results[name]
        s_res = t_res.search_result

        # --- status is derived from actual execution only ---
        timed_out = bool(t_res.timeout)
        errored = t_res.error is not None
        produced_result = s_res is not None
        success = (not timed_out) and (not errored) and produced_result and bool(s_res.success)
        reachable = bool(s_res.reachable) if (produced_result and success) else False
        dist = float(s_res.distance) if produced_result else float("nan")

        path_ok = bool(validation.path_validations.get(name, False))
        correct = bool(success and validation.is_correct and path_ok)
        valid = bool(success and correct)

        failure_reason = ""
        if timed_out:
            failure_reason = "Timeout"
        elif errored:
            failure_reason = str(t_res.error)
        elif not produced_result:
            failure_reason = "No result produced"
        elif not success:
            failure_reason = "Solver reported failure"
        elif not validation.is_correct:
            failure_reason = "; ".join(validation.diagnostics)
        elif not path_ok:
            failure_reason = "Path validation failed"

        oracle_eligible = bool(valid and eligible)
        counters = s_res.counters if s_res is not None else None

        row = BenchmarkRow(
            experiment_id=experiment_id,
            graph_id=graph.graph_id,
            graph_family=meta.get("graph_family", "unknown"),
            graph_seed=meta.get("seed", 0),
            V=graph.num_nodes,
            E=meta.get("num_edges", graph.num_edges),
            target_average_degree=meta.get("target_average_degree", 0.0),
            actual_average_degree=meta.get("actual_average_degree", 0.0),
            weight_model=meta.get("weight_model", "unknown"),
            weight_parameter=meta.get("weight_parameter"),
            epsilon=meta.get("epsilon", 0.0),
            query_id=query.query_id,
            query_seed=query.seed,
            source=source,
            target=target,
            query_distance_value=query.query_distance_value,
            query_distance_category=query.query_distance_category,
            algorithm=name,
            valid=valid,
            success=success,
            reachable=reachable,
            correct=correct,
            timeout=timed_out,
            oracle_eligible=oracle_eligible,
            heuristic_admissible=heuristic_admissible,
            failure_reason=failure_reason,
            distance=dist,
            runtime_median=t_res.median_runtime,
            runtime_mean=t_res.mean_runtime,
            runtime_std=t_res.std_runtime,
            runtime_iqr=t_res.iqr_runtime,
            runtime_min=t_res.min_runtime,
            runtime_max=t_res.max_runtime,
            warmup_runs=warmup_runs,
            timing_repetitions=repetitions,
            edges_examined=counters.edges_examined if counters else 0,
            relaxations=counters.relaxations if counters else 0,
            heap_pushes=counters.heap_pushes if counters else 0,
            heap_pops=counters.heap_pops if counters else 0,
            nodes_expanded=counters.nodes_expanded if counters else 0,
            forward_expansions=counters.forward_expansions if counters else 0,
            backward_expansions=counters.backward_expansions if counters else 0,
            timestamp=timestamp,
        )
        rows.append(row)

    return rows


def benchmark_row_fieldnames() -> List[str]:
    """Return the canonical raw-row schema field order."""
    return [f.name for f in fields(BenchmarkRow)]
