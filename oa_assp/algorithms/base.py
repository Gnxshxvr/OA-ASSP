"""Base data structures and interfaces for shortest-path algorithms."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Protocol, Tuple, Callable


@dataclass
class OperationCounters:
    """Deterministic operation counters for shortest-path algorithms."""

    edges_examined: int = 0
    relaxations: int = 0
    heap_pushes: int = 0
    heap_pops: int = 0
    nodes_expanded: int = 0  # finalized/visited nodes
    forward_expansions: int = 0
    backward_expansions: int = 0
    edge_scans: int = 0  # Bellman-Ford
    passes: int = 0  # Bellman-Ford

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.edges_examined = 0
        self.relaxations = 0
        self.heap_pushes = 0
        self.heap_pops = 0
        self.nodes_expanded = 0
        self.forward_expansions = 0
        self.backward_expansions = 0
        self.edge_scans = 0
        self.passes = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class SearchResult:
    """Structured result returned by all shortest-path solvers."""

    distance: float
    path: Optional[List[Any]] = None
    runtime: float = 0.0
    success: bool = True  # Completed without runtime exception
    reachable: bool = True  # Target was reachable from source
    counters: OperationCounters = field(default_factory=OperationCounters)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "distance": self.distance,
            "path_length": len(self.path) if self.path is not None else 0,
            "runtime": self.runtime,
            "success": self.success,
            "reachable": self.reachable,
            "counters": self.counters.to_dict(),
            "metadata": self.metadata,
        }


# Type alias for heuristic function: h(u, target) -> float
HeuristicFn = Callable[[Any, Any], float]
