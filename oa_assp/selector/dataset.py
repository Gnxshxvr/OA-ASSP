"""Dataset preparation and graph-level train/validation/test splitting for selector."""

from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from typing import Any, Dict, List, Optional, Set, Tuple

from oa_assp.benchmark.oracle import OracleInstance, OracleSummary
from oa_assp.features.extractor import FeatureExtractor
from oa_assp.features.schema import ExtractedFeatures, get_feature_names_for_tier
from oa_assp.graphs.base import Graph
from oa_assp.graphs.queries import Query
from oa_assp.selector.validation import audit_feature_columns


@dataclass
class DatasetSplit:
    """A single graph-level dataset split (e.g. train, validation, or test)."""

    split_name: str
    graph_ids: List[str]
    X: np.ndarray
    feature_names: List[str]
    y: List[str]  # VBS winner labels
    metadata: List[Dict[str, Any]]  # Traceability: graph_id, query_id, feature_time, oracle_instance


@dataclass
class SplitData:
    """Container for train, validation, and test splits with graph-level separation."""

    train: DatasetSplit
    val: Optional[DatasetSplit]
    test: DatasetSplit
    all_feature_names: List[str]
    tier: int

    def assert_no_graph_leakage(self) -> None:
        """Verify that train, validation, and test graph sets are strictly disjoint."""
        train_set = set(self.train.graph_ids)
        test_set = set(self.test.graph_ids)
        val_set = set(self.val.graph_ids) if self.val is not None else set()

        overlap_train_test = train_set & test_set
        overlap_train_val = train_set & val_set
        overlap_val_test = val_set & test_set

        if overlap_train_test:
            raise ValueError(f"Data leakage detected! Graphs in both train and test: {overlap_train_test}")
        if overlap_train_val:
            raise ValueError(f"Data leakage detected! Graphs in both train and val: {overlap_train_val}")
        if overlap_val_test:
            raise ValueError(f"Data leakage detected! Graphs in both val and test: {overlap_val_test}")


def split_graphs(
    graph_ids: List[str],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[str], List[str], List[str]]:
    """Partition unique graph IDs into disjoint train, validation, and test sets."""
    unique_ids = sorted(list(set(graph_ids)))
    n_graphs = len(unique_ids)

    if n_graphs == 0:
        raise ValueError("No graphs to split.")

    rng = np.random.default_rng(seed)
    shuffled = [str(x) for x in rng.permutation(unique_ids)]

    if n_graphs == 1:
        # Edge case for tiny tests
        return shuffled, [], shuffled
    elif n_graphs == 2:
        return [shuffled[0]], [], [shuffled[1]]
    elif n_graphs == 3:
        if val_ratio == 0.0:
            return [shuffled[0], shuffled[1]], [], [shuffled[2]]
        return [shuffled[0]], [shuffled[1]], [shuffled[2]]

    n_train = max(1, int(round(n_graphs * train_ratio)))
    n_val = max(1, int(round(n_graphs * val_ratio))) if val_ratio > 0 else 0
    n_test = n_graphs - n_train - n_val

    if n_test < 1:
        n_test = 1
        if n_val > 1:
            n_val -= 1
        else:
            n_train -= 1

    train_ids = shuffled[:n_train]
    val_ids = shuffled[n_train:n_train + n_val]
    test_ids = shuffled[n_train + n_val:]

    return train_ids, val_ids, test_ids


def stratified_split_graphs(
    graphs: Dict[str, Graph],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[str], List[str], List[str]]:
    """Partition graphs with stratification by graph family ensuring zero overlap.

    Groups graph IDs by family (e.g. random, geometric, scale_free) and splits
    each family proportionally so all families are represented in train, val,
    and test splits (where sample size permits).
    """
    family_groups: Dict[str, List[str]] = {}
    for gid, g in graphs.items():
        fam = g.metadata.get("graph_family", gid.split("_")[0])
        family_groups.setdefault(fam, []).append(gid)

    all_train, all_val, all_test = [], [], []

    for idx, (fam, gids) in enumerate(sorted(family_groups.items())):
        fam_seed = seed + idx * 101
        tr, va, te = split_graphs(
            gids,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=fam_seed,
        )
        all_train.extend(tr)
        all_val.extend(va)
        all_test.extend(te)

    return all_train, all_val, all_test


def prepare_selector_dataset(
    graphs: Dict[str, Graph],
    queries_by_graph: Dict[str, List[Query]],
    oracle_summary: OracleSummary,
    tier: int = 1,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    stratified: bool = True,
    train_graph_ids: Optional[List[str]] = None,
    val_graph_ids: Optional[List[str]] = None,
    test_graph_ids: Optional[List[str]] = None,
) -> SplitData:
    """Extract features, audit for leakage, and perform graph-level splitting."""
    extractor = FeatureExtractor(default_tier=tier)
    feature_names = sorted(get_feature_names_for_tier(tier))

    # Audit feature names
    audit = audit_feature_columns(feature_names)
    if not audit.passed:
        raise ValueError(f"Leakage audit failed: {audit.violations}")

    # Map oracle instances by (graph_id, query_id)
    oracle_map: Dict[Tuple[str, str], OracleInstance] = {
        (inst.graph_id, inst.query_id): inst for inst in oracle_summary.instances
    }

    # Extract features for all graphs and queries
    all_records: List[Dict[str, Any]] = []
    for gid, graph in graphs.items():
        # Pay graph-level feature cost ONCE per graph
        g_features, g_time = extractor.extract_graph_features(graph, tier=tier)

        queries = queries_by_graph.get(gid, [])
        for q in queries:
            key = (gid, q.query_id)
            if key not in oracle_map:
                continue
            oracle_inst = oracle_map[key]

            # Pay query-level feature cost per query
            q_features, q_time = extractor.extract_query_features(graph, q, tier=tier)

            combined_features = dict(g_features)
            combined_features.update(q_features)

            record = {
                "graph_id": gid,
                "query_id": q.query_id,
                "features": [combined_features.get(fname, 0.0) for fname in feature_names],
                "y": oracle_inst.vbs_algorithm,
                "graph_feature_time": g_time,
                "query_feature_time": q_time,
                "total_feature_time": g_time + q_time,
                "oracle_instance": oracle_inst,
            }
            all_records.append(record)

    # Perform graph-level split
    if train_graph_ids is not None and test_graph_ids is not None:
        train_gids = sorted(list(train_graph_ids))
        val_gids = sorted(list(val_graph_ids)) if val_graph_ids is not None else []
        test_gids = sorted(list(test_graph_ids))
    elif stratified:
        train_gids, val_gids, test_gids = stratified_split_graphs(
            graphs, train_ratio=train_ratio, val_ratio=val_ratio, test_ratio=test_ratio, seed=seed
        )
    else:
        unique_gids = sorted(list(graphs.keys()))
        train_gids, val_gids, test_gids = split_graphs(
            unique_gids, train_ratio=train_ratio, val_ratio=val_ratio, test_ratio=test_ratio, seed=seed
        )

    def _build_split(split_name: str, target_gids: List[str]) -> DatasetSplit:
        split_records = [r for r in all_records if r["graph_id"] in target_gids]
        if split_records:
            X = np.array([r["features"] for r in split_records], dtype=float)
            y = [r["y"] for r in split_records]
        else:
            X = np.empty((0, len(feature_names)), dtype=float)
            y = []

        return DatasetSplit(
            split_name=split_name,
            graph_ids=target_gids,
            X=X,
            feature_names=feature_names,
            y=y,
            metadata=split_records,
        )

    train_split = _build_split("train", train_gids)
    val_split = _build_split("val", val_gids) if val_gids else None
    test_split = _build_split("test", test_gids)

    split_data = SplitData(
        train=train_split,
        val=val_split,
        test=test_split,
        all_feature_names=feature_names,
        tier=tier,
    )
    split_data.assert_no_graph_leakage()

    return split_data
