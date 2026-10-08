"""Correctness validation and cross-algorithm distance verification."""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

from oa_assp.algorithms.base import SearchResult
from oa_assp.graphs.base import Graph


@dataclass
class ValidationResult:
    """Summary of cross-algorithm correctness validation for a query."""

    is_correct: bool
    distances: Dict[str, float] = field(default_factory=dict)
    paths: Dict[str, Optional[List[Any]]] = field(default_factory=dict)
    path_validations: Dict[str, bool] = field(default_factory=dict)
    diagnostics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_correct": self.is_correct,
            "distances": self.distances,
            "paths": self.paths,
            "path_validations": self.path_validations,
            "diagnostics": self.diagnostics,
        }


def verify_path(
    graph: Graph,
    source: Any,
    target: Any,
    path: Optional[List[Any]],
    expected_distance: float,
    tolerance: float = 1e-9,
) -> Tuple[bool, str]:
    """Verify that a reconstructed path is a valid walk from source to target with matching weight."""
    if math.isinf(expected_distance):
        if path is not None:
            return False, f"Expected unreachable path (None), but got path {path}."
        return True, "Path correctly None for unreachable query."

    if source == target:
        if path != [source]:
            return False, f"Source == target, expected [{source}], but got {path}."
        if abs(expected_distance) > tolerance:
            return False, f"Source == target, expected distance 0.0, but got {expected_distance}."
        return True, "Valid trivial path for source == target."

    if path is None:
        return False, f"Path is None but distance is finite ({expected_distance})."

    if len(path) < 2:
        return False, f"Path length must be at least 2 for distinct source/target, got {path}."

    if path[0] != source:
        return False, f"Path does not start at source {source}, starts at {path[0]}."

    if path[-1] != target:
        return False, f"Path does not end at target {target}, ends at {path[-1]}."

    total_weight = 0.0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        if not graph.has_edge(u, v):
            return False, f"Path contains nonexistent edge ({u}, {v})."
        total_weight += graph.get_weight(u, v)

    if abs(total_weight - expected_distance) > tolerance:
        return False, (
            f"Path edge weight sum {total_weight} does not match expected distance "
            f"{expected_distance} (diff: {abs(total_weight - expected_distance):.2e} > tol {tolerance:.2e})."
        )

    return True, "Path is valid."


def validate_results(
    graph: Graph,
    source: Any,
    target: Any,
    results: Dict[str, SearchResult],
    tolerance: float = 1e-9,
) -> ValidationResult:
    """Validate that all provided algorithm results agree on distance and have valid paths."""
    distances: Dict[str, float] = {}
    paths: Dict[str, Optional[List[Any]]] = {}
    path_validations: Dict[str, bool] = {}
    diagnostics: List[str] = []
    is_correct = True

    if not results:
        return ValidationResult(
            is_correct=False,
            diagnostics=["No algorithm results provided for validation."],
        )

    # Collect distances and validate individual paths
    for algo_name, res in results.items():
        distances[algo_name] = res.distance
        paths[algo_name] = res.path

        # Verify path validity if path was requested and distance is not -inf (neg cycle)
        if res.distance != -math.inf:
            p_valid, p_diag = verify_path(
                graph=graph,
                source=source,
                target=target,
                path=res.path,
                expected_distance=res.distance,
                tolerance=tolerance,
            )
            path_validations[algo_name] = p_valid
            if not p_valid:
                is_correct = False
                diagnostics.append(f"[{algo_name}] Path validation failed: {p_diag}")
        else:
            path_validations[algo_name] = (res.path is None)

    # Compare distances across algorithms
    algo_items = list(distances.items())
    for i in range(len(algo_items)):
        name1, d1 = algo_items[i]
        for j in range(i + 1, len(algo_items)):
            name2, d2 = algo_items[j]

            # Both unreachable
            if math.isinf(d1) and math.isinf(d2):
                if (d1 > 0 and d2 > 0) or (d1 < 0 and d2 < 0):
                    continue

            # Finite distance comparison
            if math.isfinite(d1) and math.isfinite(d2):
                diff = abs(d1 - d2)
                if diff > tolerance:
                    is_correct = False
                    diagnostics.append(
                        f"Distance mismatch between {name1} ({d1}) and {name2} ({d2}): "
                        f"diff {diff:.2e} > tolerance {tolerance:.2e}"
                    )
            else:
                is_correct = False
                diagnostics.append(
                    f"Finiteness mismatch between {name1} ({d1}) and {name2} ({d2})."
                )

    return ValidationResult(
        is_correct=is_correct,
        distances=distances,
        paths=paths,
        path_validations=path_validations,
        diagnostics=diagnostics,
    )
