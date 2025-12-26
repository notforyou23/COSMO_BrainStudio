"""Entanglement diagnostics for small qubit systems.

Provides reproducible toy experiments computing von Neumann entanglement entropy
and mutual information for (i) small transverse-field Ising chains (exact
diagonalization) and (ii) graph/cluster states (CZ-on-|+> construction).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

try:
    from scipy.linalg import eigh
except Exception as _e:  # pragma: no cover
    eigh = None
# --- Basic quantum utilities ---


def _bits(x: int, n: int) -> List[int]:
    return [(x >> k) & 1 for k in range(n)]


def state_plus(n: int) -> np.ndarray:
    """|+>^{⊗n} statevector."""
    psi = np.ones(2**n, dtype=complex) / np.sqrt(2**n)
    return psi


def ghz_state(n: int) -> np.ndarray:
    psi = np.zeros(2**n, dtype=complex)
    psi[0] = psi[-1] = 1 / np.sqrt(2)
    return psi


def bell_state() -> np.ndarray:
    return ghz_state(2)


def w_state(n: int) -> np.ndarray:
    psi = np.zeros(2**n, dtype=complex)
    for k in range(n):
        psi[1 << k] = 1 / np.sqrt(n)
    return psi


def graph_state(n: int, edges: Sequence[Tuple[int, int]]) -> np.ndarray:
    """Graph state: apply CZ for each undirected edge on |+>^{⊗n}."""
    psi = state_plus(n).copy()
    for i, j in edges:
        if i == j:
            continue
        if i > j:
            i, j = j, i
        mask = (1 << i) | (1 << j)
        for idx in range(2**n):
            if (idx & mask) == mask:
                psi[idx] *= -1
    return psi
def reduced_density_matrix(psi: np.ndarray, keep: Sequence[int], n: int) -> np.ndarray:
    """Reduced density matrix ρ_keep for a pure state |ψ> on n qubits."""
    keep = list(keep)
    if any((k < 0 or k >= n) for k in keep):
        raise ValueError("keep indices out of range")
    if len(set(keep)) != len(keep):
        raise ValueError("keep has duplicates")
    psi_t = psi.reshape((2,) * n)
    trace = [i for i in range(n) if i not in keep]
    rho = np.tensordot(psi_t, psi_t.conj(), axes=(trace, trace))
    d = 2 ** len(keep)
    return rho.reshape((d, d))


def von_neumann_entropy(rho: np.ndarray, base: float = 2.0) -> float:
    """S(ρ) = -Tr ρ log ρ, numerically stable for small matrices."""
    vals = np.linalg.eigvalsh((rho + rho.conj().T) / 2)
    vals = np.clip(vals.real, 0.0, 1.0)
    nz = vals[vals > 1e-15]
    return float(-(nz * (np.log(nz) / np.log(base))).sum())


def entanglement_entropy(psi: np.ndarray, A: Sequence[int], n: int) -> float:
    return von_neumann_entropy(reduced_density_matrix(psi, A, n))


def mutual_information(psi: np.ndarray, A: Sequence[int], B: Sequence[int], n: int) -> float:
    A, B = list(A), list(B)
    if set(A) & set(B):
        raise ValueError("A and B must be disjoint")
    S_A = entanglement_entropy(psi, A, n)
    S_B = entanglement_entropy(psi, B, n)
    S_AB = entanglement_entropy(psi, sorted(A + B), n)
    return S_A + S_B - S_AB
# --- Spin chain: transverse-field Ising model (exact diagonalization) ---

_PAULI_X = np.array([[0, 1], [1, 0]], dtype=complex)
_PAULI_Z = np.array([[1, 0], [0, -1]], dtype=complex)
_I2 = np.eye(2, dtype=complex)


def _kron_all(ops: Sequence[np.ndarray]) -> np.ndarray:
    out = ops[0]
    for op in ops[1:]:
        out = np.kron(out, op)
    return out


def _op_on(n: int, i: int, op: np.ndarray) -> np.ndarray:
    return _kron_all([op if k == i else _I2 for k in range(n)])


def tfim_hamiltonian(n: int, J: float = 1.0, h: float = 1.0, periodic: bool = False) -> np.ndarray:
    """H = -J Σ Z_i Z_{i+1} - h Σ X_i."""
    dim = 2**n
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(n):
        H += -h * _op_on(n, i, _PAULI_X)
    for i in range(n - 1 + int(periodic)):
        a, b = i, (i + 1) % n
        ops = [_PAULI_Z if k in (a, b) else _I2 for k in range(n)]
        H += -J * _kron_all(ops)
    return H


def tfim_ground_state(n: int, J: float = 1.0, h: float = 1.0, periodic: bool = False) -> np.ndarray:
    if eigh is None:
        raise ImportError("scipy is required for TFIM diagonalization")
    H = tfim_hamiltonian(n, J=J, h=h, periodic=periodic)
    vals, vecs = eigh(H)
    psi0 = vecs[:, np.argmin(vals)]
    return psi0 / np.linalg.norm(psi0)
@dataclass(frozen=True)
class EntanglementResult:
    name: str
    n: int
    partition: Tuple[Tuple[int, ...], Tuple[int, ...]]
    S_A: float
    S_B: float
    I_AB: float

    def as_dict(self) -> Dict[str, object]:
        A, B = self.partition
        return {
            "name": self.name,
            "n": self.n,
            "A": list(A),
            "B": list(B),
            "S_A": self.S_A,
            "S_B": self.S_B,
            "I_AB": self.I_AB,
        }


def diagnose_state(name: str, psi: np.ndarray, A: Sequence[int], B: Sequence[int], n: int) -> EntanglementResult:
    S_A = entanglement_entropy(psi, A, n)
    S_B = entanglement_entropy(psi, B, n)
    I_AB = mutual_information(psi, A, B, n)
    return EntanglementResult(name=name, n=n, partition=(tuple(A), tuple(B)), S_A=S_A, S_B=S_B, I_AB=I_AB)
# --- Reproducible toy experiment suite ---


def run_examples(seed: int = 0) -> List[Dict[str, object]]:
    """Return example diagnostics as JSON-serializable dicts."""
    np.random.seed(seed)
    out: List[EntanglementResult] = []

    # Bell pair: maximal entanglement; I(A:B)=2 bits.
    psi = bell_state()
    out.append(diagnose_state("bell", psi, A=[0], B=[1], n=2))

    # GHZ_4: any single qubit vs rest has S=1; pairwise MI between two single qubits is 1.
    psi = ghz_state(4)
    out.append(diagnose_state("ghz4_0|1", psi, A=[0], B=[1], n=4))
    out.append(diagnose_state("ghz4_0|123", psi, A=[0], B=[1, 2, 3], n=4))

    # 1D 4-qubit cluster state (line graph).
    edges = [(0, 1), (1, 2), (2, 3)]
    psi = graph_state(4, edges)
    out.append(diagnose_state("cluster4_01|23", psi, A=[0, 1], B=[2, 3], n=4))
    out.append(diagnose_state("cluster4_1|2", psi, A=[1], B=[2], n=4))

    # TFIM ground state: compare weak vs strong field.
    for h in (0.3, 1.5):
        psi = tfim_ground_state(6, J=1.0, h=h, periodic=False)
        out.append(diagnose_state(f"tfim6_h{h:.1f}_012|345", psi, A=[0, 1, 2], B=[3, 4, 5], n=6))

    return [r.as_dict() for r in out]


if __name__ == "__main__":  # pragma: no cover
    rows = run_examples(seed=0)
    for r in rows:
        print(r)
