"""Bidirectional Dijkstra exact single-pair shortest-path algorithm."""

from __future__ import annotations
import heapq
import math
import time
from typing import Any, Dict, List, Optional

from oa_assp.algorithms.base import OperationCounters, SearchResult
from oa_assp.graphs.base import Graph


def bidirectional_dijkstra(
    graph: Graph,
    source: Any,
    target: Any,
    return_path: bool = True,
) -> SearchResult:
    """Compute exact shortest path using Bidirectional Dijkstra.

    Simultaneously searches forward from source and backward from target.
    Guaranteed to return the exact shortest path for non-negative edge weights.

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

    # Forward search structures
    dist_f: Dict[Any, float] = {source: 0.0}
    pred_f: Dict[Any, Any] = {}
    visited_f = set()
    entry_f = 0
    pq_f: List[tuple[float, int, Any]] = [(0.0, entry_f, source)]
    counters.heap_pushes += 1

    # Backward search structures
    dist_b: Dict[Any, float] = {target: 0.0}
    pred_b: Dict[Any, Any] = {}
    visited_b = set()
    entry_b = 0
    pq_b: List[tuple[float, int, Any]] = [(0.0, entry_b, target)]
    counters.heap_pushes += 1

    mu = math.inf  # best path length seen so far
    best_meeting_node: Optional[Any] = None

    while pq_f and pq_b:
        min_f = pq_f[0][0]
        min_b = pq_b[0][0]

        # Termination condition: no shorter path can exist
        if min_f + min_b >= mu:
            break

        # Balance search frontiers: expand side with smaller min-key
        if min_f <= min_b:
            # Expand forward
            d_u, _, u = heapq.heappop(pq_f)
            counters.heap_pops += 1

            if u in visited_f:
                continue

            visited_f.add(u)
            counters.forward_expansions += 1
            counters.nodes_expanded += 1

            # Check if u is already reached in backward search
            if u in dist_b:
                cand = d_u + dist_b[u]
                if cand < mu:
                    mu = cand
                    best_meeting_node = u

            for v, weight in graph.neighbors(u).items():
                counters.edges_examined += 1

                if weight < 0:
                    raise ValueError(
                        f"Bidirectional Dijkstra does not support negative weights: edge ({u}, {v}) has weight {weight}."
                    )

                if v in visited_f:
                    continue

                new_dist = d_u + weight
                if new_dist < dist_f.get(v, math.inf):
                    dist_f[v] = new_dist
                    pred_f[v] = u
                    counters.relaxations += 1
                    entry_f += 1
                    heapq.heappush(pq_f, (new_dist, entry_f, v))
                    counters.heap_pushes += 1

                    if v in dist_b:
                        cand = new_dist + dist_b[v]
                        if cand < mu:
                            mu = cand
                            best_meeting_node = v
        else:
            # Expand backward
            d_v, _, v = heapq.heappop(pq_b)
            counters.heap_pops += 1

            if v in visited_b:
                continue

            visited_b.add(v)
            counters.backward_expansions += 1
            counters.nodes_expanded += 1

            # Check if v is already reached in forward search
            if v in dist_f:
                cand = dist_f[v] + d_v
                if cand < mu:
                    mu = cand
                    best_meeting_node = v

            for u, weight in graph.in_neighbors(v).items():
                counters.edges_examined += 1

                if weight < 0:
                    raise ValueError(
                        f"Bidirectional Dijkstra does not support negative weights: edge ({u}, {v}) has weight {weight}."
                    )

                if u in visited_b:
                    continue

                new_dist = d_v + weight
                if new_dist < dist_b.get(u, math.inf):
                    dist_b[u] = new_dist
                    pred_b[u] = v
                    counters.relaxations += 1
                    entry_b += 1
                    heapq.heappush(pq_b, (new_dist, entry_b, u))
                    counters.heap_pushes += 1

                    if u in dist_f:
                        cand = dist_f[u] + new_dist
                        if cand < mu:
                            mu = cand
                            best_meeting_node = u

    runtime = time.perf_counter() - start_time

    if math.isinf(mu) or best_meeting_node is None:
        return SearchResult(
            distance=math.inf,
            path=None,
            runtime=runtime,
            success=True,
            reachable=False,
            counters=counters,
            metadata={"reason": "target unreachable"},
        )

    path: Optional[List[Any]] = None
    if return_path:
        # Reconstruct path: source -> ... -> best_meeting_node
        path_f = [best_meeting_node]
        curr = best_meeting_node
        while curr != source:
            curr = pred_f[curr]
            path_f.append(curr)
        path_f.reverse()

        # Reconstruct path: best_meeting_node -> ... -> target
        path_b = []
        curr = best_meeting_node
        while curr != target:
            curr = pred_b[curr]
            path_b.append(curr)

        path = path_f + path_b

    return SearchResult(
        distance=mu,
        path=path,
        runtime=runtime,
        success=True,
        reachable=True,
        counters=counters,
        metadata={"meeting_node": best_meeting_node},
    )
