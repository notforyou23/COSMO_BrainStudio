"""Small quantum-state utilities.

Provides constructors for common n-qubit states, density-matrix helpers,
partial traces, and von Neumann/Rényi entropies (base-2 by default).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple, Union, Optional

import numpy as np

Array = np.ndarray
def set_seed(seed: Optional[int] = None) -> np.random.Generator:
    """Return a reproducible RNG (NumPy Generator)."""
    return np.random.default_rng(seed)


def _as_complex(a: Array) -> Array:
    a = np.asarray(a)
    return a.astype(np.complex128, copy=False)


def normalize_state(psi: Array) -> Array:
    """Normalize a statevector."""
    psi = _as_complex(psi).reshape(-1)
    n = np.linalg.norm(psi)
    if n == 0:
        raise ValueError("Cannot normalize zero state.")
    return psi / n


def ket(bit: int) -> Array:
    """Computational basis ket |0>, |1>."""
    if bit not in (0, 1):
        raise ValueError("bit must be 0 or 1")
    v = np.zeros(2, dtype=np.complex128)
    v[bit] = 1.0
    return v


def kron(*ops: Array) -> Array:
    """Kronecker product of many arrays."""
    out = np.array([1.0], dtype=np.complex128)
    for op in ops:
        out = np.kron(out, _as_complex(op))
    return out
def density_matrix_from_state(psi: Array) -> Array:
    """|psi><psi| for a (possibly unnormalized) statevector."""
    psi = normalize_state(psi)
    return np.outer(psi, np.conjugate(psi))


def is_hermitian(rho: Array, tol: float = 1e-10) -> bool:
    rho = _as_complex(rho)
    return np.allclose(rho, rho.conj().T, atol=tol, rtol=0)


def random_pure_state(dim: int, rng: Optional[np.random.Generator] = None) -> Array:
    """Haar-ish random pure state via complex normal + normalization."""
    rng = rng or np.random.default_rng()
    x = rng.normal(size=dim) + 1j * rng.normal(size=dim)
    return normalize_state(x)


def random_density_matrix(
    dim: int, rank: Optional[int] = None, rng: Optional[np.random.Generator] = None
) -> Array:
    """Random density matrix from Wishart ensemble (optionally low rank)."""
    rng = rng or np.random.default_rng()
    r = dim if rank is None else int(rank)
    x = rng.normal(size=(dim, r)) + 1j * rng.normal(size=(dim, r))
    rho = x @ x.conj().T
    rho = rho / np.trace(rho)
    return _as_complex(rho)
def bell_state(label: str = "phi+") -> Array:
    """Return 2-qubit Bell statevector (phi+/phi-/psi+/psi-)."""
    z0, z1 = ket(0), ket(1)
    if label == "phi+":
        psi = (kron(z0, z0) + kron(z1, z1)) / np.sqrt(2)
    elif label == "phi-":
        psi = (kron(z0, z0) - kron(z1, z1)) / np.sqrt(2)
    elif label == "psi+":
        psi = (kron(z0, z1) + kron(z1, z0)) / np.sqrt(2)
    elif label == "psi-":
        psi = (kron(z0, z1) - kron(z1, z0)) / np.sqrt(2)
    else:
        raise ValueError("label must be one of phi+, phi-, psi+, psi-")
    return _as_complex(psi)


def ghz_state(n: int) -> Array:
    """n-qubit GHZ: (|0..0> + |1..1>)/sqrt(2)."""
    if n < 1:
        raise ValueError("n must be >= 1")
    z0, z1 = ket(0), ket(1)
    psi0 = z0
    psi1 = z1
    for _ in range(n - 1):
        psi0 = kron(psi0, z0)
        psi1 = kron(psi1, z1)
    return _as_complex((psi0 + psi1) / np.sqrt(2))


def w_state(n: int) -> Array:
    """n-qubit W state: uniform superposition of Hamming-weight-1 basis states."""
    if n < 1:
        raise ValueError("n must be >= 1")
    dim = 2**n
    psi = np.zeros(dim, dtype=np.complex128)
    for i in range(n):
        psi[1 << (n - 1 - i)] = 1.0
    return normalize_state(psi)
def partial_trace(
    rho: Array, dims: Sequence[int], keep: Sequence[int]
) -> Array:
    """Partial trace of density matrix.

    Args:
        rho: (D,D) density matrix with D=prod(dims)
        dims: subsystem dimensions, e.g. [2,2,2]
        keep: indices of subsystems to keep (0-based)
    Returns:
        Reduced density matrix on kept subsystems.
    """
    rho = _as_complex(rho)
    dims = list(map(int, dims))
    n = len(dims)
    keep = list(map(int, keep))
    if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
        raise ValueError("rho must be a square matrix")
    D = int(np.prod(dims))
    if rho.shape[0] != D:
        raise ValueError("rho shape incompatible with dims")
    if any(k < 0 or k >= n for k in keep):
        raise ValueError("keep indices out of range")
    trace_out = [i for i in range(n) if i not in keep]

    reshaped = rho.reshape(*dims, *dims)  # (i1..in, j1..jn)
    for ax in sorted(trace_out, reverse=True):
        reshaped = np.trace(reshaped, axis1=ax, axis2=ax + n)
    kept_dims = [dims[i] for i in keep]
    dkeep = int(np.prod(kept_dims)) if kept_dims else 1
    return reshaped.reshape(dkeep, dkeep)
def _safe_eigvals(rho: Array, tol: float = 1e-15) -> Array:
    rho = _as_complex(rho)
    # Ensure Hermitian for numerical stability
    rho = 0.5 * (rho + rho.conj().T)
    vals = np.linalg.eigvalsh(rho)
    vals = np.real(vals)
    vals[vals < tol] = 0.0
    s = vals.sum()
    if s > 0 and not np.isclose(s, 1.0):
        vals = vals / s
    return vals


def von_neumann_entropy(rho: Array, base: float = 2.0) -> float:
    """S(rho) = -Tr rho log rho."""
    p = _safe_eigvals(rho)
    nz = p[p > 0]
    if nz.size == 0:
        return 0.0
    log = np.log(nz) / np.log(base)
    return float(-np.sum(nz * log))


def renyi_entropy(rho: Array, alpha: float = 2.0, base: float = 2.0) -> float:
    """Rényi entropy S_α(rho). Uses eigenvalues; alpha=1 -> von Neumann."""
    if alpha <= 0:
        raise ValueError("alpha must be > 0")
    if np.isclose(alpha, 1.0):
        return von_neumann_entropy(rho, base=base)
    p = _safe_eigvals(rho)
    val = np.sum(p**alpha)
    if val <= 0:
        return 0.0
    return float(np.log(val) / (1.0 - alpha) / np.log(base))
