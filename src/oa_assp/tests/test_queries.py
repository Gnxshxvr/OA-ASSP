"""Unit tests for query generator."""

import pytest
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.graphs.geometric import generate_geometric_graph
from oa_assp.graphs.queries import generate_query_workload
from oa_assp.graphs.random import generate_random_graph
from oa_assp.graphs.weights import assign_positive_random_weights


def test_query_workload_determinism():
    g = generate_random_graph(num_vertices=50, average_degree=6.0, seed=42)
    assign_positive_random_weights(g, seed=42)

    queries1 = generate_query_workload(g, count=20, global_seed=1001)
    queries2 = generate_query_workload(g, count=20, global_seed=1001)

    assert len(queries1) == len(queries2) == 20
    for q1, q2 in zip(queries1, queries2):
        assert q1.query_id == q2.query_id
        assert q1.source == q2.source
        assert q1.target == q2.target
        assert q1.query_distance_value == q2.query_distance_value
        assert q1.query_distance_category == q2.query_distance_category


def test_queries_are_reachable_and_distinct():
    g = generate_geometric_graph(num_vertices=40, average_degree=6.0, seed=77)
    assign_positive_random_weights(g, seed=77)

    queries = generate_query_workload(g, count=25, global_seed=2001)

    for q in queries:
        assert q.source != q.target
        # Verify reachable using Dijkstra
        res = dijkstra(g, q.source, q.target)
        assert res.reachable is True
        assert res.distance < float("inf")


def test_query_distance_categorization():
    g = generate_random_graph(num_vertices=60, average_degree=4.0, seed=12)
    assign_positive_random_weights(g, seed=12)

    queries = generate_query_workload(
        g,
        count=30,
        global_seed=3001,
        short_percentile=0.25,
        long_percentile=0.75,
    )

    categories = {q.query_distance_category for q in queries}
    assert "short" in categories
    assert "long" in categories
    # All queries should have valid category
    for q in queries:
        assert q.query_distance_category in ("short", "medium", "long")
        assert q.query_distance_value >= 0.0
