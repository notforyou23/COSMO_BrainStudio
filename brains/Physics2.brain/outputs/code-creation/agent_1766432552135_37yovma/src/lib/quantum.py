"""Lightweight quantum-state utilities for toy entanglement diagnostics.

Conventions: states are 1D complex kets (dim,), density matrices are (dim, dim).
All functions are NumPy-only and deterministic given inputs/RNG.
"""

from __future__ import annotations

import numpy as np
# ---- Basic building blocks ----

def kron(*ops: np.ndarray) -> np.ndarray:
    """Kronecker product of many operators/vectors."""
    out = np.array([1.0], dtype=complex)
    for op in ops:
        out = np.kron(out, np.asarray(op, dtype=complex))
    return out


def basis(dim: int, i: int) -> np.ndarray:
    v = np.zeros(dim, dtype=complex)
    v[i] = 1.0
    return v


ket0 = basis(2, 0)
ket1 = basis(2, 1)


def normalize(psi: np.ndarray, tol: float = 1e-15) -> np.ndarray:
    psi = np.asarray(psi, dtype=complex).reshape(-1)
    n = np.linalg.norm(psi)
    if n < tol:
        raise ValueError("Cannot normalize near-zero vector")
    return psi / n


def dm(psi: np.ndarray) -> np.ndarray:
    """Density matrix from a pure state ket."""
    psi = np.asarray(psi, dtype=complex).reshape(-1)
    return np.outer(psi, psi.conj())
# ---- Common toy states ----

def product_state(kets: list[np.ndarray]) -> np.ndarray:
    """Tensor product ket from a list of subsystem kets."""
    return kron(*kets)


def bell_state(label: str = "phi+") -> np.ndarray:
    """Return one of the four Bell states as a ket (2 qubits)."""
    a = product_state([ket0, ket0])
    b = product_state([ket1, ket1])
    c = product_state([ket0, ket1])
    d = product_state([ket1, ket0])
    if label in ("phi+", "Φ+"):
        psi = a + b
    elif label in ("phi-", "Φ-"):
        psi = a - b
    elif label in ("psi+", "Ψ+"):
        psi = c + d
    elif label in ("psi-", "Ψ-"):
        psi = c - d
    else:
        raise ValueError(f"Unknown Bell label: {label}")
    return normalize(psi)  # 1/sqrt(2)


def ghz_state(n: int) -> np.ndarray:
    """n-qubit GHZ state (|0...0> + |1...1>)/sqrt(2)."""
    if n < 1:
        raise ValueError("n must be >= 1")
    return normalize(product_state([ket0] * n) + product_state([ket1] * n))


def random_pure(dim: int, rng: np.random.Generator) -> np.ndarray:
    """Haar-ish random pure state via complex Gaussian + normalization."""
    x = rng.normal(size=dim) + 1j * rng.normal(size=dim)
    return normalize(x)
# ---- Partial trace & reductions ----

def partial_trace(rho: np.ndarray, keep: list[int], dims: list[int]) -> np.ndarray:
    """Partial trace of density matrix over subsystems not in keep.

    Args:
        rho: (D,D) density matrix where D=prod(dims).
        keep: subsystem indices to keep (0..N-1).
        dims: list of subsystem dimensions.
    """
    dims = list(map(int, dims))
    N = len(dims)
    keep = sorted(set(map(int, keep)))
    if any(k < 0 or k >= N for k in keep):
        raise ValueError("keep indices out of range")
    rho = np.asarray(rho, dtype=complex)
    D = int(np.prod(dims))
    if rho.shape != (D, D):
        raise ValueError(f"rho shape {rho.shape} incompatible with dims (D={D})")
    traced = [i for i in range(N) if i not in keep]
    out = rho.reshape(dims + dims)
    for s in sorted(traced, reverse=True):
        out = np.trace(out, axis1=s, axis2=s + N)
        dims.pop(s)
        N -= 1
    d = int(np.prod(dims)) if dims else 1
    return out.reshape(d, d)


def reduced_density(psi: np.ndarray, keep: list[int], dims: list[int]) -> np.ndarray:
    """Reduced density matrix from a pure state ket."""
    return partial_trace(dm(psi), keep=keep, dims=dims)
# ---- Entropies / mutual information ----

def entropy_vn(rho: np.ndarray, base: float = 2.0, tol: float = 1e-12) -> float:
    """Von Neumann entropy S(rho) = -Tr rho log rho."""
    rho = np.asarray(rho, dtype=complex)
    if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
        raise ValueError("rho must be square")
    # Ensure Hermitian numerical stability
    evals = np.linalg.eigvalsh((rho + rho.conj().T) / 2.0).real
    evals = np.clip(evals, 0.0, 1.0)
    evals = evals[evals > tol]
    if evals.size == 0:
        return 0.0
    return float(-(evals * (np.log(evals) / np.log(base))).sum())


def mutual_information(rho: np.ndarray, A: list[int], B: list[int], dims: list[int]) -> float:
    """I(A:B) = S(A)+S(B)-S(AB) for a joint density matrix."""
    A = sorted(set(map(int, A)))
    B = sorted(set(map(int, B)))
    AB = sorted(set(A + B))
    rhoA = partial_trace(rho, keep=A, dims=dims)
    rhoB = partial_trace(rho, keep=B, dims=dims)
    rhoAB = partial_trace(rho, keep=AB, dims=dims)
    return entropy_vn(rhoA) + entropy_vn(rhoB) - entropy_vn(rhoAB)
# ---- Simple evolutions (unitaries) ----

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
CNOT = np.array(
    [[1, 0, 0, 0],
     [0, 1, 0, 0],
     [0, 0, 0, 1],
     [0, 0, 1, 0]],
    dtype=complex,
)


def apply_unitary_state(U: np.ndarray, psi: np.ndarray) -> np.ndarray:
    U = np.asarray(U, dtype=complex)
    psi = np.asarray(psi, dtype=complex).reshape(-1)
    if U.shape[0] != U.shape[1] or U.shape[1] != psi.size:
        raise ValueError("dimension mismatch")
    return U @ psi


def apply_unitary_rho(U: np.ndarray, rho: np.ndarray) -> np.ndarray:
    U = np.asarray(U, dtype=complex)
    rho = np.asarray(rho, dtype=complex)
    if U.shape[0] != U.shape[1] or rho.shape != (U.shape[0], U.shape[0]):
        raise ValueError("dimension mismatch")
    return U @ rho @ U.conj().T
