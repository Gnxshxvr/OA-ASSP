"""Controlled geometric graph generator with 2D coordinates."""

from __future__ import annotations
import math
import numpy as np
from scipy.spatial import KDTree
from typing import Optional

from oa_assp.graphs.base import Graph


def generate_geometric_graph(
    num_vertices: int,
    average_degree: float,
    seed: int,
    directed: bool = False,
    mechanism: str = "knn",
) -> Graph:
    """Generate a geometric graph with 2D coordinates and controlled connectivity.

    Parameters
    ----------
    num_vertices : int
        Number of vertices V.
    average_degree : float
        Target average degree.
    seed : int
        Random seed for reproducibility.
    directed : bool, optional
        Whether the graph is directed, by default False.
    mechanism : str, optional
        Edge connection rule: 'knn' (k-nearest neighbors) or 'radius', by default 'knn'.

    Returns
    -------
    Graph
        Generated geometric graph with coordinates and metadata.
    """
    if num_vertices < 1:
        raise ValueError("num_vertices must be at least 1.")
    if average_degree < 0:
        raise ValueError("average_degree must be non-negative.")

    rng = np.random.default_rng(seed)
    graph_id = f"geometric_V{num_vertices}_D{int(round(average_degree))}_s{seed}"
    g = Graph(directed=directed, graph_id=graph_id)

    # Generate 2D coordinates uniformly in [0, 1] x [0, 1]
    coords = rng.uniform(0.0, 1.0, size=(num_vertices, 2))
    for i in range(num_vertices):
        g.add_node(i, coords=(float(coords[i, 0]), float(coords[i, 1])))

    if num_vertices == 1 or average_degree == 0:
        g.metadata = {
            "graph_family": "geometric",
            "seed": seed,
            "num_vertices": num_vertices,
            "num_edges": 0,
            "target_average_degree": average_degree,
            "actual_average_degree": 0.0,
            "directed": directed,
            "mechanism": mechanism,
        }
        return g

    tree = KDTree(coords)

    if mechanism == "knn":
        # k-nearest neighbors
        if not directed:
            k = max(1, int(round(average_degree / 2.0)))
        else:
            k = max(1, int(round(average_degree)))
        k_query = min(num_vertices, k + 1)  # +1 because query includes the point itself

        _, indices = tree.query(coords, k=k_query)
        # indices is (N, k_query)
        for u in range(num_vertices):
            row = indices[u] if k_query > 1 else [indices[u]]
            for v in row:
                if u == v:
                    continue
                g.add_edge(u, int(v), weight=1.0, bidirectional=(not directed))

    elif mechanism == "radius":
        # Radius based connection
        # Expected degree in 2D unit square: d ≈ (V - 1) * pi * r^2
        r = math.sqrt(average_degree / (math.pi * max(1, num_vertices - 1)))
        pairs = tree.query_pairs(r)
        for u, v in pairs:
            if directed:
                # Add random direction or both
                g.add_edge(u, v, weight=1.0, bidirectional=False)
            else:
                g.add_edge(u, v, weight=1.0, bidirectional=True)
    else:
        raise ValueError(f"Unknown geometric mechanism: {mechanism}. Choose 'knn' or 'radius'.")

    actual_e = g.num_edges // 2 if not directed else g.num_edges
    actual_d = (2.0 * actual_e / num_vertices) if not directed else (float(actual_e) / num_vertices)

    g.metadata = {
        "graph_family": "geometric",
        "seed": seed,
        "num_vertices": num_vertices,
        "num_edges": actual_e,
        "target_average_degree": average_degree,
        "actual_average_degree": actual_d,
        "directed": directed,
        "mechanism": mechanism,
    }

    return g
