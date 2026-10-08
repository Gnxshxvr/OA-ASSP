"""Unit tests for A* algorithm and heuristics."""

import math
import pytest
from oa_assp.algorithms.astar import astar, euclidean_heuristic, zero_heuristic
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.graphs.base import Graph


def test_source_equals_target():
    g = Graph()
    g.add_node(0, coords=(0.0, 0.0))
    res = astar(g, 0, 0)
    assert res.distance == 0.0
    assert res.path == [0]
    assert res.reachable is True
    assert res.counters.nodes_expanded == 0


def test_single_edge():
    g = Graph()
    g.add_node(0, coords=(0.0, 0.0))
    g.add_node(1, coords=(1.0, 0.0))
    g.add_edge(0, 1, weight=1.0)
    res = astar(g, 0, 1)
    assert res.distance == 1.0
    assert res.path == [0, 1]
    assert res.reachable is True


def test_unreachable_target():
    g = Graph()
    g.add_node(0, coords=(0.0, 0.0))
    g.add_node(1, coords=(5.0, 5.0))
    res = astar(g, 0, 1)
    assert math.isinf(res.distance)
    assert res.path is None
    assert res.reachable is False


def test_zero_heuristic_equivalence_to_dijkstra():
    g = Graph()
    g.add_edge(0, 1, 2.0)
    g.add_edge(0, 2, 5.0)
    g.add_edge(1, 2, 1.0)
    g.add_edge(1, 3, 4.0)
    g.add_edge(2, 3, 1.0)

    res_dijkstra = dijkstra(g, 0, 3)
    res_astar = astar(g, 0, 3, heuristic=zero_heuristic)

    assert res_astar.distance == res_dijkstra.distance
    assert res_astar.path == res_dijkstra.path
    assert res_astar.counters.nodes_expanded == res_dijkstra.counters.nodes_expanded


def test_euclidean_heuristic_on_grid():
    # 4x4 grid graph where edge weights are Euclidean distances (1.0)
    g = Graph(directed=False)
    for r in range(4):
        for c in range(4):
            node = r * 4 + c
            g.add_node(node, coords=(float(r), float(c)))

    for r in range(4):
        for c in range(4):
            u = r * 4 + c
            if r + 1 < 4:
                v = (r + 1) * 4 + c
                g.add_edge(u, v, 1.0)
            if c + 1 < 4:
                v = r * 4 + (c + 1)
                g.add_edge(u, v, 1.0)

    source = 0  # (0, 0)
    target = 15  # (3, 3)

    res_dijkstra = dijkstra(g, source, target)
    res_astar = astar(g, source, target)

    # Both must find exact shortest path distance (6.0 in Manhattan grid with length 1 edges)
    assert res_astar.distance == res_dijkstra.distance == 6.0
    # Informed A* should expand fewer or equal nodes than blind Dijkstra
    assert res_astar.counters.nodes_expanded <= res_dijkstra.counters.nodes_expanded


def test_negative_weight_raises_error():
    g = Graph()
    g.add_edge(0, 1, -2.0)
    with pytest.raises(ValueError, match="negative edge weights"):
        astar(g, 0, 1)


def test_euclidean_heuristic_admissibility_proof():
    """Verify that Euclidean distance heuristic is provably admissible on geometric graphs."""
    from oa_assp.graphs.geometric import generate_geometric_graph
    from oa_assp.graphs.weights import assign_geometric_weights

    # Test across multiple multiplier values c >= 1.0 and epsilon >= 0
    for c in [1.0, 1.25, 1.5, 2.0, 3.0]:
        g = generate_geometric_graph(num_vertices=20, average_degree=6.0, seed=42)
        assign_geometric_weights(g, c=c, epsilon=0.1, seed=42)
        h_fn = euclidean_heuristic(g)

        # For multiple pairs, verify h(u, t) <= true_shortest_path_distance(u, t)
        for u in range(0, 10, 2):
            for t in range(1, 10, 2):
                if u == t:
                    continue
                res = dijkstra(g, u, t)
                if res.reachable:
                    h_val = h_fn(u, t)
                    assert h_val <= res.distance + 1e-9, (
                        f"Heuristic inadmissible for c={c}: h({u}, {t}) = {h_val} > dist = {res.distance}"
                    )
