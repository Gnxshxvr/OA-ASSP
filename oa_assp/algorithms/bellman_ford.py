"""Bellman-Ford exact shortest-path algorithm with negative weight support."""

from __future__ import annotations
import math
import time
from typing import Any, Dict, List, Optional

from oa_assp.algorithms.base import OperationCounters, SearchResult
from oa_assp.graphs.base import Graph


def bellman_ford(
    graph: Graph,
    source: Any,
    target: Any,
    return_path: bool = True,
) -> SearchResult:
    """Compute shortest path using Bellman-Ford algorithm.

    Supports negative edge weights and detects negative cycles reachable from source.

    Parameters
    ----------
    graph : Graph
        Input graph (can have negative edge weights).
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
    num_nodes = graph.num_nodes

    # Relax edges repeatedly up to |V| - 1 times
    all_edges = list(graph.edges())

    for _ in range(num_nodes - 1):
        counters.passes += 1
        relaxed_in_pass = False

        for u, v, weight in all_edges:
            if u not in dist:
                continue

            counters.edge_scans += 1
            new_dist = dist[u] + weight
            if new_dist < dist.get(v, math.inf):
                dist[v] = new_dist
                pred[v] = u
                counters.relaxations += 1
                relaxed_in_pass = True

        if not relaxed_in_pass:
            break

    # Check for negative weight cycles
    negative_cycle_nodes = set()
    for u, v, weight in all_edges:
        if u not in dist:
            continue
        if dist[u] + weight < dist.get(v, math.inf):
            negative_cycle_nodes.add(v)

    negative_cycle_affects_target = False
    if negative_cycle_nodes:
        # Determine if target is reachable from any node in a negative cycle
        visited = set(negative_cycle_nodes)
        queue = list(negative_cycle_nodes)
        while queue:
            curr = queue.pop(0)
            if curr == target:
                negative_cycle_affects_target = True
                break
            for nbr in graph.neighbors(curr):
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append(nbr)

    runtime = time.perf_counter() - start_time

    if negative_cycle_affects_target:
        return SearchResult(
            distance=-math.inf,
            path=None,
            runtime=runtime,
            success=True,
            reachable=True,
            counters=counters,
            metadata={"negative_cycle": True, "reason": "negative cycle affects target"},
        )

    if target not in dist or math.isinf(dist[target]):
        return SearchResult(
            distance=math.inf,
            path=None,
            runtime=runtime,
            success=True,
            reachable=False,
            counters=counters,
            metadata={"negative_cycle": len(negative_cycle_nodes) > 0, "reason": "target unreachable"},
        )

    final_dist = dist[target]
    path: Optional[List[Any]] = None
    if return_path:
        curr = target
        path = [curr]
        visited_nodes = {curr}
        has_cycle = False
        while curr != source:
            curr = pred.get(curr)
            if curr is None:
                has_cycle = True
                break
            if curr in visited_nodes:
                has_cycle = True
                break
            visited_nodes.add(curr)
            path.append(curr)

        if has_cycle:
            path = None
        else:
            path.reverse()

    return SearchResult(
        distance=final_dist,
        path=path,
        runtime=runtime,
        success=True,
        reachable=True,
        counters=counters,
        metadata={"negative_cycle": len(negative_cycle_nodes) > 0},
    )
