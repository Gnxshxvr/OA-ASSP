"""Unit tests for Bidirectional Dijkstra algorithm."""

import math
import pytest
from oa_assp.algorithms.bidirectional_dijkstra import bidirectional_dijkstra
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.graphs.base import Graph


def test_source_equals_target():
    g = Graph()
    g.add_node(0)
    res = bidirectional_dijkstra(g, 0, 0)
    assert res.distance == 0.0
    assert res.path == [0]
    assert res.reachable is True
    assert res.counters.nodes_expanded == 0


def test_single_edge():
    g = Graph()
    g.add_edge(0, 1, 4.0)
    res = bidirectional_dijkstra(g, 0, 1)
    assert res.distance == 4.0
    assert res.path == [0, 1]
    assert res.reachable is True
    assert res.counters.forward_expansions >= 1
    assert res.counters.nodes_expanded == (
        res.counters.forward_expansions + res.counters.backward_expansions
    )


def test_unreachable_target():
    g = Graph()
    g.add_edge(0, 1, 1.0)
    g.add_node(2)
    res = bidirectional_dijkstra(g, 0, 2)
    assert math.isinf(res.distance)
    assert res.path is None
    assert res.reachable is False


def test_agreement_with_dijkstra_on_various_topologies():
    # 1. Line graph
    g_line = Graph()
    for i in range(10):
        g_line.add_edge(i, i + 1, weight=float(i + 1))
    res_dijk_line = dijkstra(g_line, 0, 10)
    res_bidi_line = bidirectional_dijkstra(g_line, 0, 10)
    assert res_bidi_line.distance == res_dijk_line.distance
    assert res_bidi_line.path == res_dijk_line.path

    # 2. Cycle / diamond graph with multiple paths
    g_diamond = Graph()
    g_diamond.add_edge(0, 1, 2.0)
    g_diamond.add_edge(0, 2, 5.0)
    g_diamond.add_edge(1, 2, 1.0)
    g_diamond.add_edge(1, 3, 4.0)
    g_diamond.add_edge(2, 3, 1.0)
    res_dijk_dia = dijkstra(g_diamond, 0, 3)
    res_bidi_dia = bidirectional_dijkstra(g_diamond, 0, 3)
    assert res_bidi_dia.distance == res_dijk_dia.distance == 4.0
    assert res_bidi_dia.path == [0, 1, 2, 3]

    # 3. 2D grid
    g_grid = Graph(directed=False)
    for r in range(5):
        for c in range(5):
            u = r * 5 + c
            if r + 1 < 5:
                g_grid.add_edge(u, (r + 1) * 5 + c, 1.5)
            if c + 1 < 5:
                g_grid.add_edge(u, r * 5 + (c + 1), 1.5)
    res_dijk_grid = dijkstra(g_grid, 0, 24)
    res_bidi_grid = bidirectional_dijkstra(g_grid, 0, 24)
    assert abs(res_bidi_grid.distance - res_dijk_grid.distance) < 1e-9


def test_forward_and_backward_expansion_counts():
    g = Graph()
    for i in range(5):
        g.add_edge(i, i + 1, 1.0)
    res = bidirectional_dijkstra(g, 0, 5)
    assert res.counters.forward_expansions > 0
    assert res.counters.backward_expansions > 0
    assert res.counters.nodes_expanded == (
        res.counters.forward_expansions + res.counters.backward_expansions
    )


def test_negative_weight_raises_error():
    g = Graph()
    g.add_edge(0, 1, -1.0)
    with pytest.raises(ValueError, match="negative weights"):
        bidirectional_dijkstra(g, 0, 1)
