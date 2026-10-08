"""Tier 0 — O(1) feature extraction from pre-stored graph and query metadata."""

from __future__ import annotations
import time
from typing import Any, Dict, Tuple

from oa_assp.graphs.base import Graph
from oa_assp.graphs.queries import Query


def extract_tier_0_graph_features(graph: Graph) -> Tuple[Dict[str, float], float]:
    """Extract Tier 0 graph-level features in O(1) time.

    Returns
    -------
    Tuple[Dict[str, float], float]
        Dictionary of feature values and wall-clock execution duration in seconds.
    """
    t0 = time.perf_counter()

    num_v = float(graph.num_nodes)
    num_e = float(graph.metadata.get("num_edges", graph.num_edges))
    avg_d = float(graph.metadata.get("actual_average_degree", (2.0 * num_e / num_v) if num_v > 0 else 0.0))
    has_coords = 1.0 if bool(graph.coords) else 0.0

    features = {
        "num_vertices": num_v,
        "num_edges": num_e,
        "average_degree": avg_d,
        "heuristic_available": has_coords,
    }

    elapsed = time.perf_counter() - t0
    return features, elapsed


def extract_tier_0_query_features(graph: Graph, query: Query) -> Tuple[Dict[str, float], float]:
    """Extract Tier 0 query-level features in O(1) time.

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

    features = {
        "source_degree": s_deg,
        "target_degree": t_deg,
    }

    elapsed = time.perf_counter() - t0
    return features, elapsed
