"""Unit tests for Bellman-Ford algorithm."""

import math
from oa_assp.algorithms.bellman_ford import bellman_ford
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.graphs.base import Graph


def test_source_equals_target():
    g = Graph()
    g.add_node(0)
    res = bellman_ford(g, 0, 0)
    assert res.distance == 0.0
    assert res.path == [0]
    assert res.reachable is True
    assert res.counters.passes == 0


def test_agreement_with_dijkstra_on_non_negative_graph():
    g = Graph()
    g.add_edge(0, 1, 2.0)
    g.add_edge(0, 2, 5.0)
    g.add_edge(1, 2, 1.0)
    g.add_edge(1, 3, 4.0)
    g.add_edge(2, 3, 1.0)

    res_dijk = dijkstra(g, 0, 3)
    res_bf = bellman_ford(g, 0, 3)

    assert abs(res_bf.distance - res_dijk.distance) < 1e-9
    assert res_bf.path == res_dijk.path
    assert res_bf.reachable is True


def test_negative_weights_without_negative_cycle():
    # Graph with negative edge where Dijkstra would fail if greedy
    # 0 -> 1 (wt 4)
    # 0 -> 2 (wt 5)
    # 2 -> 1 (wt -3)
    g = Graph()
    g.add_edge(0, 1, 4.0)
    g.add_edge(0, 2, 5.0)
    g.add_edge(2, 1, -3.0)

    res = bellman_ford(g, 0, 1)
    # True shortest path: 0 -> 2 -> 1 (cost 5 + (-3) = 2.0 < 4.0)
    assert res.distance == 2.0
    assert res.path == [0, 2, 1]
    assert res.reachable is True


def test_negative_cycle_detection():
    # 0 -> 1 -> 2 -> 1 (cycle 1->2->1 has weight 1 + (-3) = -2)
    # 2 -> 3 (target)
    g = Graph()
    g.add_edge(0, 1, 1.0)
    g.add_edge(1, 2, 1.0)
    g.add_edge(2, 1, -3.0)
    g.add_edge(2, 3, 1.0)

    res = bellman_ford(g, 0, 3)
    assert res.distance == -math.inf
    assert res.metadata.get("negative_cycle") is True


def test_early_stopping_passes():
    # A single edge graph only needs 1 relaxation pass
    g = Graph()
    g.add_node(2)
    g.add_node(3)
    g.add_node(4)
    g.add_edge(0, 1, 1.0)
    # Total nodes = 5, max passes would be 4, but only 1 or 2 needed
    res = bellman_ford(g, 0, 1)
    assert res.distance == 1.0
    assert res.counters.passes < 4
