"""Trivial baselines for algorithm selection.

These exist so that the decision tree can be compared against a selector that
learns nothing, which is the only way to tell whether the tree captured any
transferable structure at all.

All baselines are fitted on TRAINING data only.
"""

from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from oa_assp.benchmark.oracle import OracleInstance, policy_cost_for_instance
from oa_assp.selector.decision_tree import _solver_cost_for_prediction


@dataclass
class BaselineEvaluation:
    """Evaluation of a constant policy on a set of instances."""

    name: str
    policy: str
    num_queries: int
    exact_accuracy: float
    near_best_accuracy: float
    total_selected_solver_runtime: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "policy": self.policy,
            "num_queries": self.num_queries,
            "exact_accuracy": self.exact_accuracy,
            "near_best_accuracy": self.near_best_accuracy,
            "total_selected_solver_runtime": self.total_selected_solver_runtime,
        }


class MajorityPolicySelector:
    """Predict the most frequent VBS winner observed in the training data."""

    def __init__(self, name: str = "majority_label") -> None:
        self.name = name
        self.policy: Optional[str] = None
        self.label_counts: Dict[str, int] = {}

    def fit_labels(self, labels: List[str]) -> "MajorityPolicySelector":
        if not labels:
            raise ValueError("Cannot fit a majority policy on an empty label list.")
        counts = Counter(str(l) for l in labels)
        self.label_counts = dict(counts)
        self.policy = counts.most_common(1)[0][0]
        return self

    def fit_instances(self, oracle_instances: List[OracleInstance]) -> "MajorityPolicySelector":
        """Fit from the VBS winner labels of the supplied (training) instances."""
        return self.fit_labels([inst.vbs_algorithm for inst in oracle_instances if inst.vbs_algorithm != "none"])


class FixedPolicySelector:
    """A fixed policy expressed in the oracle's policy vocabulary or in algorithm names."""

    def __init__(self, policy: str, name: str = "fixed_policy") -> None:
        self.policy = policy
        self.name = name


def evaluate_constant_policy(
    instances: List[OracleInstance],
    algorithm: str,
    epsilon: float = 0.05,
    name: Optional[str] = None,
) -> BaselineEvaluation:
    """Evaluate a constant algorithm policy (by algorithm name) on oracle instances."""
    n = len(instances)
    if n == 0:
        raise ValueError("No instances to evaluate.")

    exact = 0
    near = 0
    total = 0.0
    for inst in instances:
        cost = _solver_cost_for_prediction(algorithm, inst)
        total += cost
        if inst.vbs_algorithm == algorithm:
            exact += 1
        if cost <= (1.0 + epsilon) * inst.vbs_cost + 1e-12:
            near += 1

    return BaselineEvaluation(
        name=name or f"Always-{algorithm}",
        policy=algorithm,
        num_queries=n,
        exact_accuracy=exact / n,
        near_best_accuracy=near / n,
        total_selected_solver_runtime=total,
    )


def evaluate_oracle_policy(
    instances: List[OracleInstance],
    policy: str,
    epsilon: float = 0.05,
) -> BaselineEvaluation:
    """Evaluate a fixed oracle policy (e.g. Always-Bidirectional-Dijkstra)."""
    n = len(instances)
    if n == 0:
        raise ValueError("No instances to evaluate.")

    exact = 0
    near = 0
    total = 0.0
    for inst in instances:
        cost = policy_cost_for_instance(inst, policy)
        total += cost
        if policy == "Always-Dijkstra" and inst.vbs_algorithm == "Dijkstra":
            exact += 1
        elif policy == "Always-Bidirectional-Dijkstra" and inst.vbs_algorithm == "Bidirectional Dijkstra":
            exact += 1
        elif policy == "Always-A*" and inst.vbs_algorithm == "A*":
            exact += 1
        if cost <= (1.0 + epsilon) * inst.vbs_cost + 1e-12:
            near += 1

    return BaselineEvaluation(
        name=policy,
        policy=policy,
        num_queries=n,
        exact_accuracy=exact / n,
        near_best_accuracy=near / n,
        total_selected_solver_runtime=total,
    )
