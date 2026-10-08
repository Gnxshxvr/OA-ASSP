"""Tier 2 — Structural topology features (clustering coefficient, approximate diameter)."""

from __future__ import annotations
import numpy as np
import time
from typing import Any, Dict, List, Tuple

from oa_assp.graphs.base import Graph


def _compute_clustering_coefficient(graph: Graph, sample_limit: int = 300) -> float:
    """Compute average local clustering coefficient (sampled if graph is very large)."""
    nodes = list(graph.nodes)
    if not nodes:
        return 0.0

    if len(nodes) > sample_limit:
        # Deterministic sampling
        step = len(nodes) // sample_limit
        eval_nodes = nodes[::step][:sample_limit]
    else:
        eval_nodes = nodes

    coeffs = []
    for u in eval_nodes:
        nbrs = set(graph.neighbors(u).keys())
        k = len(nbrs)
        if k < 2:
            coeffs.append(0.0)
            continue

        # Count edges between neighbors
        edges_between = 0
        for n1 in nbrs:
            for n2 in graph.neighbors(n1):
                if n2 in nbrs and n1 != n2:
                    edges_between += 1

        # For directed: k * (k - 1) possible directed edges
        # For undirected: edges_between is counted twice, k * (k - 1) / 2 possible edges
        possible = float(k * (k - 1))
        coeffs.append(edges_between / possible if possible > 0 else 0.0)

    return float(np.mean(coeffs)) if coeffs else 0.0


def _compute_approx_diameter(graph: Graph) -> float:
    """Compute approximate diameter via 2-sweep BFS on the largest component."""
    nodes = list(graph.nodes)
    if len(nodes) <= 1:
        return 0.0

    # Start from node with maximum degree
    start_node = max(nodes, key=lambda u: graph.degree(u))

    def _bfs_farthest(start: Any) -> Tuple[Any, int]:
        queue = [(start, 0)]
        visited = {start}
        farthest_node = start
        max_dist = 0
        while queue:
            curr, d = queue.pop(0)
            if d > max_dist:
                max_dist = d
                farthest_node = curr
            for nbr in graph.neighbors(curr):
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append((nbr, d + 1))
        return farthest_node, max_dist

    # Sweep 1
    node_a, _ = _bfs_farthest(start_node)
    # Sweep 2
    _, diam_approx = _bfs_farthest(node_a)

    return float(diam_approx)


def extract_tier_2_graph_features(graph: Graph) -> Tuple[Dict[str, float], float]:
    """Extract Tier 2 structural graph-level features.

    Returns
    -------
    Tuple[Dict[str, float], float]
        Dictionary of feature values and wall-clock execution duration in seconds.
    """
    t0 = time.perf_counter()

    clustering = _compute_clustering_coefficient(graph)
    diameter = _compute_approx_diameter(graph)

    features = {
        "clustering_coefficient": clustering,
        "approx_diameter": diameter,
    }

    elapsed = time.perf_counter() - t0
    return features, elapsed
