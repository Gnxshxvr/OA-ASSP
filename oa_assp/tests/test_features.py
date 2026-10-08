"""Unit tests for feature extraction and cost measurement."""

import pytest
from oa_assp.features.cheap import (
    extract_tier_0_graph_features,
    extract_tier_0_query_features,
)
from oa_assp.features.linear_scan import (
    extract_tier_1_graph_features,
    extract_tier_1_query_features,
)
from oa_assp.features.structural import extract_tier_2_graph_features
from oa_assp.features.extractor import FeatureExtractor
from oa_assp.graphs.geometric import generate_geometric_graph
from oa_assp.graphs.queries import generate_query_workload
from oa_assp.graphs.random import generate_random_graph
from oa_assp.graphs.weights import assign_geometric_weights, assign_positive_random_weights


def test_tier_0_features():
    g = generate_random_graph(num_vertices=30, average_degree=4.0, seed=42)
    assign_positive_random_weights(g, seed=42)
    queries = generate_query_workload(g, count=2, global_seed=10)
    q = queries[0]

    g_feat, g_time = extract_tier_0_graph_features(g)
    assert g_feat["num_vertices"] == 30.0
    assert g_feat["num_edges"] > 0
    assert g_feat["average_degree"] > 0
    assert g_feat["heuristic_available"] == 0.0  # non-geometric
    assert g_time >= 0.0

    q_feat, q_time = extract_tier_0_query_features(g, q)
    assert q_feat["source_degree"] == float(g.degree(q.source))
    assert q_feat["target_degree"] == float(g.degree(q.target))
    assert q_time >= 0.0


def test_tier_1_features_geometric():
    g = generate_geometric_graph(num_vertices=25, average_degree=6.0, seed=123)
    assign_geometric_weights(g, c=1.25, epsilon=0.1, seed=123)
    queries = generate_query_workload(g, count=2, global_seed=456)
    q = queries[0]

    g_feat, g_time = extract_tier_1_graph_features(g)
    assert "degree_mean" in g_feat
    assert "degree_variance" in g_feat
    assert "weight_mean" in g_feat
    assert g_feat["negative_edge_fraction"] == 0.0
    assert g_feat["heuristic_quality_mean"] > 0.0
    assert g_time >= 0.0

    q_feat, q_time = extract_tier_1_query_features(g, q)
    assert q_feat["source_target_euclidean_distance"] > 0.0
    assert q_feat["relative_geometric_query_distance"] > 0.0
    assert q_time >= 0.0


def test_tier_2_structural_features():
    g = generate_random_graph(num_vertices=20, average_degree=4.0, seed=77)
    assign_positive_random_weights(g, seed=77)

    g_feat, g_time = extract_tier_2_graph_features(g)
    assert "clustering_coefficient" in g_feat
    assert 0.0 <= g_feat["clustering_coefficient"] <= 1.0
    assert "approx_diameter" in g_feat
    assert g_feat["approx_diameter"] >= 1.0
    assert g_time >= 0.0


def test_feature_extractor_subsets_and_cost_accounting():
    g = generate_geometric_graph(num_vertices=20, average_degree=4.0, seed=99)
    assign_geometric_weights(g, seed=99)
    queries = generate_query_workload(g, count=1, global_seed=88)
    q = queries[0]

    # Tier 0 only
    ext0 = FeatureExtractor(default_tier=0)
    res0 = ext0.extract_all(g, q)
    assert "num_vertices" in res0.features
    assert "degree_variance" not in res0.features
    assert res0.graph_feature_time >= 0.0
    assert res0.query_feature_time >= 0.0

    # Tier 1 (Tier 0 + Tier 1)
    ext1 = FeatureExtractor(default_tier=1)
    res1 = ext1.extract_all(g, q)
    assert "num_vertices" in res1.features
    assert "degree_variance" in res1.features
    assert "clustering_coefficient" not in res1.features

    # Tier 2 (Tier 0 + Tier 1 + Tier 2)
    ext2 = FeatureExtractor(default_tier=2)
    res2 = ext2.extract_all(g, q)
    assert "num_vertices" in res2.features
    assert "degree_variance" in res2.features
    assert "clustering_coefficient" in res2.features
