"""Unit tests for Dijkstra's algorithm."""

import math
import pytest
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.graphs.base import Graph


def test_source_equals_target():
    g = Graph()
    g.add_node(0)
    res = dijkstra(g, 0, 0)
    assert res.distance == 0.0
    assert res.path == [0]
    assert res.reachable is True
    assert res.success is True
    assert res.counters.nodes_expanded == 0


def test_single_edge():
    g = Graph()
    g.add_edge(0, 1, weight=3.5)
    res = dijkstra(g, 0, 1)
    assert res.distance == 3.5
    assert res.path == [0, 1]
    assert res.reachable is True
    assert res.counters.relaxations == 1
    assert res.counters.nodes_expanded == 2  # popped 0, then 1


def test_unreachable_target():
    g = Graph()
    g.add_edge(0, 1, weight=1.0)
    g.add_node(2)
    res = dijkstra(g, 0, 2)
    assert math.isinf(res.distance)
    assert res.path is None
    assert res.reachable is False
    assert res.success is True


def test_multiple_shortest_paths():
    g = Graph()
    g.add_edge(0, 1, weight=1.0)
    g.add_edge(1, 3, weight=2.0)
    g.add_edge(0, 2, weight=1.0)
    g.add_edge(2, 3, weight=2.0)
    res = dijkstra(g, 0, 3)
    assert res.distance == 3.0
    assert res.path in ([0, 1, 3], [0, 2, 3])
    assert res.reachable is True


def test_zero_weight_edges():
    g = Graph()
    g.add_edge(0, 1, weight=0.0)
    g.add_edge(1, 2, weight=2.0)
    g.add_edge(0, 2, weight=5.0)
    res = dijkstra(g, 0, 2)
    assert res.distance == 2.0
    assert res.path == [0, 1, 2]


def test_negative_weight_raises_error():
    g = Graph()
    g.add_edge(0, 1, weight=-1.0)
    with pytest.raises(ValueError, match="negative edge weights"):
        dijkstra(g, 0, 1)


def test_exact_operation_counters():
    # Reference graph:
    # 0 -> 1 (wt 2)
    # 0 -> 2 (wt 5)
    # 1 -> 2 (wt 1)
    # 1 -> 3 (wt 4)
    # 2 -> 3 (wt 1)
    g = Graph()
    g.add_edge(0, 1, 2.0)
    g.add_edge(0, 2, 5.0)
    g.add_edge(1, 2, 1.0)
    g.add_edge(1, 3, 4.0)
    g.add_edge(2, 3, 1.0)

    res = dijkstra(g, 0, 3)
    assert res.distance == 4.0
    assert res.path == [0, 1, 2, 3]

    # Hand-verified operation counts:
    # pushes: source(1) + relax(1)+relax(2)+relax(2 via 1)+relax(3 via 1)+relax(3 via 2) = 6
    # pops: 0 (dist 0), 1 (dist 2), 2 (dist 3), 3 (dist 4, target -> breaks early) = 4
    # nodes_expanded: 0, 1, 2, 3 = 4
    # relaxations: 5
    # edges_examined: 2 (from 0) + 2 (from 1) + 1 (from 2) = 5
    assert res.counters.heap_pushes == 6
    assert res.counters.heap_pops == 4
    assert res.counters.nodes_expanded == 4
    assert res.counters.relaxations == 5
    assert res.counters.edges_examined == 5
