"""Controlled edge weight assignment for OA-ASSP graphs."""

from __future__ import annotations
import math
import numpy as np
from typing import Optional

from oa_assp.graphs.base import Graph


def assign_positive_random_weights(
    graph: Graph,
    min_weight: float = 1.0,
    max_weight: float = 100.0,
    seed: int = 42,
) -> None:
    """Assign strictly positive random uniform edge weights to a graph.

    For undirected graphs, weights are symmetrically assigned: w(u, v) == w(v, u).
    """
    if min_weight <= 0:
        raise ValueError("min_weight must be strictly positive (> 0).")
    if max_weight < min_weight:
        raise ValueError("max_weight must be greater than or equal to min_weight.")

    rng = np.random.default_rng(seed)
    assigned_edges = set()

    for u in list(graph.adj.keys()):
        for v in list(graph.adj[u].keys()):
            edge_key = (min(u, v), max(u, v)) if not graph.directed else (u, v)
            if edge_key not in assigned_edges:
                w = float(rng.uniform(min_weight, max_weight))
                assigned_edges.add(edge_key)
                graph.adj[u][v] = w
                graph.rev_adj[v][u] = w
                if not graph.directed:
                    graph.adj[v][u] = w
                    graph.rev_adj[u][v] = w

    graph.metadata.update({
        "weight_model": "positive_random",
        "weight_parameter": None,
        "weight_min": min_weight,
        "weight_max": max_weight,
        "epsilon": 0.0,
        "heuristic_available": False,
        "heuristic_valid": False,
        "heuristic_type": None,
        "heuristic_admissible": False,
    })


def assign_geometric_weights(
    graph: Graph,
    c: float = 1.0,
    epsilon: float = 0.1,
    noise_epsilon: float = 0.0,
    seed: int = 42,
) -> None:
    """Assign geometric edge weights: w(u, v) = c * euclidean_dist(u, v) + epsilon + noise.

    Parameters
    ----------
    graph : Graph
        Graph with node coordinates in graph.coords.
    c : float, optional
        Multiplier for Euclidean distance (e.g. 1.0, 1.25, 1.5, 2.0, 3.0), by default 1.0.
    epsilon : float, optional
        Additive constant term (>= 0), by default 0.1.
    noise_epsilon : float, optional
        Magnitude of non-negative uniform noise added, by default 0.0.
    seed : int, optional
        Random seed for noise generation, by default 42.
    """
    if not graph.coords:
        raise ValueError("Cannot assign geometric weights: graph has no node coordinates.")
    if c <= 0:
        raise ValueError("c must be strictly positive (> 0).")
    if epsilon < 0:
        raise ValueError("epsilon must be non-negative (>= 0).")

    rng = np.random.default_rng(seed)
    coords = graph.coords
    assigned_edges = set()

    for u in list(graph.adj.keys()):
        for v in list(graph.adj[u].keys()):
            edge_key = (min(u, v), max(u, v)) if not graph.directed else (u, v)
            if edge_key not in assigned_edges:
                c_u = coords[u]
                c_v = coords[v]
                euc_d = math.sqrt(sum((a - b) ** 2 for a, b in zip(c_u, c_v)))
                noise = float(rng.uniform(0.0, noise_epsilon)) if noise_epsilon > 0 else 0.0
                w = float(c * euc_d + epsilon + noise)

                assigned_edges.add(edge_key)
                graph.adj[u][v] = w
                graph.rev_adj[v][u] = w
                if not graph.directed:
                    graph.adj[v][u] = w
                    graph.rev_adj[u][v] = w

    # Heuristic admissibility:
    # When c >= 1.0 and epsilon >= 0, standard Euclidean distance d(u, t) <= w(u, t)
    # is provably admissible and monotonic (consistent).
    heuristic_admissible = (c >= 1.0 and epsilon >= 0.0)
    heuristic_scaling = 1.0 if heuristic_admissible else c

    graph.metadata.update({
        "weight_model": "geometric",
        "weight_parameter": c,
        "epsilon": epsilon,
        "noise_epsilon": noise_epsilon,
        "heuristic_available": True,
        "heuristic_valid": heuristic_admissible,
        "heuristic_type": "euclidean",
        "heuristic_admissible": heuristic_admissible,
        "heuristic_scaling": heuristic_scaling,
    })


def assign_negative_weights(
    graph: Graph,
    negative_fraction: float = 0.1,
    min_neg: float = -5.0,
    max_pos: float = 10.0,
    seed: int = 42,
) -> None:
    """Assign mixed weights with a controlled fraction of negative edges (for Bellman-Ford tests)."""
    rng = np.random.default_rng(seed)
    assigned_edges = set()

    for u in list(graph.adj.keys()):
        for v in list(graph.adj[u].keys()):
            edge_key = (min(u, v), max(u, v)) if not graph.directed else (u, v)
            if edge_key not in assigned_edges:
                is_neg = (rng.uniform() < negative_fraction)
                if is_neg:
                    w = float(rng.uniform(min_neg, -0.1))
                else:
                    w = float(rng.uniform(0.1, max_pos))

                assigned_edges.add(edge_key)
                graph.adj[u][v] = w
                graph.rev_adj[v][u] = w
                if not graph.directed:
                    graph.adj[v][u] = w
                    graph.rev_adj[u][v] = w

    graph.metadata.update({
        "weight_model": "mixed_negative",
        "negative_fraction": negative_fraction,
        "heuristic_available": False,
        "heuristic_admissible": False,
    })
