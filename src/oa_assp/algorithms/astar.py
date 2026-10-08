"""A* exact single-pair shortest-path algorithm."""

from __future__ import annotations
import heapq
import math
import time
from typing import Any, Callable, Dict, List, Optional

from oa_assp.algorithms.base import HeuristicFn, OperationCounters, SearchResult
from oa_assp.graphs.base import Graph


def euclidean_heuristic(graph: Graph) -> HeuristicFn:
    """Create an admissible Euclidean distance heuristic for a geometric graph.

    The heuristic value h(u, target) is memoized per (node, target) pair so that a
    given node's heuristic is computed at most once per target, instead of being
    recomputed on every edge relaxation / heap push.

    Memoization does not change any returned value or any floating-point operation:
    every value is still produced by ``math.sqrt(sum((a - b) ** 2 ...))`` on the same
    inputs. It only removes redundant recomputation, and therefore does not alter
    admissibility, consistency, expansion order, operation counters, or the exact
    shortest-path result (see ``oa_assp/tests/test_astar_cached.py``).

    Because the memo is created per returned closure, each closure carries its own
    per-target cache; a fresh closure is cheap and is created per query by callers
    that want the memoization cost charged to that query.
    """
    coords = graph.coords
    # Nested memo keyed by target, then by node, so that a single closure is correct
    # even if it is reused across queries with different targets.
    memo: Dict[Any, Dict[Any, float]] = {}

    def h(u: Any, target: Any) -> float:
        if u not in coords or target not in coords:
            return 0.0
        per_target = memo.get(target)
        if per_target is None:
            per_target = {}
            memo[target] = per_target
        cached = per_target.get(u)
        if cached is not None:
            return cached
        c1 = coords[u]
        c2 = coords[target]
        value = math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))
        per_target[u] = value
        return value

    return h


def zero_heuristic(u: Any, target: Any) -> float:
    """Trivial zero heuristic (admissible and consistent for any non-negative graph)."""
    return 0.0


def astar(
    graph: Graph,
    source: Any,
    target: Any,
    heuristic: Optional[HeuristicFn] = None,
    return_path: bool = True,
) -> SearchResult:
    """Compute the exact shortest path from source to target using A* search.

    Parameters
    ----------
    graph : Graph
        Input graph with non-negative edge weights.
    source : Any
        Source node identifier.
    target : Any
        Target node identifier.
    heuristic : Optional[HeuristicFn], optional
        Heuristic function h(u, target) -> float. If None, defaults to zero_heuristic
        (or euclidean_heuristic if coordinates exist for both nodes).
    return_path : bool, optional
        Whether to reconstruct and return the full path, by default True.

    Returns
    -------
    SearchResult
        Structured result containing distance, path, runtime, and operation counters.

    Raises
    ------
    ValueError
        If a negative edge weight is encountered.
    """
    counters = OperationCounters()
    start_time = time.perf_counter()

    if source not in graph or target not in graph:
        runtime = time.perf_counter() - start_time
        return SearchResult(
            distance=math.inf,
            path=None,
            runtime=runtime,
            success=True,
            reachable=False,
            counters=counters,
            metadata={"reason": "source or target not in graph"},
        )

    if source == target:
        runtime = time.perf_counter() - start_time
        return SearchResult(
            distance=0.0,
            path=[source] if return_path else None,
            runtime=runtime,
            success=True,
            reachable=True,
            counters=counters,
            metadata={"reason": "source equals target"},
        )

    # Determine heuristic
    if heuristic is None:
        if source in graph.coords and target in graph.coords:
            h_fn = euclidean_heuristic(graph)
        else:
            h_fn = zero_heuristic
    else:
        h_fn = heuristic

    g_score: Dict[Any, float] = {source: 0.0}
    pred: Dict[Any, Any] = {}
    visited = set()

    h_source = h_fn(source, target)
    entry_id = 0
    # PQ entries: (f_score, h_score, entry_id, node)
    pq: List[tuple[float, float, int, Any]] = [(h_source, h_source, entry_id, source)]
    counters.heap_pushes += 1

    target_found = False

    while pq:
        f_u, h_u, _, u = heapq.heappop(pq)
        counters.heap_pops += 1

        if u in visited:
            continue

        visited.add(u)
        counters.nodes_expanded += 1

        if u == target:
            target_found = True
            break

        g_u = g_score[u]

        for v, weight in graph.neighbors(u).items():
            counters.edges_examined += 1

            if weight < 0:
                raise ValueError(
                    f"A* does not support negative edge weights: edge ({u}, {v}) has weight {weight}."
                )

            if v in visited:
                continue

            tentative_g = g_u + weight
            if tentative_g < g_score.get(v, math.inf):
                g_score[v] = tentative_g
                pred[v] = u
                counters.relaxations += 1

                h_v = h_fn(v, target)
                f_v = tentative_g + h_v
                entry_id += 1
                heapq.heappush(pq, (f_v, h_v, entry_id, v))
                counters.heap_pushes += 1

    runtime = time.perf_counter() - start_time

    if not target_found or target not in g_score:
        return SearchResult(
            distance=math.inf,
            path=None,
            runtime=runtime,
            success=True,
            reachable=False,
            counters=counters,
            metadata={"reason": "target unreachable"},
        )

    final_dist = g_score[target]
    path: Optional[List[Any]] = None
    if return_path:
        curr = target
        path = [curr]
        while curr != source:
            curr = pred[curr]
            path.append(curr)
        path.reverse()

    return SearchResult(
        distance=final_dist,
        path=path,
        runtime=runtime,
        success=True,
        reachable=True,
        counters=counters,
    )
