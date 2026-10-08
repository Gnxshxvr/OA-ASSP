"""Deterministic query generator for reachable source-target workloads."""

from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib
import math
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Set

from oa_assp.graphs.base import Graph


@dataclass
class Query:
    """Structured query representation."""

    query_id: str
    graph_id: str
    source: Any
    target: Any
    seed: int
    source_degree: int
    target_degree: int
    query_distance_value: float
    query_distance_category: str  # "short", "medium", "long"
    euclidean_distance: Optional[float] = None
    relative_query_distance: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _derive_seed(global_seed: int, graph_id: str) -> int:
    """Deterministically derive a 32-bit integer seed from global_seed and graph_id."""
    raw = f"{global_seed}_{graph_id}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16)


def _get_undirected_components(graph: Graph) -> List[List[Any]]:
    """Compute connected components of an undirected graph."""
    visited = set()
    components = []
    for node in graph.nodes:
        if node not in visited:
            comp = []
            queue = [node]
            visited.add(node)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for nbr in graph.neighbors(curr):
                    if nbr not in visited:
                        visited.add(nbr)
                        queue.append(nbr)
            components.append(comp)
    return components


def _bfs_hop_distance(graph: Graph, source: Any, target: Any) -> float:
    """Compute unweighted shortest path hop distance from source to target."""
    if source == target:
        return 0.0
    queue = [(source, 0)]
    visited = {source}
    while queue:
        curr, d = queue.pop(0)
        if curr == target:
            return float(d)
        for nbr in graph.neighbors(curr):
            if nbr not in visited:
                visited.add(nbr)
                queue.append((nbr, d + 1))
    return math.inf


def generate_query_workload(
    graph: Graph,
    count: int = 500,
    global_seed: int = 2001,
    short_percentile: float = 0.25,
    long_percentile: float = 0.75,
) -> List[Query]:
    """Generate a single deterministic sequence of reachable queries for a graph.

    Parameters
    ----------
    graph : Graph
        Input graph.
    count : int, optional
        Number of queries to generate (Q_max), by default 500.
    global_seed : int, optional
        Master seed for query generation, by default 2001.
    short_percentile : float, optional
        Quantile boundary for 'short' queries, by default 0.25.
    long_percentile : float, optional
        Quantile boundary for 'long' queries, by default 0.75.

    Returns
    -------
    List[Query]
        Deterministic sequence of reachable queries with distance metadata.
    """
    if count < 1:
        return []

    query_seed = _derive_seed(global_seed, graph.graph_id or "default_graph")
    rng = np.random.default_rng(query_seed)

    # 1. Identify reachable node pairs
    if not graph.directed:
        components = _get_undirected_components(graph)
        valid_components = [c for c in components if len(c) >= 2]
        if not valid_components:
            raise ValueError("Graph has no connected components with at least 2 vertices.")

        comp_sizes = np.array([len(c) for c in valid_components], dtype=float)
        comp_probs = comp_sizes / comp_sizes.sum()

        raw_pairs = []
        for _ in range(count):
            comp_idx = rng.choice(len(valid_components), p=comp_probs)
            comp = valid_components[comp_idx]
            s, t = rng.choice(comp, size=2, replace=False)
            raw_pairs.append((s, t))
    else:
        # Directed graph: sample s, find reachable set R(s), sample t in R(s)
        nodes = list(graph.nodes)
        raw_pairs = []
        attempts = 0
        max_attempts = count * 50
        while len(raw_pairs) < count and attempts < max_attempts:
            attempts += 1
            s = rng.choice(nodes)
            # Find reachable nodes via BFS
            reachable = []
            queue = [s]
            visited = {s}
            while queue:
                curr = queue.pop(0)
                for nbr in graph.neighbors(curr):
                    if nbr not in visited:
                        visited.add(nbr)
                        queue.append(nbr)
                        reachable.append(nbr)
            if reachable:
                t = rng.choice(reachable)
                raw_pairs.append((s, t))

        if len(raw_pairs) < count:
            raise ValueError(
                f"Could only find {len(raw_pairs)} reachable directed pairs after {attempts} attempts."
            )

    # 2. Compute distance proxy for each pair
    is_geometric = bool(graph.coords)
    distance_values = []
    euc_distances = []

    for s, t in raw_pairs:
        if is_geometric and s in graph.coords and t in graph.coords:
            c_s = graph.coords[s]
            c_t = graph.coords[t]
            euc_d = math.sqrt(sum((a - b) ** 2 for a, b in zip(c_s, c_t)))
            distance_values.append(euc_d)
            euc_distances.append(euc_d)
        else:
            hop_d = _bfs_hop_distance(graph, s, t)
            distance_values.append(hop_d)
            euc_distances.append(None)

    # 3. Determine quantile boundaries for categorization
    dist_arr = np.array(distance_values, dtype=float)
    p_short = float(np.percentile(dist_arr, short_percentile * 100))
    p_long = float(np.percentile(dist_arr, long_percentile * 100))
    max_d = float(np.max(dist_arr)) if len(dist_arr) > 0 and np.max(dist_arr) > 0 else 1.0

    queries: List[Query] = []
    for idx, (s, t) in enumerate(raw_pairs):
        d_val = distance_values[idx]
        if d_val <= p_short:
            category = "short"
        elif d_val >= p_long:
            category = "long"
        else:
            category = "medium"

        rel_dist = float(d_val / max_d) if max_d > 0 else 0.0

        q = Query(
            query_id=f"{graph.graph_id}_q{idx:04d}",
            graph_id=graph.graph_id,
            source=s,
            target=t,
            seed=query_seed,
            source_degree=graph.degree(s),
            target_degree=graph.degree(t),
            query_distance_value=float(d_val),
            query_distance_category=category,
            euclidean_distance=euc_distances[idx],
            relative_query_distance=rel_dist,
        )
        queries.append(q)

    return queries
