"""Unit tests for graph generators and weight assignment."""

import pytest
from oa_assp.graphs.geometric import generate_geometric_graph
from oa_assp.graphs.random import generate_random_graph
from oa_assp.graphs.scale_free import generate_scale_free_graph
from oa_assp.graphs.weights import (
    assign_geometric_weights,
    assign_positive_random_weights,
)


def test_random_graph_determinism():
    g1 = generate_random_graph(num_vertices=100, average_degree=8.0, seed=42)
    g2 = generate_random_graph(num_vertices=100, average_degree=8.0, seed=42)
    g3 = generate_random_graph(num_vertices=100, average_degree=8.0, seed=99)

    assert g1.num_nodes == g2.num_nodes == 100
    assert g1.num_edges == g2.num_edges
    assert list(g1.edges()) == list(g2.edges())
    assert g1.metadata["actual_average_degree"] == g2.metadata["actual_average_degree"]
    # Different seed produces different edges
    assert list(g1.edges()) != list(g3.edges())


def test_geometric_graph_determinism_and_coords():
    g1 = generate_geometric_graph(num_vertices=50, average_degree=6.0, seed=123)
    g2 = generate_geometric_graph(num_vertices=50, average_degree=6.0, seed=123)

    assert g1.num_nodes == 50
    assert len(g1.coords) == 50
    assert g1.coords == g2.coords
    assert list(g1.edges()) == list(g2.edges())

    # All coordinates within unit square [0, 1] x [0, 1]
    for node, (x, y) in g1.coords.items():
        assert 0.0 <= x <= 1.0
        assert 0.0 <= y <= 1.0


def test_scale_free_graph_preferential_attachment():
    g = generate_scale_free_graph(num_vertices=100, average_degree=6.0, seed=42)
    assert g.num_nodes == 100
    assert g.num_edges > 0
    # Degrees should follow heavy-tailed distribution (max degree >> average degree)
    degrees = [g.degree(u) for u in g.nodes]
    assert max(degrees) > g.metadata["actual_average_degree"] * 2


def test_positive_random_weights():
    g = generate_random_graph(num_vertices=20, average_degree=4.0, seed=42)
    assign_positive_random_weights(g, min_weight=5.0, max_weight=25.0, seed=42)

    assert g.metadata["weight_model"] == "positive_random"
    for u, v, w in g.edges():
        assert 5.0 <= w <= 25.0


def test_geometric_weights_and_heuristic_admissibility():
    g = generate_geometric_graph(num_vertices=20, average_degree=4.0, seed=42)
    assign_geometric_weights(g, c=1.5, epsilon=0.1, seed=42)

    assert g.metadata["weight_model"] == "geometric"
    assert g.metadata["heuristic_admissible"] is True
    assert g.metadata["heuristic_scaling"] == 1.0

    for u, v, w in g.edges():
        assert w > 0.0
