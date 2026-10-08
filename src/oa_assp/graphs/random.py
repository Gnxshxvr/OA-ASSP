"""Controlled random graph generator (Erdos-Renyi / G(V, M) style)."""

from __future__ import annotations
import math
import numpy as np
from typing import Optional

from oa_assp.graphs.base import Graph


def generate_random_graph(
    num_vertices: int,
    average_degree: float,
    seed: int,
    directed: bool = False,
) -> Graph:
    """Generate a random graph with controlled vertex count and average degree.

    Parameters
    ----------
    num_vertices : int
        Number of vertices V.
    average_degree : float
        Target average degree d_bar = 2E / V (for undirected) or E / V (for directed).
    seed : int
        Random seed for reproducibility.
    directed : bool, optional
        Whether the graph is directed, by default False.

    Returns
    -------
    Graph
        Generated graph with metadata.
    """
    if num_vertices < 1:
        raise ValueError("num_vertices must be at least 1.")
    if average_degree < 0:
        raise ValueError("average_degree must be non-negative.")

    rng = np.random.default_rng(seed)
    graph_id = f"random_V{num_vertices}_D{int(round(average_degree))}_s{seed}"
    g = Graph(directed=directed, graph_id=graph_id)

    for i in range(num_vertices):
        g.add_node(i)

    if num_vertices == 1 or average_degree == 0:
        g.metadata = {
            "graph_family": "random",
            "seed": seed,
            "num_vertices": num_vertices,
            "num_edges": 0,
            "target_average_degree": average_degree,
            "actual_average_degree": 0.0,
            "directed": directed,
        }
        return g

    if not directed:
        max_edges = num_vertices * (num_vertices - 1) // 2
        target_edges = min(max_edges, int(round(num_vertices * average_degree / 2.0)))
    else:
        max_edges = num_vertices * (num_vertices - 1)
        target_edges = min(max_edges, int(round(num_vertices * average_degree)))

    # Select unique edges
    edge_set = set()
    # If dense, can generate all possible edges and choice
    if max_edges > 0 and target_edges >= max_edges * 0.5:
        all_possible = []
        for u in range(num_vertices):
            for v in range(u + 1 if not directed else 0, num_vertices):
                if directed and u == v:
                    continue
                all_possible.append((u, v))
        chosen_indices = rng.choice(len(all_possible), size=target_edges, replace=False)
        for idx in chosen_indices:
            u, v = all_possible[idx]
            g.add_edge(u, v, weight=1.0, bidirectional=(not directed))
    else:
        # Sparse sampling
        batch_size = max(100, target_edges * 2)
        while len(edge_set) < target_edges:
            needed = target_edges - len(edge_set)
            u_samples = rng.integers(0, num_vertices, size=needed * 2)
            v_samples = rng.integers(0, num_vertices, size=needed * 2)
            for u, v in zip(u_samples, v_samples):
                if u == v:
                    continue
                edge = (min(u, v), max(u, v)) if not directed else (u, v)
                if edge not in edge_set:
                    edge_set.add(edge)
                    g.add_edge(edge[0], edge[1], weight=1.0, bidirectional=(not directed))
                    if len(edge_set) == target_edges:
                        break

    actual_e = g.num_edges // 2 if not directed else g.num_edges
    actual_d = (2.0 * actual_e / num_vertices) if not directed else (float(actual_e) / num_vertices)

    g.metadata = {
        "graph_family": "random",
        "seed": seed,
        "num_vertices": num_vertices,
        "num_edges": actual_e,
        "target_average_degree": average_degree,
        "actual_average_degree": actual_d,
        "directed": directed,
    }

    return g
