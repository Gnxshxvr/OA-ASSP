"""Timeout semantics and execution-derived validity."""

from __future__ import annotations

import time

import pytest

from oa_assp.algorithms.base import OperationCounters, SearchResult
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.benchmark import runner as runner_module
from oa_assp.benchmark.runner import build_graph, run_single_query
from oa_assp.benchmark.timing import time_solver
from oa_assp.graphs.geometric import generate_geometric_graph
from oa_assp.graphs.queries import generate_query_workload
from oa_assp.graphs.weights import assign_geometric_weights


def _slow_solver(graph, source, target, return_path=True):
    time.sleep(0.05)
    return SearchResult(distance=0.0, path=[source, target], success=True, reachable=True)


def _failing_solver(graph, source, target, return_path=True):
    raise RuntimeError("synthetic solver failure")


def _make_graph():
    g = generate_geometric_graph(num_vertices=25, average_degree=4.0, seed=5)
    assign_geometric_weights(g, seed=5)
    return g


def test_post_hoc_timeout_is_not_a_success():
    g = _make_graph()
    res = time_solver(_slow_solver, g, 0, 10, warmup_runs=0, repetitions=1, timeout_seconds=0.01)
    assert res.timeout is True
    assert res.success is False
    assert res.error is not None


def test_guarded_timeout_is_not_a_success_even_if_the_call_never_returns():
    g = _make_graph()
    res = time_solver(
        _slow_solver, g, 0, 10,
        warmup_runs=0, repetitions=1, timeout_seconds=0.01, enforce_timeout=True,
    )
    assert res.timeout is True
    assert res.success is False
    assert res.search_result is None


def test_enforce_timeout_requires_a_finite_timeout():
    g = _make_graph()
    with pytest.raises(ValueError):
        time_solver(_slow_solver, g, 0, 10, timeout_seconds=None, enforce_timeout=True)


def test_solver_exception_is_not_a_success():
    g = _make_graph()
    res = time_solver(_failing_solver, g, 0, 10, warmup_runs=0, repetitions=1, timeout_seconds=10.0)
    assert res.success is False
    assert res.timeout is False
    assert "synthetic" in (res.error or "")


def test_timing_reports_repetitions_and_dispersion():
    g = _make_graph()
    res = time_solver(dijkstra, g, 0, 10, warmup_runs=1, repetitions=5, timeout_seconds=10.0)
    assert res.success is True
    assert res.repetitions == 5
    assert res.warmup_runs == 1
    assert len(res.raw_runtimes) == 5
    assert res.min_runtime <= res.median_runtime <= res.max_runtime
    assert res.iqr_runtime >= 0.0
    assert res.std_runtime >= 0.0


def test_run_single_query_derives_validity_from_execution():
    g = _make_graph()
    queries = generate_query_workload(g, count=1, global_seed=55)
    rows = run_single_query(g, queries[0], "t", warmup_runs=1, repetitions=2, timeout_seconds=10.0)
    assert len(rows) == 3
    for r in rows:
        assert r.timeout is False
        assert r.success is True
        assert r.correct is True
        assert r.valid is True
        assert r.failure_reason == ""
    # A* is oracle-eligible only on a graph with an admissible heuristic (this one).
    astar_row = next(r for r in rows if r.algorithm == "A*")
    assert astar_row.oracle_eligible is True
    assert astar_row.heuristic_admissible is True


def test_non_geometric_astar_is_executed_but_not_oracle_eligible():
    g = build_graph("random", 40, 6.0, 101, weight_model="positive_random")
    queries = generate_query_workload(g, count=1, global_seed=2101)
    rows = run_single_query(g, queries[0], "t", warmup_runs=1, repetitions=2, timeout_seconds=10.0)
    astar_row = next(r for r in rows if r.algorithm == "A*")
    assert astar_row.success is True          # it really ran
    assert astar_row.correct is True          # and it is exact
    assert astar_row.valid is True
    assert astar_row.oracle_eligible is False  # but it cannot be a competitive option
    assert astar_row.heuristic_admissible is False


def test_timeout_is_never_recorded_as_valid(monkeypatch):
    """If every solver times out, no row may claim success/valid/oracle eligibility."""
    from oa_assp.benchmark.timing import TimingResult

    def fake_time_solver(*args, **kwargs):
        return TimingResult(
            median_runtime=0.0, mean_runtime=0.0, std_runtime=0.0, iqr_runtime=0.0,
            min_runtime=0.0, max_runtime=0.0, raw_runtimes=[], repetitions=1, warmup_runs=1,
            timeout=True, success=False, error="Timeout", search_result=None,
        )

    monkeypatch.setattr(runner_module, "time_solver", fake_time_solver)

    g = _make_graph()
    queries = generate_query_workload(g, count=1, global_seed=77)
    rows = run_single_query(g, queries[0], "t", warmup_runs=1, repetitions=1, timeout_seconds=0.001)
    for r in rows:
        assert r.timeout is True
        assert r.success is False
        assert r.valid is False
        assert r.oracle_eligible is False
        assert r.failure_reason == "Timeout"


def test_no_hardcoded_validity_literals_remain_in_runner():
    """Guard against reintroducing fabricated status fields.

    The check is AST-based so that prose in docstrings (which explains the removed
    hard-coded ``valid=True``) is not mistaken for code.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(runner_module))
    forbidden = {"valid", "success", "reachable", "timeout", "correct", "oracle_eligible"}
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in forbidden and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    offenders.append(kw.arg)
    assert not offenders, f"status fields hard-coded to True in runner: {sorted(set(offenders))}"
