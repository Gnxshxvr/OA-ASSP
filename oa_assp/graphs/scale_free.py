"""Controlled scale-free graph generator (Barabasi-Albert preferential attachment)."""

from __future__ import annotations
import math
import numpy as np
from typing import Optional

from oa_assp.graphs.base import Graph


def generate_scale_free_graph(
    num_vertices: int,
    average_degree: float,
    seed: int,
    directed: bool = False,
) -> Graph:
    """Generate a scale-free graph using Barabasi-Albert preferential attachment.

    Parameters
    ----------
    num_vertices : int
        Number of vertices V.
    average_degree : float
        Target average degree (attachment parameter m = round(average_degree / 2)).
    seed : int
        Random seed for reproducibility.
    directed : bool, optional
        Whether the graph is directed, by default False.

    Returns
    -------
    Graph
        Generated scale-free graph with metadata.
    """
    if num_vertices < 1:
        raise ValueError("num_vertices must be at least 1.")
    if average_degree < 0:
        raise ValueError("average_degree must be non-negative.")

    rng = np.random.default_rng(seed)
    graph_id = f"scalefree_V{num_vertices}_D{int(round(average_degree))}_s{seed}"
    g = Graph(directed=directed, graph_id=graph_id)

    for i in range(num_vertices):
        g.add_node(i)

    if num_vertices == 1 or average_degree == 0:
        g.metadata = {
            "graph_family": "scale_free",
            "seed": seed,
            "num_vertices": num_vertices,
            "num_edges": 0,
            "target_average_degree": average_degree,
            "actual_average_degree": 0.0,
            "directed": directed,
            "attachment_m": 0,
        }
        return g

    # Attachment parameter m
    if not directed:
        m = max(1, int(round(average_degree / 2.0)))
    else:
        m = max(1, int(round(average_degree)))

    # Initial core: clique of m + 1 nodes (or all nodes if V <= m + 1)
    m0 = min(num_vertices, m + 1)
    repeated_nodes = []

    for u in range(m0):
        for v in range(u + 1, m0):
            g.add_edge(u, v, weight=1.0, bidirectional=(not directed))
            repeated_nodes.extend([u, v])
            if directed:
                repeated_nodes.extend([u, v])

    # Preferential attachment for remaining nodes
    for u in range(m0, num_vertices):
        targets = set()
        # Sample m distinct targets from repeated_nodes
        # Fallback to all existing nodes if repeated_nodes doesn't have enough distinct
        if len(set(repeated_nodes)) <= m:
            targets = set(range(u))
        else:
            while len(targets) < m:
                chosen = int(rng.choice(repeated_nodes))
                if chosen != u:
                    targets.add(chosen)

        for v in targets:
            g.add_edge(u, v, weight=1.0, bidirectional=(not directed))
            repeated_nodes.append(u)
            repeated_nodes.append(v)

    actual_e = g.num_edges // 2 if not directed else g.num_edges
    actual_d = (2.0 * actual_e / num_vertices) if not directed else (float(actual_e) / num_vertices)

    g.metadata = {
        "graph_family": "scale_free",
        "seed": seed,
        "num_vertices": num_vertices,
        "num_edges": actual_e,
        "target_average_degree": average_degree,
        "actual_average_degree": actual_d,
        "directed": directed,
        "attachment_m": m,
    }

    return g
