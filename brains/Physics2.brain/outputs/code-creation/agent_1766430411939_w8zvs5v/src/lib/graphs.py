"""Graph helpers for emergent-geometry toy diagnostics.

The experiments in this repo use small graphs (lattices / causal-like DAGs) as
stand-ins for discrete substrate structure. This module provides:
- constructors for simple graphs,
- shortest-path distance utilities,
- mapping of an "entanglement" matrix onto edge weights + derived distances.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
import networkx as nx
def grid_2d_graph(
    Lx: int,
    Ly: int,
    *,
    periodic: bool = False,
    diagonal: bool = False,
) -> nx.Graph:
    """Return an Lx x Ly undirected grid graph.

    Nodes are integer tuples (x, y). If periodic=True, boundaries wrap.
    If diagonal=True, add (x±1,y±1) neighbors as well (Chebyshev adjacency).
    """
    if Lx <= 0 or Ly <= 0:
        raise ValueError("Lx and Ly must be positive")
    G = nx.Graph()
    for x in range(Lx):
        for y in range(Ly):
            G.add_node((x, y))
            for dx, dy in [(1, 0), (0, 1)]:
                nx_, ny_ = x + dx, y + dy
                if periodic:
                    nx_, ny_ = nx_ % Lx, ny_ % Ly
                if 0 <= nx_ < Lx and 0 <= ny_ < Ly:
                    G.add_edge((x, y), (nx_, ny_))
            if diagonal:
                for dx, dy in [(1, 1), (1, -1)]:
                    nx_, ny_ = x + dx, y + dy
                    if periodic:
                        nx_, ny_ = nx_ % Lx, ny_ % Ly
                    if 0 <= nx_ < Lx and 0 <= ny_ < Ly:
                        G.add_edge((x, y), (nx_, ny_))
    return G
def ring_graph(n: int, *, k: int = 1) -> nx.Graph:
    """Return an undirected ring with n nodes and k-nearest neighbor edges."""
    if n <= 2:
        raise ValueError("n must be > 2")
    if k <= 0 or k >= n // 2 + 1:
        raise ValueError("k must be in [1, floor(n/2)]")
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for i in range(n):
        for d in range(1, k + 1):
            G.add_edge(i, (i + d) % n)
    return G
def random_causal_dag(
    n: int,
    p: float,
    *,
    seed: Optional[int] = None,
    time_order: Optional[Sequence[int]] = None,
) -> nx.DiGraph:
    """Return a simple random DAG respecting a time ordering.

    Edges only go forward in the provided order (default: 0..n-1). For each
    ordered pair (i<j) an edge is included with probability p.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be in [0,1]")
    order = list(range(n)) if time_order is None else list(time_order)
    if len(order) != n or len(set(order)) != n:
        raise ValueError("time_order must be a permutation of n labels")
    rng = np.random.default_rng(seed)
    pos = {node: t for t, node in enumerate(order)}
    G = nx.DiGraph()
    G.add_nodes_from(order)
    for a in order:
        for b in order:
            if pos[a] < pos[b] and rng.random() < p:
                G.add_edge(a, b)
    return G
def shortest_path_distances(
    G: Union[nx.Graph, nx.DiGraph],
    *,
    weight: Optional[str] = None,
) -> Dict[Tuple[object, object], float]:
    """All-pairs shortest path distances as a flat dict keyed by (u,v)."""
    d: Dict[Tuple[object, object], float] = {}
    for u, dist_u in nx.all_pairs_dijkstra_path_length(G, weight=weight):
        for v, dv in dist_u.items():
            d[(u, v)] = float(dv)
    return d
def entanglement_weighted_graph(
    base: Union[nx.Graph, nx.DiGraph],
    E: np.ndarray,
    *,
    nodes: Optional[Sequence[object]] = None,
    mode: str = "neglog",
    eps: float = 1e-12,
) -> Union[nx.Graph, nx.DiGraph]:
    """Copy base graph and assign edge weight from entanglement matrix E.

    Parameters
    ----------
    base:
        Graph defining which edges exist.
    E:
        NxN matrix (not necessarily symmetric) giving entanglement strength.
    nodes:
        Optional explicit node ordering matching E. Default: list(base.nodes()).
    mode:
        How to convert entanglement to distance-like edge weights:
        - "neglog": w = -log(E+eps)  (large E -> short edge)
        - "inv":    w = 1/(E+eps)
        - "one_minus": w = 1 - clip(E,0,1)
    eps:
        Small constant for numerical stability.

    Returns
    -------
    Graph with edge attribute 'weight'.
    """
    node_list = list(base.nodes()) if nodes is None else list(nodes)
    n = len(node_list)
    E = np.asarray(E, dtype=float)
    if E.shape != (n, n):
        raise ValueError(f"E must have shape ({n},{n}), got {E.shape}")
    idx = {node: i for i, node in enumerate(node_list)}
    H = base.copy()
    for u, v in H.edges():
        euv = float(E[idx[u], idx[v]])
        if mode == "neglog":
            w = -np.log(max(euv, 0.0) + eps)
        elif mode == "inv":
            w = 1.0 / (euv + eps)
        elif mode == "one_minus":
            w = 1.0 - float(np.clip(euv, 0.0, 1.0))
        else:
            raise ValueError("mode must be one of: neglog, inv, one_minus")
        H.edges[u, v]["entanglement"] = euv
        H.edges[u, v]["weight"] = float(w)
    return H
@dataclass(frozen=True)
class GeometryDiagnostics:
    """Lightweight emergent-geometry summary statistics."""

    n: int
    m: int
    mean_distance: float
    diameter: float
    clustering: float


def geometry_diagnostics(
    G: Union[nx.Graph, nx.DiGraph],
    *,
    weight: Optional[str] = None,
    sample: Optional[int] = None,
    seed: Optional[int] = None,
) -> GeometryDiagnostics:
    """Compute a small set of diagnostics for emergent geometry.

    If sample is provided, estimate mean distance using that many random sources.
    Diameter is computed exactly for small graphs; for large graphs consider
    using sample to keep runtime predictable.
    """
    nodes = list(G.nodes())
    n = len(nodes)
    m = G.number_of_edges()
    if n == 0:
        return GeometryDiagnostics(0, 0, float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    sources = nodes if (sample is None or sample >= n) else list(rng.choice(nodes, size=sample, replace=False))
    dists: List[float] = []
    diam = 0.0
    for s in sources:
        dist_s = nx.single_source_dijkstra_path_length(G, s, weight=weight)
        vals = [float(v) for v in dist_s.values()]
        if len(vals) > 1:
            dists.extend(vals)
            diam = max(diam, max(vals))
    mean_d = float(np.mean(dists)) if dists else 0.0
    clust = float(nx.average_clustering(G.to_undirected())) if n >= 3 else 0.0
    return GeometryDiagnostics(n=n, m=m, mean_distance=mean_d, diameter=float(diam), clustering=clust)
