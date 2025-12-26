"""Graph/lattice construction utilities.

This module provides tiny, dependency-light graph builders used by the toy
emergence / entanglement diagnostics. Graphs are undirected and simple by
construction (no self-loops, no parallel edges).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np
Edge = Tuple[int, int]


def _canon_edge(u: int, v: int) -> Edge:
    if u == v:
        raise ValueError("self-loops are not allowed")
    return (u, v) if u < v else (v, u)


def _unique_edges(edges: Iterable[Edge], n: int) -> Tuple[Edge, ...]:
    seen = set()
    out = []
    for (u, v) in edges:
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError("edge endpoint out of range")
        e = _canon_edge(int(u), int(v))
        if e not in seen:
            seen.add(e)
            out.append(e)
    return tuple(out)
@dataclass(frozen=True)
class Graph:
    """Simple undirected graph container.

    Attributes
    ----------
    n : int
        Number of vertices labeled 0..n-1.
    edges : tuple[(u,v), ...]
        Canonical undirected edge list with u<v.
    coords : np.ndarray | None
        Optional vertex coordinates (n, d), useful for geometric graphs/lattices.
    """

    n: int
    edges: Tuple[Edge, ...]
    coords: Optional[np.ndarray] = None

    def adjacency(self, *, dtype=float) -> np.ndarray:
        a = np.zeros((self.n, self.n), dtype=dtype)
        for u, v in self.edges:
            a[u, v] = 1
            a[v, u] = 1
        return a

    def laplacian(self, *, dtype=float) -> np.ndarray:
        a = self.adjacency(dtype=dtype)
        deg = np.sum(a, axis=1)
        return np.diag(deg) - a

    def degrees(self) -> np.ndarray:
        d = np.zeros(self.n, dtype=int)
        for u, v in self.edges:
            d[u] += 1
            d[v] += 1
        return d
def path_graph(n: int) -> Graph:
    n = int(n)
    if n < 1:
        raise ValueError("n must be >= 1")
    edges = [(i, i + 1) for i in range(n - 1)]
    return Graph(n=n, edges=_unique_edges(edges, n))


def cycle_graph(n: int) -> Graph:
    n = int(n)
    if n < 3:
        raise ValueError("n must be >= 3")
    edges = [(i, (i + 1) % n) for i in range(n)]
    return Graph(n=n, edges=_unique_edges(edges, n))


def grid_2d(Lx: int, Ly: int, *, periodic: bool = False) -> Graph:
    """2D square lattice with optional periodic boundaries."""
    Lx, Ly = int(Lx), int(Ly)
    if Lx < 1 or Ly < 1:
        raise ValueError("Lx,Ly must be >= 1")
    def vid(x: int, y: int) -> int:
        return y * Lx + x

    edges = []
    for y in range(Ly):
        for x in range(Lx):
            if x + 1 < Lx:
                edges.append((vid(x, y), vid(x + 1, y)))
            elif periodic and Lx > 1:
                edges.append((vid(x, y), vid(0, y)))
            if y + 1 < Ly:
                edges.append((vid(x, y), vid(x, y + 1)))
            elif periodic and Ly > 1:
                edges.append((vid(x, y), vid(x, 0)))
    coords = np.array([(x, y) for y in range(Ly) for x in range(Lx)], dtype=float)
    return Graph(n=Lx * Ly, edges=_unique_edges(edges, Lx * Ly), coords=coords)
def erdos_renyi(n: int, p: float, *, rng: Optional[np.random.Generator] = None) -> Graph:
    """G(n,p) with independent edges."""
    n = int(n)
    if n < 1:
        raise ValueError("n must be >= 1")
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be in [0,1]")
    rng = np.random.default_rng() if rng is None else rng
    edges = []
    for i in range(n):
        r = rng.random(n - i - 1)
        js = np.where(r < p)[0]
        for off in js:
            edges.append((i, i + 1 + int(off)))
    return Graph(n=n, edges=_unique_edges(edges, n))


def random_geometric(
    n: int,
    radius: float,
    *,
    dim: int = 2,
    periodic: bool = True,
    rng: Optional[np.random.Generator] = None,
) -> Graph:
    """Random geometric graph on [0,1)^dim with optional torus metric."""
    n, dim = int(n), int(dim)
    if n < 1 or dim < 1:
        raise ValueError("n, dim must be >= 1")
    if radius <= 0:
        raise ValueError("radius must be > 0")
    rng = np.random.default_rng() if rng is None else rng
    x = rng.random((n, dim))
    edges = []
    for i in range(n):
        d = x[i + 1 :] - x[i]
        if periodic:
            d = np.minimum(np.abs(d), 1.0 - np.abs(d))
        dist = np.sqrt(np.sum(d * d, axis=1))
        js = np.where(dist <= radius)[0]
        for off in js:
            edges.append((i, i + 1 + int(off)))
    return Graph(n=n, edges=_unique_edges(edges, n), coords=x)
def subgraph(g: Graph, nodes: Sequence[int]) -> Graph:
    """Induced subgraph on `nodes`, relabeled to 0..k-1 in given order."""
    idx = [int(u) for u in nodes]
    k = len(idx)
    pos = {u: i for i, u in enumerate(idx)}
    edges = []
    for u, v in g.edges:
        if u in pos and v in pos:
            edges.append((pos[u], pos[v]))
    coords = None
    if g.coords is not None:
        coords = np.asarray(g.coords, dtype=float)[idx]
    return Graph(n=k, edges=_unique_edges(edges, k), coords=coords)
