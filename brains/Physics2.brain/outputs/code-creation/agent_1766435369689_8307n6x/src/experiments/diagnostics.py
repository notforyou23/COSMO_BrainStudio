"""Quantum/classical diagnostics for small finite-dimensional systems.

Utilities here are intentionally lightweight (NumPy-only) and aimed at toy
experiments: entanglement entropy, mutual information, correlators, and simple
decoherence/coherence metrics for density matrices.
"""
from __future__ import annotations

import numpy as np

_EPS = 1e-12

PAULI = {
    "I": np.array([[1, 0], [0, 1]], dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
}
def ket_to_rho(psi: np.ndarray) -> np.ndarray:
    """Projector |psi><psi| for a state vector (normalized or not)."""
    psi = np.asarray(psi, dtype=complex).reshape(-1)
    nrm = np.vdot(psi, psi).real
    if nrm < _EPS:
        raise ValueError("State has (near-)zero norm.")
    psi = psi / np.sqrt(nrm)
    return np.outer(psi, psi.conj())


def _log(x: np.ndarray, base: float) -> np.ndarray:
    return np.log(x) / np.log(base)


def entropy_vn(rho: np.ndarray, base: float = 2.0) -> float:
    """Von Neumann entropy S(ρ) = -Tr ρ log ρ (default in bits)."""
    rho = np.asarray(rho, dtype=complex)
    evals = np.linalg.eigvalsh((rho + rho.conj().T) / 2.0)
    evals = np.clip(evals.real, 0.0, 1.0)
    nz = evals[evals > _EPS]
    return float(-np.sum(nz * _log(nz, base)))


def purity(rho: np.ndarray) -> float:
    """Purity Tr(ρ²)."""
    rho = np.asarray(rho, dtype=complex)
    return float(np.trace(rho @ rho).real)


def dephase(rho: np.ndarray) -> np.ndarray:
    """Return fully dephased ρ in the computational basis (keep diagonal)."""
    rho = np.asarray(rho, dtype=complex)
    return np.diag(np.diag(rho))


def coherence_l1(rho: np.ndarray) -> float:
    """L1 coherence: sum_{i≠j} |ρ_{ij}| in computational basis."""
    rho = np.asarray(rho, dtype=complex)
    return float(np.sum(np.abs(rho)) - np.sum(np.abs(np.diag(rho))))


def decoherence_diagnostics(rho: np.ndarray, base: float = 2.0) -> dict:
    """Convenience bundle of simple 'quantum vs classical' metrics."""
    rho = np.asarray(rho, dtype=complex)
    rho_d = dephase(rho)
    return {
        "entropy": entropy_vn(rho, base=base),
        "purity": purity(rho),
        "coherence_l1": coherence_l1(rho),
        "diag_entropy": entropy_vn(rho_d, base=base),
        "offdiag_ratio": float(coherence_l1(rho) / (np.sum(np.abs(np.diag(rho))) + _EPS)),
    }
def partial_trace(rho: np.ndarray, dims: tuple[int, ...], keep: tuple[int, ...]) -> np.ndarray:
    """Partial trace over subsystems not in 'keep'.

    Args:
        rho: density matrix on ⊗_k C^{dims[k]} (shape (D,D))
        dims: subsystem dimensions, product equals D
        keep: indices of subsystems to keep (e.g. (0,2))
    """
    rho = np.asarray(rho, dtype=complex)
    dims = tuple(int(d) for d in dims)
    keep = tuple(int(i) for i in keep)
    n = len(dims)
    D = int(np.prod(dims))
    if rho.shape != (D, D):
        raise ValueError("rho shape incompatible with dims.")
    if any(i < 0 or i >= n for i in keep):
        raise ValueError("keep contains invalid subsystem index.")
    trace = tuple(i for i in range(n) if i not in keep)
    resh = rho.reshape(*dims, *dims)  # (a0..a_{n-1}, b0..b_{n-1})
    for i in sorted(trace, reverse=True):
        resh = np.trace(resh, axis1=i, axis2=i + resh.ndim // 2)
    kept_dims = [dims[i] for i in keep]
    dK = int(np.prod(kept_dims)) if kept_dims else 1
    return resh.reshape(dK, dK)
def mutual_information(rho: np.ndarray, dims: tuple[int, ...], A: tuple[int, ...], B: tuple[int, ...], base: float = 2.0) -> float:
    """Mutual information I(A:B)=S(A)+S(B)-S(AB) for disjoint A,B."""
    A, B = tuple(A), tuple(B)
    if set(A) & set(B):
        raise ValueError("A and B must be disjoint.")
    rhoA = partial_trace(rho, dims, A)
    rhoB = partial_trace(rho, dims, B)
    rhoAB = partial_trace(rho, dims, tuple(sorted(set(A) | set(B))))
    return entropy_vn(rhoA, base) + entropy_vn(rhoB, base) - entropy_vn(rhoAB, base)
def kron_n(ops: list[np.ndarray]) -> np.ndarray:
    """Kronecker product of a list of operators."""
    out = np.array([[1.0 + 0j]])
    for op in ops:
        out = np.kron(out, np.asarray(op, dtype=complex))
    return out


def local_op(op: np.ndarray, site: int, n: int, d: int = 2) -> np.ndarray:
    """Operator acting as op on 'site' and identity elsewhere (qudits size d)."""
    if site < 0 or site >= n:
        raise ValueError("site out of range.")
    I = np.eye(d, dtype=complex)
    ops = [I] * n
    ops[site] = np.asarray(op, dtype=complex)
    return kron_n(ops)


def correlator(rho: np.ndarray, op_i: np.ndarray, i: int, op_j: np.ndarray, j: int, n: int, d: int = 2) -> complex:
    """Two-point correlator ⟨op_i op_j⟩ for an n-site qudit chain."""
    Oi = local_op(op_i, i, n, d)
    Oj = local_op(op_j, j, n, d)
    return complex(np.trace(np.asarray(rho, complex) @ (Oi @ Oj)))
def example_bell_state() -> dict:
    """Example diagnostics for |Φ+> Bell state on 2 qubits."""
    psi = (np.kron([1, 0], [1, 0]) + np.kron([0, 1], [0, 1])) / np.sqrt(2)
    rho = ket_to_rho(psi)
    S_A = entropy_vn(partial_trace(rho, (2, 2), (0,)))
    I_AB = mutual_information(rho, (2, 2), (0,), (1,))
    zz = correlator(rho, PAULI["Z"], 0, PAULI["Z"], 1, n=2)
    return {"S(A)": S_A, "I(A:B)": I_AB, "<Z0 Z1>": float(np.real_if_close(zz))}


if __name__ == "__main__":
    out = example_bell_state()
    print("example_bell_state:", out)
