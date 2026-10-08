"""Tier 1 — O(V+E) feature extraction requiring a single linear graph scan."""

from __future__ import annotations
import math
import numpy as np
import time
from typing import Any, Dict, Tuple

from oa_assp.graphs.base import Graph
from oa_assp.graphs.queries import Query


def extract_tier_1_graph_features(graph: Graph) -> Tuple[Dict[str, float], float]:
    """Extract Tier 1 graph-level features via a single scan over nodes and edges.

    Returns
    -------
    Tuple[Dict[str, float], float]
        Dictionary of feature values and wall-clock execution duration in seconds.
    """
    t0 = time.perf_counter()

    # 1. Degree statistics
    degrees = [float(graph.degree(u)) for u in graph.nodes]
    if degrees:
        deg_arr = np.array(degrees, dtype=float)
        d_mean = float(np.mean(deg_arr))
        d_var = float(np.var(deg_arr))
        d_min = float(np.min(deg_arr))
        d_max = float(np.max(deg_arr))
    else:
        d_mean, d_var, d_min, d_max = 0.0, 0.0, 0.0, 0.0

    # 2. Edge weight and heuristic quality statistics
    weights = []
    heuristic_ratios = []
    coords = graph.coords
    has_coords = bool(coords)
    neg_count = 0

    for u, v, w in graph.edges():
        weights.append(w)
        if w < 0:
            neg_count += 1
        if has_coords and u in coords and v in coords:
            c_u = coords[u]
            c_v = coords[v]
            euc_d = math.sqrt(sum((a - b) ** 2 for a, b in zip(c_u, c_v)))
            # Pre-solver ratio: Euclidean distance / edge weight
            heuristic_ratios.append(euc_d / (w + 1e-9) if w > 0 else 0.0)

    if weights:
        w_arr = np.array(weights, dtype=float)
        w_mean = float(np.mean(w_arr))
        w_var = float(np.var(w_arr))
        w_min = float(np.min(w_arr))
        w_max = float(np.max(w_arr))
        neg_frac = float(neg_count / len(weights))
    else:
        w_mean, w_var, w_min, w_max, neg_frac = 0.0, 0.0, 0.0, 0.0, 0.0

    if heuristic_ratios:
        h_arr = np.array(heuristic_ratios, dtype=float)
        h_mean = float(np.mean(h_arr))
        h_var = float(np.var(h_arr))
    else:
        h_mean, h_var = 0.0, 0.0

    features = {
        "degree_mean": d_mean,
        "degree_variance": d_var,
        "degree_min": d_min,
        "degree_max": d_max,
        "weight_mean": w_mean,
        "weight_variance": w_var,
        "weight_min": w_min,
        "weight_max": w_max,
        "negative_edge_fraction": neg_frac,
        "heuristic_quality_mean": h_mean,
        "heuristic_quality_var": h_var,
    }

    elapsed = time.perf_counter() - t0
    return features, elapsed


def extract_tier_1_query_features(graph: Graph, query: Query) -> Tuple[Dict[str, float], float]:
    """Extract Tier 1 query-level features in O(1) time without solving shortest paths.

    Returns
    -------
    Tuple[Dict[str, float], float]
        Dictionary of feature values and wall-clock execution duration in seconds.
    """
    t0 = time.perf_counter()

    s = query.source
    t = query.target
    s_deg = float(graph.degree(s))
    t_deg = float(graph.degree(t))

    coords = graph.coords
    if coords and s in coords and t in coords:
        c_s = coords[s]
        c_t = coords[t]
        euc_dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(c_s, c_t)))
        # In unit square [0, 1] x [0, 1], maximum distance is sqrt(2)
        rel_euc_dist = euc_dist / math.sqrt(2.0)
    else:
        euc_dist = 0.0
        rel_euc_dist = 0.0

    avg_d = float(graph.metadata.get("actual_average_degree", 1.0))
    deg_prod_norm = (s_deg * t_deg) / (avg_d ** 2 + 1e-9)
    deg_diff = abs(s_deg - t_deg)

    features = {
        "source_target_euclidean_distance": euc_dist,
        "relative_geometric_query_distance": rel_euc_dist,
        "degree_product_normalized": deg_prod_norm,
        "degree_difference": deg_diff,
    }

    elapsed = time.perf_counter() - t0
    return features, elapsed
