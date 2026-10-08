"""Automated data leakage audit for algorithm selection."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from oa_assp.features.schema import FEATURE_REGISTRY


# Forbidden substrings that must NEVER appear in selector feature columns
FORBIDDEN_KEYWORDS = [
    "runtime",
    "cost",
    "time",
    "distance_from_solver",
    "shortest_path",
    "vbs",
    "sbs",
    "winner",
    "actual_algorithm",
    "operation_count",
    "edges_examined",
    "relaxations",
    "heap_pushes",
    "heap_pops",
    "nodes_expanded",
    "forward_expansions",
    "backward_expansions",
    "edge_scans",
    "passes",
]


# Oracle and ground-truth columns that must NEVER appear in feature matrix
ORACLE_COLUMNS: Set[str] = {
    "vbs_algorithm",
    "vbs_cost",
    "dijkstra_cost",
    "astar_cost",
    "bidirectional_cost",
    "valid_dijkstra",
    "valid_astar",
    "valid_bidirectional",
    "always_dijkstra_cost",
    "always_bidi_cost",
    "always_astar_cost",
    "sbs_policy",
    "sbs_total_cost",
}

# Benchmark outcome columns that must NEVER appear in feature matrix
BENCHMARK_OUTCOME_COLUMNS: Set[str] = {
    "distance",
    "runtime_median",
    "runtime_mean",
    "runtime_std",
    "edges_examined",
    "relaxations",
    "heap_pushes",
    "heap_pops",
    "nodes_expanded",
    "forward_expansions",
    "backward_expansions",
    "edge_scans",
    "passes",
    "success",
    "reachable",
    "correct",
    "failure_reason",
}


@dataclass
class AuditResult:
    """Result of data leakage audit on a feature matrix."""

    passed: bool
    allowed_features: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "allowed_features": self.allowed_features,
            "violations": self.violations,
        }


def audit_feature_columns(column_names: List[str]) -> AuditResult:
    """Audit feature column names to verify no post-solver or oracle information is present.

    Enforces:
    1. Whitelist: every column must be in the registered pre-solver FEATURE_REGISTRY.
    2. Oracle disjointness: column_names intersect ORACLE_COLUMNS == empty.
    3. Benchmark outcome disjointness: column_names intersect BENCHMARK_OUTCOME_COLUMNS == empty.
    4. Blacklist: no column name may contain forbidden post-solver substrings.
    """
    violations: List[str] = []
    allowed: List[str] = []
    col_set = set(column_names)

    # 1. Oracle disjointness check
    oracle_intersection = col_set & ORACLE_COLUMNS
    if oracle_intersection:
        violations.append(f"Feature columns intersect oracle columns: {oracle_intersection}")

    # 2. Benchmark outcome disjointness check
    outcome_intersection = col_set & BENCHMARK_OUTCOME_COLUMNS
    if outcome_intersection:
        violations.append(f"Feature columns intersect benchmark outcome columns: {outcome_intersection}")

    # 3. Whitelist & Blacklist check per column
    for col in column_names:
        if col not in FEATURE_REGISTRY:
            violations.append(f"Column '{col}' is not in pre-solver FEATURE_REGISTRY allowlist.")
            continue

        meta = FEATURE_REGISTRY[col]
        if not meta.pre_solver:
            violations.append(f"Column '{col}' is explicitly marked pre_solver=False in registry.")

        lower_col = col.lower()
        for kw in FORBIDDEN_KEYWORDS:
            if kw in lower_col:
                violations.append(f"Column '{col}' contains forbidden post-solver keyword '{kw}'.")

        if not any(v.startswith(f"Column '{col}'") for v in violations):
            allowed.append(col)

    passed = (len(violations) == 0)
    return AuditResult(passed=passed, allowed_features=allowed, violations=violations)
