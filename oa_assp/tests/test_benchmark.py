"""Unit and integration tests for timing and the benchmark runner (corrected schema)."""

import csv
from pathlib import Path

import pytest

from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.benchmark.runner import (
    BenchmarkRow,
    benchmark_row_fieldnames,
    build_graph,
    run_single_query,
)
from oa_assp.benchmark.timing import time_solver
from oa_assp.graphs.geometric import generate_geometric_graph
from oa_assp.graphs.queries import generate_query_workload
from oa_assp.graphs.weights import assign_geometric_weights


def test_time_solver_repetitions_and_warmup():
    g = generate_geometric_graph(num_vertices=30, average_degree=4.0, seed=42)
    assign_geometric_weights(g, seed=42)

    t_res = time_solver(
        solver_fn=dijkstra,
        graph=g,
        source=0,
        target=10,
        warmup_runs=2,
        repetitions=5,
    )

    assert len(t_res.raw_runtimes) == 5
    assert t_res.repetitions == 5
    assert t_res.warmup_runs == 2
    assert t_res.median_runtime > 0.0
    assert t_res.min_runtime <= t_res.median_runtime <= t_res.max_runtime
    assert t_res.iqr_runtime >= 0.0
    assert t_res.timeout is False
    assert t_res.success is True
    assert t_res.error is None
    assert t_res.search_result is not None
    assert t_res.search_result.reachable is True


def test_run_single_query_generates_valid_rows():
    g = generate_geometric_graph(num_vertices=25, average_degree=4.0, seed=55)
    assign_geometric_weights(g, seed=55)

    queries = generate_query_workload(g, count=1, global_seed=123)
    assert len(queries) == 1
    q = queries[0]

    rows = run_single_query(
        graph=g,
        query=q,
        experiment_id="test_exp",
        warmup_runs=1,
        repetitions=3,
        timeout_seconds=5.0,
    )

    # 3 default algorithms: Dijkstra, Bidirectional Dijkstra, A*
    assert len(rows) == 3
    algos = {r.algorithm for r in rows}
    assert algos == {"Dijkstra", "Bidirectional Dijkstra", "A*"}

    for r in rows:
        assert isinstance(r, BenchmarkRow)
        assert r.experiment_id == "test_exp"
        assert r.graph_id == g.graph_id
        assert r.query_id == q.query_id
        assert r.success is True
        assert r.correct is True
        assert r.valid is True
        assert r.timeout is False
        assert r.reachable is True
        assert r.distance > 0.0
        assert r.runtime_median > 0.0
        assert r.timing_repetitions == 3
        assert r.warmup_runs == 1


def test_raw_row_schema_is_streamable_to_csv(tmp_path: Path):
    """The corrected raw schema must write and round-trip, so tables trace to raw data."""
    g = generate_geometric_graph(num_vertices=20, average_degree=4.0, seed=9)
    assign_geometric_weights(g, seed=9)
    q = generate_query_workload(g, count=1, global_seed=1000)[0]
    rows = run_single_query(g, q, "schema_test", warmup_runs=1, repetitions=2, timeout_seconds=5.0)

    out = tmp_path / "rows.csv"
    fieldnames = benchmark_row_fieldnames()
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r.to_dict())

    with open(out, "r", encoding="utf-8") as f:
        back = list(csv.DictReader(f))
    assert len(back) == 3
    for row in back:
        for key in ("oracle_eligible", "timeout", "valid", "runtime_iqr", "heuristic_admissible"):
            assert key in row
    assert back[0]["experiment_id"] == "schema_test"


def test_build_graph_is_deterministic_across_calls():
    a = build_graph("random", 60, 6.0, 123, weight_model="positive_random")
    b = build_graph("random", 60, 6.0, 123, weight_model="positive_random")
    assert a.num_edges == b.num_edges
    assert a.metadata["actual_average_degree"] == b.metadata["actual_average_degree"]
    for u in a.nodes:
        assert a.neighbors(u) == b.neighbors(u)
