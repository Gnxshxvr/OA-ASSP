"""The memoized Euclidean heuristic must be behaviour-preserving, not just faster."""

import math

import pytest

from oa_assp.algorithms.astar import astar, euclidean_heuristic, zero_heuristic
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.benchmark.correctness import verify_path
from oa_assp.graphs.geometric import generate_geometric_graph
from oa_assp.graphs.queries import generate_query_workload
from oa_assp.graphs.random import generate_random_graph
from oa_assp.graphs.weights import assign_geometric_weights, assign_positive_random_weights


def _reference_heuristic(graph):
    """The historical implementation: recomputes the Euclidean distance every call."""
    coords = graph.coords

    def h(u, target):
        if u not in coords or target not in coords:
            return 0.0
        c1 = coords[u]
        c2 = coords[target]
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))

    return h


@pytest.mark.parametrize("seed,V,D", [(11, 40, 6.0), (12, 120, 8.0), (13, 200, 10.0)])
def test_cached_heuristic_matches_reference_values(seed, V, D):
    g = generate_geometric_graph(num_vertices=V, average_degree=D, seed=seed)
    assign_geometric_weights(g, c=1.25, epsilon=0.1, seed=seed)

    cached = euclidean_heuristic(g)
    reference = _reference_heuristic(g)

    for target in list(g.nodes)[:5]:
        for node in list(g.nodes)[:40]:
            assert cached(node, target) == reference(node, target)


def test_cached_heuristic_correct_across_multiple_targets():
    """A single closure reused with different targets must not mix up memo entries."""
    g = generate_geometric_graph(num_vertices=60, average_degree=6.0, seed=99)
    assign_geometric_weights(g, c=1.25, epsilon=0.1, seed=99)

    cached = euclidean_heuristic(g)
    reference = _reference_heuristic(g)

    for target in (0, 5, 17, 33, 59):
        for node in g.nodes:
            assert cached(node, target) == reference(node, target)


@pytest.mark.parametrize("seed", [3, 21, 44])
def test_cached_astar_same_result_and_counters(seed):
    g = generate_geometric_graph(num_vertices=150, average_degree=6.0, seed=seed)
    assign_geometric_weights(g, c=1.25, epsilon=0.1, seed=seed)

    queries = generate_query_workload(g, count=25, global_seed=seed + 2000)
    for q in queries:
        cached = astar(g, q.source, q.target, heuristic=euclidean_heuristic(g))
        reference = astar(g, q.source, q.target, heuristic=_reference_heuristic(g))
        exact = dijkstra(g, q.source, q.target)

        assert cached.distance == pytest.approx(reference.distance, abs=1e-12)
        assert cached.distance == pytest.approx(exact.distance, abs=1e-12)
        assert cached.path == reference.path  # same tie-breaking, same expansion order

        # Operation counters must be untouched by memoization.
        assert cached.counters.nodes_expanded == reference.counters.nodes_expanded
        assert cached.counters.heap_pushes == reference.counters.heap_pushes
        assert cached.counters.heap_pops == reference.counters.heap_pops
        assert cached.counters.relaxations == reference.counters.relaxations
        assert cached.counters.edges_examined == reference.counters.edges_examined

        ok, msg = verify_path(g, q.source, q.target, cached.path, cached.distance)
        assert ok, msg


def test_cached_astar_on_non_geometric_graph_uses_zero_heuristic():
    g = generate_random_graph(num_vertices=80, average_degree=6.0, seed=7)
    assign_positive_random_weights(g, seed=7)
    queries = generate_query_workload(g, count=10, global_seed=3007)

    for q in queries:
        res = astar(g, q.source, q.target, heuristic=zero_heuristic)
        exact = dijkstra(g, q.source, q.target)
        assert res.distance == pytest.approx(exact.distance, abs=1e-12)


def test_memoized_heuristic_is_admissible_and_consistent():
    g = generate_geometric_graph(num_vertices=90, average_degree=6.0, seed=17)
    assign_geometric_weights(g, c=1.25, epsilon=0.1, seed=17)

    for target in list(g.nodes)[:6]:
        h = euclidean_heuristic(g)
        assert h(target, target) == pytest.approx(0.0)

        # Admissibility: h(u, target) must never exceed the true distance u -> target.
        sample = list(g.nodes)[:15]
        for u in sample:
            true_dist = dijkstra(g, u, target).distance
            assert h(u, target) <= true_dist + 1e-12

        # Consistency: h(u, target) <= w(u, v) + h(v, target) for every edge (u, v).
        for u in sample:
            for v, w in g.neighbors(u).items():
                assert h(u, target) <= w + h(v, target) + 1e-12
