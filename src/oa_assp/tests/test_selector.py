"""Unit tests for dataset splitting, leakage auditing, and Decision Tree selector."""

import numpy as np
import pytest
from oa_assp.benchmark.oracle import OracleInstance, OracleSummary
from oa_assp.selector.dataset import (
    DatasetSplit,
    SplitData,
    prepare_selector_dataset,
    split_graphs,
)
from oa_assp.selector.decision_tree import DecisionTreeSelector
from oa_assp.selector.validation import audit_feature_columns


def test_graph_level_split_disjointness():
    graph_ids = [f"graph_{i}" for i in range(10)]
    train_gids, val_gids, test_gids = split_graphs(
        graph_ids, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2, seed=42
    )

    set_train = set(train_gids)
    set_val = set(val_gids)
    set_test = set(test_gids)

    # Disjointness assertions
    assert len(set_train & set_test) == 0
    assert len(set_train & set_val) == 0
    assert len(set_val & set_test) == 0
    assert len(set_train | set_val | set_test) == 10

    # Test SplitData leakage validation
    dummy_feat = ["num_vertices"]
    s_train = DatasetSplit("train", train_gids, np.zeros((5, 1)), dummy_feat, ["Dijkstra"] * 5, [])
    s_val = DatasetSplit("val", val_gids, np.zeros((2, 1)), dummy_feat, ["Dijkstra"] * 2, [])
    s_test = DatasetSplit("test", test_gids, np.zeros((2, 1)), dummy_feat, ["Dijkstra"] * 2, [])

    split_data = SplitData(s_train, s_val, s_test, dummy_feat, tier=0)
    split_data.assert_no_graph_leakage()

    # Intentionally corrupt with leakage
    s_test_leaked = DatasetSplit("test", [train_gids[0]], np.zeros((1, 1)), dummy_feat, ["Dijkstra"], [])
    leaked_data = SplitData(s_train, s_val, s_test_leaked, dummy_feat, tier=0)
    with pytest.raises(ValueError, match="Data leakage detected"):
        leaked_data.assert_no_graph_leakage()


def test_leakage_audit():
    # 1. Allowed pre-solver features
    valid_cols = ["num_vertices", "average_degree", "source_degree", "weight_mean"]
    res = audit_feature_columns(valid_cols)
    assert res.passed is True
    assert len(res.violations) == 0

    # 2. Forbidden post-solver keyword
    forbidden_cols = ["num_vertices", "runtime_median", "vbs_cost", "nodes_expanded"]
    res_bad = audit_feature_columns(forbidden_cols)
    assert res_bad.passed is False
    assert len(res_bad.violations) >= 3

    # 3. Unknown column not in registry
    unknown_cols = ["num_vertices", "random_unregistered_metric"]
    res_unk = audit_feature_columns(unknown_cols)
    assert res_unk.passed is False


def test_decision_tree_fit_predict_evaluate():
    feature_names = ["num_vertices", "average_degree", "heuristic_available"]

    # Synthetic train split
    X_train = np.array([
        [50.0, 4.0, 0.0],
        [100.0, 8.0, 0.0],
        [50.0, 4.0, 1.0],
        [100.0, 8.0, 1.0],
    ])
    y_train = ["Dijkstra", "Bidirectional Dijkstra", "A*", "A*"]
    train_split = DatasetSplit("train", ["g1", "g2"], X_train, feature_names, y_train, [])

    # Synthetic test split with oracle metadata
    X_test = np.array([
        [50.0, 4.0, 0.0],
        [100.0, 8.0, 1.0],
    ])
    y_test = ["Dijkstra", "A*"]

    oracle_meta = [
        {
            "graph_id": "g3",
            "query_id": "q1",
            "total_feature_time": 0.0001,
            "oracle_instance": OracleInstance(
                graph_id="g3", query_id="q1", vbs_algorithm="Dijkstra", vbs_cost=0.002,
                dijkstra_cost=0.002, astar_cost=0.010, bidirectional_cost=0.003,
                valid_dijkstra=True, valid_astar=False, valid_bidirectional=True,
                always_dijkstra_cost=0.002, always_bidi_cost=0.003, always_astar_cost=0.002,
            )
        },
        {
            "graph_id": "g4",
            "query_id": "q2",
            "total_feature_time": 0.0002,
            "oracle_instance": OracleInstance(
                graph_id="g4", query_id="q2", vbs_algorithm="A*", vbs_cost=0.001,
                dijkstra_cost=0.005, astar_cost=0.001, bidirectional_cost=0.003,
                valid_dijkstra=True, valid_astar=True, valid_bidirectional=True,
                always_dijkstra_cost=0.005, always_bidi_cost=0.003, always_astar_cost=0.001,
            )
        }
    ]
    test_split = DatasetSplit("test", ["g3", "g4"], X_test, feature_names, y_test, oracle_meta)

    # Train selector
    selector = DecisionTreeSelector(max_depth=3, min_samples_leaf=1, random_state=42)
    selector.fit(train_split)
    assert selector.is_fitted is True

    # Evaluate
    eval_res = selector.evaluate(test_split, epsilon=0.05)
    assert eval_res.exact_accuracy == 1.0
    assert eval_res.near_best_accuracy == 1.0
    assert eval_res.num_queries == 2
    assert eval_res.mean_selection_time >= 0.0
    assert len(eval_res.feature_importances) == 3
    assert len(eval_res.tree_text) > 0
