"""Feature schema, metadata definitions, and allowlist registry."""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Set


@dataclass(frozen=True)
class FeatureMetadata:
    """Metadata specification for an individual feature."""

    name: str
    scope: str  # 'graph' or 'query'
    tier: int  # 0, 1, or 2
    cost_class: str  # 'O(1)', 'O(V+E)', or 'structural'
    requires_coordinates: bool
    pre_solver: bool = True  # MUST be True for all selector inputs


# Strict allowlist of valid pre-solver features
FEATURE_REGISTRY: Dict[str, FeatureMetadata] = {
    # Tier 0 Graph
    "num_vertices": FeatureMetadata("num_vertices", "graph", 0, "O(1)", False),
    "num_edges": FeatureMetadata("num_edges", "graph", 0, "O(1)", False),
    "average_degree": FeatureMetadata("average_degree", "graph", 0, "O(1)", False),
    "heuristic_available": FeatureMetadata("heuristic_available", "graph", 0, "O(1)", False),

    # Tier 0 Query
    "source_degree": FeatureMetadata("source_degree", "query", 0, "O(1)", False),
    "target_degree": FeatureMetadata("target_degree", "query", 0, "O(1)", False),

    # Tier 1 Graph
    "degree_mean": FeatureMetadata("degree_mean", "graph", 1, "O(V+E)", False),
    "degree_variance": FeatureMetadata("degree_variance", "graph", 1, "O(V+E)", False),
    "degree_min": FeatureMetadata("degree_min", "graph", 1, "O(V+E)", False),
    "degree_max": FeatureMetadata("degree_max", "graph", 1, "O(V+E)", False),
    "weight_mean": FeatureMetadata("weight_mean", "graph", 1, "O(V+E)", False),
    "weight_variance": FeatureMetadata("weight_variance", "graph", 1, "O(V+E)", False),
    "weight_min": FeatureMetadata("weight_min", "graph", 1, "O(V+E)", False),
    "weight_max": FeatureMetadata("weight_max", "graph", 1, "O(V+E)", False),
    "negative_edge_fraction": FeatureMetadata("negative_edge_fraction", "graph", 1, "O(V+E)", False),
    "heuristic_quality_mean": FeatureMetadata("heuristic_quality_mean", "graph", 1, "O(V+E)", True),
    "heuristic_quality_var": FeatureMetadata("heuristic_quality_var", "graph", 1, "O(V+E)", True),

    # Tier 1 Query
    "source_target_euclidean_distance": FeatureMetadata("source_target_euclidean_distance", "query", 1, "O(1)", True),
    "relative_geometric_query_distance": FeatureMetadata("relative_geometric_query_distance", "query", 1, "O(1)", True),
    "degree_product_normalized": FeatureMetadata("degree_product_normalized", "query", 1, "O(1)", False),
    "degree_difference": FeatureMetadata("degree_difference", "query", 1, "O(1)", False),

    # Tier 2 Graph (Structural)
    "clustering_coefficient": FeatureMetadata("clustering_coefficient", "graph", 2, "structural", False),
    "approx_diameter": FeatureMetadata("approx_diameter", "graph", 2, "structural", False),
}


@dataclass
class ExtractedFeatures:
    """Container holding extracted features and measured extraction costs."""

    graph_id: str
    query_id: Optional[str]
    features: Dict[str, float]
    graph_feature_time: float = 0.0
    query_feature_time: float = 0.0

    @property
    def total_feature_time(self) -> float:
        return self.graph_feature_time + self.query_feature_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "query_id": self.query_id,
            "features": self.features,
            "graph_feature_time": self.graph_feature_time,
            "query_feature_time": self.query_feature_time,
            "total_feature_time": self.total_feature_time,
        }


def get_feature_names_for_tier(tier: int) -> List[str]:
    """Return all pre-solver feature names up to and including the specified tier."""
    return [name for name, meta in FEATURE_REGISTRY.items() if meta.tier <= tier and meta.pre_solver]


def get_feature_manifest() -> List[Dict[str, Any]]:
    """Return detailed manifest of all registered features."""
    manifest = []
    for name, meta in FEATURE_REGISTRY.items():
        manifest.append({
            "feature_name": meta.name,
            "tier": meta.tier,
            "scope": meta.scope,
            "cost_class": meta.cost_class,
            "requires_coordinates": meta.requires_coordinates,
            "pre_solver": meta.pre_solver,
        })
    return manifest


def calculate_feature_costs_for_workload(
    graph_feature_time: float,
    query_feature_times: List[float],
    q_values: Optional[List[int]] = None,
) -> Dict[int, Dict[str, float]]:
    """Calculate one-time, cumulative, and amortized feature costs for different workload sizes Q.

    Formula:
      C_feature(Q) = C_graph_feature + sum_{q=1}^Q C_query_feature,q
      AmortizedFeatureCost(Q) = C_feature(Q) / Q
    """
    if q_values is None:
        q_values = [1, 10, 50, 100, 500]

    results: Dict[int, Dict[str, float]] = {}
    total_available_queries = len(query_feature_times)

    for Q in q_values:
        # Evaluate up to available queries or Q
        effective_q = min(Q, total_available_queries)
        if effective_q <= 0:
            cum_query_cost = 0.0
            total_cost = graph_feature_time
            amortized = total_cost
        else:
            cum_query_cost = float(sum(query_feature_times[:effective_q]))
            # If fewer queries than Q, scale linearly for projection or use actual
            total_cost = graph_feature_time + cum_query_cost
            amortized = total_cost / effective_q

        results[Q] = {
            "Q": Q,
            "effective_q": effective_q,
            "one_time_graph_feature_cost": graph_feature_time,
            "cumulative_query_feature_cost": cum_query_cost,
            "total_feature_cost": total_cost,
            "amortized_feature_cost_per_query": amortized,
        }

    return results
