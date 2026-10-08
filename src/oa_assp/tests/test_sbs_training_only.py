"""SBS must be determined from training graphs only."""

from __future__ import annotations

import pytest

from oa_assp.benchmark.oracle import (
    assert_reference_disjoint,
    compute_oracles,
    policy_cost_for_instance,
)


def _row(gid, qid, algo, cost, weight_model="positive_random", eligible=True):
    return {
        "graph_id": gid,
        "query_id": qid,
        "algorithm": algo,
        "runtime_median": cost,
        "weight_model": weight_model,
        "valid": True,
        "success": True,
        "timeout": False,
        "oracle_eligible": eligible,
    }


def test_sbs_uses_reference_set_only():
    """Train favours Bidi; test favours Dijkstra. SBS must follow TRAIN."""
    data = []
    # Training graphs: Bidirectional Dijkstra is 4x faster.
    for q in ("q1", "q2", "q3"):
        data.append(_row("g_train", q, "Dijkstra", 0.010))
        data.append(_row("g_train", q, "Bidirectional Dijkstra", 0.0025))
        data.append(_row("g_train", q, "A*", 0.020, eligible=False))
    # Test graphs: Dijkstra is 10x faster (would flip the policy if it were counted).
    for q in ("q1", "q2", "q3"):
        data.append(_row("g_test", q, "Dijkstra", 0.001))
        data.append(_row("g_test", q, "Bidirectional Dijkstra", 0.010))
        data.append(_row("g_test", q, "A*", 0.020, eligible=False))

    summary = compute_oracles(
        data,
        sbs_reference_graph_ids=["g_train"],
        sbs_source="training only",
        must_exclude_graph_ids=["g_test"],
    )
    assert summary.sbs_policy == "Always-Bidirectional-Dijkstra"
    assert summary.sbs_source == "training only"
    assert summary.sbs_reference_graph_ids == ["g_train"]
    assert summary.num_reference_instances == 3
    assert summary.policy_total_costs_reference["Always-Bidirectional-Dijkstra"] == pytest.approx(0.0075)


def test_sbs_changes_when_held_out_data_is_included():
    """Demonstrates the leakage the corrected implementation prevents."""
    data = []
    for q in ("q1",):
        data.append(_row("g_train", q, "Dijkstra", 0.010))
        data.append(_row("g_train", q, "Bidirectional Dijkstra", 0.0025))
        data.append(_row("g_test", q, "Dijkstra", 0.0001))
        data.append(_row("g_test", q, "Bidirectional Dijkstra", 0.010))

    correct = compute_oracles(data, sbs_reference_graph_ids=["g_train"])
    leaky = compute_oracles(data, sbs_reference_graph_ids=None)

    assert correct.sbs_policy == "Always-Bidirectional-Dijkstra"
    assert leaky.sbs_policy == "Always-Dijkstra"  # contaminated by the test graph
    assert correct.sbs_policy != leaky.sbs_policy


def test_reference_disjointness_is_enforced():
    data = [
        _row("g_train", "q1", "Dijkstra", 0.01),
        _row("g_train", "q1", "Bidirectional Dijkstra", 0.02),
        _row("g_test", "q1", "Dijkstra", 0.01),
        _row("g_test", "q1", "Bidirectional Dijkstra", 0.02),
    ]
    with pytest.raises(ValueError, match="SBS leakage"):
        compute_oracles(data, sbs_reference_graph_ids=["g_train", "g_test"], must_exclude_graph_ids=["g_test"])

    with pytest.raises(ValueError):
        assert_reference_disjoint(["a", "b"], ["b", "c"])

    assert_reference_disjoint(["a"], ["b", "c"])  # must not raise


def test_timeout_rows_are_excluded_from_the_oracle():
    data = [
        _row("g1", "q1", "Dijkstra", 0.010),
        {**_row("g1", "q1", "Bidirectional Dijkstra", 0.001), "timeout": True, "success": False, "oracle_eligible": True},
    ]
    summary = compute_oracles(data, sbs_reference_graph_ids=["g1"])
    inst = summary.instances[0]
    assert inst.valid_bidirectional is False
    assert inst.vbs_algorithm == "Dijkstra"


def test_policy_cost_helper_matches_instance_fields():
    data = [
        _row("g1", "q1", "Dijkstra", 0.010),
        _row("g1", "q1", "Bidirectional Dijkstra", 0.004),
    ]
    inst = compute_oracles(data, sbs_reference_graph_ids=["g1"]).instances[0]
    assert policy_cost_for_instance(inst, "Always-Dijkstra") == pytest.approx(0.010)
    assert policy_cost_for_instance(inst, "Always-Bidirectional-Dijkstra") == pytest.approx(0.004)
    with pytest.raises(ValueError):
        policy_cost_for_instance(inst, "Always-Nonsense")
