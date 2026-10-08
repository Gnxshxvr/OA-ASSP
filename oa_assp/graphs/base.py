"""Base graph data structure for OA-ASSP."""

from __future__ import annotations
from typing import Dict, Any, Tuple, Optional, Iterator, Set, List


class Graph:
    """Directed graph representation with forward and reverse adjacency.
    
    Supports edge weights, node coordinates for geometric heuristics,
    and efficient querying of in/out neighborhoods.
    """

    def __init__(self, directed: bool = True, graph_id: str = "") -> None:
        self.directed: bool = directed
        self.graph_id: str = graph_id
        self.metadata: Dict[str, Any] = {}
        self.adj: Dict[Any, Dict[Any, float]] = {}
        self.rev_adj: Dict[Any, Dict[Any, float]] = {}
        self.coords: Dict[Any, Tuple[float, ...]] = {}
        self._num_edges: int = 0
        self._has_negative_edge: bool = False

    def add_node(self, node: Any, coords: Optional[Tuple[float, ...]] = None) -> None:
        """Add a node to the graph with optional spatial coordinates."""
        if node not in self.adj:
            self.adj[node] = {}
            self.rev_adj[node] = {}
        if coords is not None:
            self.coords[node] = coords

    def add_edge(
        self,
        u: Any,
        v: Any,
        weight: float = 1.0,
        bidirectional: Optional[bool] = None,
    ) -> None:
        """Add a directed or undirected edge with weight.
        
        If bidirectional is None, uses self.directed (if not directed, bidirectional=True).
        """
        self.add_node(u)
        self.add_node(v)

        is_bidi = (not self.directed) if bidirectional is None else bidirectional

        if v not in self.adj[u]:
            self._num_edges += 1
        self.adj[u][v] = float(weight)
        self.rev_adj[v][u] = float(weight)

        if weight < 0:
            self._has_negative_edge = True

        if is_bidi and u != v:
            if u not in self.adj[v]:
                self._num_edges += 1
            self.adj[v][u] = float(weight)
            self.rev_adj[u][v] = float(weight)

    @property
    def num_nodes(self) -> int:
        return len(self.adj)

    @property
    def num_edges(self) -> int:
        return self._num_edges

    @property
    def nodes(self) -> List[Any]:
        return list(self.adj.keys())

    @property
    def has_negative_edge(self) -> bool:
        return self._has_negative_edge

    def neighbors(self, u: Any) -> Dict[Any, float]:
        """Outgoing neighbors and weights from u."""
        return self.adj.get(u, {})

    def in_neighbors(self, u: Any) -> Dict[Any, float]:
        """Incoming neighbors and weights to u."""
        return self.rev_adj.get(u, {})

    def get_weight(self, u: Any, v: Any) -> float:
        """Get weight of edge (u, v)."""
        return self.adj[u][v]

    def has_edge(self, u: Any, v: Any) -> bool:
        return u in self.adj and v in self.adj[u]

    def out_degree(self, u: Any) -> int:
        return len(self.adj.get(u, {}))

    def in_degree(self, u: Any) -> int:
        return len(self.rev_adj.get(u, {}))

    def degree(self, u: Any) -> int:
        if not self.directed:
            return self.out_degree(u)
        return self.out_degree(u) + self.in_degree(u)

    def edges(self) -> Iterator[Tuple[Any, Any, float]]:
        """Iterate over all directed edges (u, v, weight)."""
        for u, nbrs in self.adj.items():
            for v, weight in nbrs.items():
                yield u, v, weight

    def __len__(self) -> int:
        return self.num_nodes

    def __contains__(self, node: Any) -> bool:
        return node in self.adj
