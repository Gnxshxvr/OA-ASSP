"""Master feature extractor coordinating Tier 0, Tier 1, and Tier 2 extraction."""

from __future__ import annotations
import time
from typing import Any, Dict, Optional, Tuple

from oa_assp.features.cheap import (
    extract_tier_0_graph_features,
    extract_tier_0_query_features,
)
from oa_assp.features.linear_scan import (
    extract_tier_1_graph_features,
    extract_tier_1_query_features,
)
from oa_assp.features.structural import extract_tier_2_graph_features
from oa_assp.features.schema import ExtractedFeatures, get_feature_names_for_tier
from oa_assp.graphs.base import Graph
from oa_assp.graphs.queries import Query


class FeatureExtractor:
    """Extractor for graph-level and query-level features with separate cost accounting."""

    def __init__(self, default_tier: int = 1) -> None:
        if default_tier not in (0, 1, 2):
            raise ValueError(f"Feature tier must be 0, 1, or 2, got {default_tier}.")
        self.default_tier = default_tier

    def extract_graph_features(
        self, graph: Graph, tier: Optional[int] = None
    ) -> Tuple[Dict[str, float], float]:
        """Extract graph-level features for the specified tier.

        Computed once per graph and reused across queries.
        """
        active_tier = self.default_tier if tier is None else tier
        features: Dict[str, float] = {}
        total_time = 0.0

        # Tier 0: O(1)
        f0, t0 = extract_tier_0_graph_features(graph)
        features.update(f0)
        total_time += t0

        # Tier 1: O(V+E)
        if active_tier >= 1:
            f1, t1 = extract_tier_1_graph_features(graph)
            features.update(f1)
            total_time += t1

        # Tier 2: Structural
        if active_tier >= 2:
            f2, t2 = extract_tier_2_graph_features(graph)
            features.update(f2)
            total_time += t2

        return features, total_time

    def extract_query_features(
        self, graph: Graph, query: Query, tier: Optional[int] = None
    ) -> Tuple[Dict[str, float], float]:
        """Extract query-level features for the specified tier."""
        active_tier = self.default_tier if tier is None else tier
        features: Dict[str, float] = {}
        total_time = 0.0

        # Tier 0: O(1)
        f0, t0 = extract_tier_0_query_features(graph, query)
        features.update(f0)
        total_time += t0

        # Tier 1: O(V+E) proxy / geometric query
        if active_tier >= 1:
            f1, t1 = extract_tier_1_query_features(graph, query)
            features.update(f1)
            total_time += t1

        return features, total_time

    def extract_all(
        self,
        graph: Graph,
        query: Query,
        tier: Optional[int] = None,
        cached_graph_features: Optional[Tuple[Dict[str, float], float]] = None,
    ) -> ExtractedFeatures:
        """Extract combined graph and query features for an instance with cost tracking."""
        active_tier = self.default_tier if tier is None else tier

        if cached_graph_features is not None:
            g_features, g_time = cached_graph_features
        else:
            g_features, g_time = self.extract_graph_features(graph, tier=active_tier)

        q_features, q_time = self.extract_query_features(graph, query, tier=active_tier)

        combined = dict(g_features)
        combined.update(q_features)

        return ExtractedFeatures(
            graph_id=graph.graph_id,
            query_id=query.query_id,
            features=combined,
            graph_feature_time=g_time,
            query_feature_time=q_time,
        )
