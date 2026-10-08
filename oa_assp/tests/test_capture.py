"""CaptureRate / RequiredCapture arithmetic."""

from __future__ import annotations

import math

import pytest

from oa_assp.analysis.capture import compute_capture_analysis

META = {"g1": {"family": "random", "V": 40, "target_D": 6.0}, "g2": {"family": "geometric", "V": 80, "target_D": 12.0}}


def _records(n, qf, sel, solver, sbs, vbs):
    return [
        {"query_id": f"q{i}", "query_feature_time": qf, "selection_time": sel,
         "solver_time": solver, "sbs_solver_time": sbs, "vbs_solver_time": vbs,
         "selected_algorithm": "Bidirectional Dijkstra", "vbs_algorithm": "Bidirectional Dijkstra"}
        for i in range(n)
    ]


def test_capture_and_required_capture_arithmetic():
    per_graph = {"g1": _records(4, 1e-6, 1e-6, 1e-4, 2e-4, 1.5e-4)}
    res = compute_capture_analysis(
        per_graph_queries=per_graph,
        graph_feature_times={"g1": 1e-5},
        graph_meta=META,
        q_checkpoints=[1, 2, 4],
    )
    pt = {(p.graph_id, p.Q): p for p in res.graph_points}

    p4 = pt[("g1", 4)]
    # overhead = graph 1e-5 + 4*(1e-6 + 1e-6) = 1.8e-5
    assert p4.SelectionOverhead == pytest.approx(1.8e-5)
    assert p4.C_Adaptive == pytest.approx(1.8e-5 + 4e-4)
    assert p4.C_SBS == pytest.approx(8e-4)
    assert p4.C_VBS == pytest.approx(6e-4)
    assert p4.OracleGap == pytest.approx(2e-4)
    assert p4.AdaptiveSavings == pytest.approx(8e-4 - (1.8e-5 + 4e-4))
    assert p4.CaptureRate == pytest.approx(p4.AdaptiveSavings / 2e-4)
    assert p4.RequiredCapture == pytest.approx(1.8e-5 / 2e-4)
    assert p4.Pays_for_itself is (p4.C_Adaptive < p4.C_SBS)

    p1 = pt[("g1", 1)]
    # Q=1 is not amortised: the graph feature is paid for a single query.
    assert p1.SelectionOverhead == pytest.approx(1e-5 + 2e-6)
    assert p1.RequiredCapture > p4.RequiredCapture


def test_zero_oracle_gap_is_labelled_not_patched():
    per_graph = {"g1": _records(3, 1e-6, 1e-6, 1e-4, 1e-4, 1e-4)}
    res = compute_capture_analysis(per_graph, {"g1": 1e-5}, META, q_checkpoints=[1, 3])
    for p in res.graph_points:
        assert p.gap_status == "zero_oracle_gap"
        assert math.isnan(p.CaptureRate)
        assert math.isnan(p.RequiredCapture)
    agg = res.aggregate_points[3]
    assert agg["gap_status"] == "zero_oracle_gap"
    assert math.isnan(agg["RequiredCapture"])


def test_negative_oracle_gap_is_labelled():
    per_graph = {"g1": _records(2, 1e-6, 1e-6, 1e-4, 1e-4, 2e-4)}
    res = compute_capture_analysis(per_graph, {"g1": 0.0}, META, q_checkpoints=[2])
    assert res.graph_points[0].gap_status == "negative_gap"
    assert math.isnan(res.graph_points[0].CaptureRate)


def test_pays_for_itself_requires_capture_to_exceed_required_capture():
    # Cheap overhead, good capture -> pays.
    good = compute_capture_analysis({"g1": _records(50, 1e-7, 1e-7, 5e-5, 1e-4, 1e-5)}, {"g1": 1e-6}, META, q_checkpoints=[50])
    p = good.aggregate_points[50]
    assert p["CaptureRate"] > p["RequiredCapture"]
    assert p["Pays_for_itself"] is True

    # Expensive overhead, same capture -> does not pay.
    bad = compute_capture_analysis({"g1": _records(50, 5e-4, 5e-4, 5e-5, 1e-4, 1e-5)}, {"g1": 1e-3}, META, q_checkpoints=[50])
    q = bad.aggregate_points[50]
    assert q["CaptureRate"] <= q["RequiredCapture"]
    assert q["Pays_for_itself"] is False


def test_aggregate_is_ratio_of_sums_not_mean_of_ratios():
    per_graph = {
        "g1": _records(10, 1e-6, 1e-6, 1e-4, 2e-4, 1e-5),   # large gap
        "g2": _records(10, 1e-6, 1e-6, 1e-4, 1.0001e-4, 1e-4),  # tiny gap
    }
    res = compute_capture_analysis(per_graph, {"g1": 0.0, "g2": 0.0}, META, q_checkpoints=[10])
    agg = res.aggregate_points[10]
    tot_sbs = sum(p.C_SBS for p in res.graph_points)
    tot_vbs = sum(p.C_VBS for p in res.graph_points)
    assert agg["OracleGap"] == pytest.approx(tot_sbs - tot_vbs)
    assert agg["CaptureRate"] == pytest.approx((tot_sbs - agg["total_Adaptive"]) / (tot_sbs - tot_vbs))


def test_break_even_Q_is_first_Q_that_pays():
    per_graph = {"g1": _records(100, 1e-6, 1e-6, 9.9e-5, 1e-4, 1e-5)}
    res = compute_capture_analysis(
        per_graph, {"g1": 1e-3}, META, q_checkpoints=[1, 10, 50, 100]
    )
    first = res.break_even_Q_per_graph["g1"]
    if first is not None:
        pts = {p.Q: p for p in res.graph_points if p.graph_id == "g1"}
        assert pts[first].Pays_for_itself is True
        for Q, p in pts.items():
            if Q < first:
                assert p.Pays_for_itself is False
