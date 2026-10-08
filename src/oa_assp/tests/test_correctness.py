"""Cross-algorithm correctness validation tests."""

import math
from oa_assp.algorithms.astar import astar, euclidean_heuristic
from oa_assp.algorithms.bellman_ford import bellman_ford
from oa_assp.algorithms.bidirectional_dijkstra import bidirectional_dijkstra
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.benchmark.correctness import validate_results, verify_path
from oa_assp.graphs.base import Graph


def test_cross_algorithm_agreement_grid():
    # Construct 5x5 grid with spatial coordinates and non-negative weights
    g = Graph(directed=False)
    for r in range(5):
        for c in range(5):
            node = r * 5 + c
            g.add_node(node, coords=(float(r), float(c)))

    for r in range(5):
        for c in range(5):
            u = r * 5 + c
            if r + 1 < 5:
                v = (r + 1) * 5 + c
                g.add_edge(u, v, 2.0)
            if c + 1 < 5:
                v = r * 5 + (c + 1)
                g.add_edge(u, v, 2.0)

    source, target = 0, 24

    res_dijk = dijkstra(g, source, target)
    res_astar = astar(g, source, target, heuristic=euclidean_heuristic(g))
    res_bidi = bidirectional_dijkstra(g, source, target)
    res_bf = bellman_ford(g, source, target)

    results = {
        "Dijkstra": res_dijk,
        "A*": res_astar,
        "Bidirectional Dijkstra": res_bidi,
        "Bellman-Ford": res_bf,
    }

    validation = validate_results(g, source, target, results)
    assert validation.is_correct is True
    assert len(validation.diagnostics) == 0
    # Expected distance on 5x5 grid: (4 + 4) * 2.0 = 16.0
    for name, dist in validation.distances.items():
        assert abs(dist - 16.0) < 1e-9


def test_cross_algorithm_unreachable():
    g = Graph()
    g.add_edge(0, 1, 1.0)
    g.add_edge(2, 3, 1.0)

    source, target = 0, 3

    results = {
        "Dijkstra": dijkstra(g, source, target),
        "A*": astar(g, source, target),
        "Bidirectional Dijkstra": bidirectional_dijkstra(g, source, target),
        "Bellman-Ford": bellman_ford(g, source, target),
    }

    validation = validate_results(g, source, target, results)
    assert validation.is_correct is True
    for name, dist in validation.distances.items():
        assert math.isinf(dist)


def test_verify_path_detects_corrupted_path():
    g = Graph()
    g.add_edge(0, 1, 2.0)
    g.add_edge(1, 2, 3.0)

    # 1. Correct path
    valid, msg = verify_path(g, 0, 2, [0, 1, 2], expected_distance=5.0)
    assert valid is True

    # 2. Path with wrong distance
    valid, msg = verify_path(g, 0, 2, [0, 1, 2], expected_distance=4.0)
    assert valid is False
    assert "does not match" in msg

    # 3. Path with nonexistent edge
    valid, msg = verify_path(g, 0, 2, [0, 2], expected_distance=5.0)
    assert valid is False
    assert "nonexistent edge" in msg
