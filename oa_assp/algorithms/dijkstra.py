"""Dijkstra's exact single-pair shortest-path algorithm."""

from __future__ import annotations
import heapq
import math
import time
from typing import Any, Dict, List, Optional

from oa_assp.algorithms.base import OperationCounters, SearchResult
from oa_assp.graphs.base import Graph


def dijkstra(
    graph: Graph,
    source: Any,
    target: Any,
    return_path: bool = True,
) -> SearchResult:
    """Compute the exact shortest path from source to target using Dijkstra's algorithm.

    Parameters
    ----------
    graph : Graph
        Input graph with non-negative edge weights.
    source : Any
        Source node identifier.
    target : Any
        Target node identifier.
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

    dist: Dict[Any, float] = {source: 0.0}
    pred: Dict[Any, Any] = {}
    visited = set()

    # Priority queue stores tuples of (distance, entry_id, node)
    entry_id = 0
    pq: List[tuple[float, int, Any]] = [(0.0, entry_id, source)]
    counters.heap_pushes += 1

    target_found = False

    while pq:
        d_u, _, u = heapq.heappop(pq)
        counters.heap_pops += 1

        if u in visited:
            continue

        visited.add(u)
        counters.nodes_expanded += 1

        if u == target:
            target_found = True
            break

        for v, weight in graph.neighbors(u).items():
            counters.edges_examined += 1

            if weight < 0:
                raise ValueError(
                    f"Dijkstra does not support negative edge weights: edge ({u}, {v}) has weight {weight}."
                )

            if v in visited:
                continue

            new_dist = d_u + weight
            if new_dist < dist.get(v, math.inf):
                dist[v] = new_dist
                pred[v] = u
                counters.relaxations += 1
                entry_id += 1
                heapq.heappush(pq, (new_dist, entry_id, v))
                counters.heap_pushes += 1

    runtime = time.perf_counter() - start_time

    if not target_found or target not in dist:
        return SearchResult(
            distance=math.inf,
            path=None,
            runtime=runtime,
            success=True,
            reachable=False,
            counters=counters,
            metadata={"reason": "target unreachable"},
        )

    final_dist = dist[target]
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
