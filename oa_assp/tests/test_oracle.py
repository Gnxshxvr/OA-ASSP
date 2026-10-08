"""Unit tests for offline SBS and VBS oracles."""

from pathlib import Path
import pytest
from oa_assp.benchmark.oracle import compute_oracles, save_oracle_results


def test_vbs_selection_and_validity():
    # Synthetic benchmark data with 2 queries
    data = [
        # Query 1: Geometric graph (A* is valid)
        {"graph_id": "g_geom", "query_id": "q1", "algorithm": "Dijkstra", "runtime_median": 0.005, "weight_model": "geometric", "valid": True},
        {"graph_id": "g_geom", "query_id": "q1", "algorithm": "Bidirectional Dijkstra", "runtime_median": 0.003, "weight_model": "geometric", "valid": True},
        {"graph_id": "g_geom", "query_id": "q1", "algorithm": "A*", "runtime_median": 0.001, "weight_model": "geometric", "valid": True},

        # Query 2: Non-geometric graph (A* is INVALID)
        {"graph_id": "g_rand", "query_id": "q2", "algorithm": "Dijkstra", "runtime_median": 0.004, "weight_model": "positive_random", "valid": True},
        {"graph_id": "g_rand", "query_id": "q2", "algorithm": "Bidirectional Dijkstra", "runtime_median": 0.002, "weight_model": "positive_random", "valid": True},
        {"graph_id": "g_rand", "query_id": "q2", "algorithm": "A*", "runtime_median": 0.0001, "weight_model": "positive_random", "valid": False},
    ]

    summary = compute_oracles(data)
    assert len(summary.instances) == 2

    # Query 1: A* is valid and fastest
    inst1 = next(i for i in summary.instances if i.query_id == "q1")
    assert inst1.valid_astar is True
    assert inst1.vbs_algorithm == "A*"
    assert inst1.vbs_cost == 0.001

    # Query 2: A* is invalid, so Bidirectional Dijkstra wins despite A* row value
    inst2 = next(i for i in summary.instances if i.query_id == "q2")
    assert inst2.valid_astar is False
    assert inst2.vbs_algorithm == "Bidirectional Dijkstra"
    assert inst2.vbs_cost == 0.002


def test_sbs_global_workload_minimization():
    data = [
        # Query 1
        {"graph_id": "g1", "query_id": "q1", "algorithm": "Dijkstra", "runtime_median": 0.010, "weight_model": "positive_random", "valid": True},
        {"graph_id": "g1", "query_id": "q1", "algorithm": "Bidirectional Dijkstra", "runtime_median": 0.005, "weight_model": "positive_random", "valid": True},
        # Query 2
        {"graph_id": "g1", "query_id": "q2", "algorithm": "Dijkstra", "runtime_median": 0.008, "weight_model": "positive_random", "valid": True},
        {"graph_id": "g1", "query_id": "q2", "algorithm": "Bidirectional Dijkstra", "runtime_median": 0.004, "weight_model": "positive_random", "valid": True},
    ]

    summary = compute_oracles(data)
    # Total costs: Dijkstra = 0.018, Bidi = 0.009
    assert summary.sbs_policy == "Always-Bidirectional-Dijkstra"
    assert summary.sbs_total_cost == pytest.approx(0.009)
    assert summary.vbs_total_cost == pytest.approx(0.009)


def test_save_oracle_results(tmp_path: Path):
    data = [
        {"graph_id": "g1", "query_id": "q1", "algorithm": "Dijkstra", "runtime_median": 0.005, "weight_model": "positive_random", "valid": True},
        {"graph_id": "g1", "query_id": "q1", "algorithm": "Bidirectional Dijkstra", "runtime_median": 0.003, "weight_model": "positive_random", "valid": True},
    ]
    summary = compute_oracles(data)
    out_csv = tmp_path / "oracle_results.csv"
    saved_path = save_oracle_results(summary, out_csv)
    assert Path(saved_path).exists()
