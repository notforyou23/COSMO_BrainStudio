"""Measurement-protocol library.

Provides a small, prioritized, machine-readable registry of concrete measurement
protocols for correlators and entanglement diagnostics spanning analogue
platforms and astrophysical probes. The schema is designed for downstream
simulation and inference modules.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence
@dataclass(frozen=True)
class Protocol:
    """Machine-readable measurement protocol.

    Fields are JSON-serializable (lists/dicts/strings/numbers). `params` encodes
    discrete-structure knobs (e.g., sprinkling density rho, discreteness length
    ell_d, spectral dimension d_s) and how the measurement constrains them.
    """

    id: str
    title: str
    platform: str  # e.g. "BEC", "superconducting", "CMB", "GW"
    priority: int  # higher is earlier in a measurement campaign
    observables: Sequence[str]
    estimator: str  # concise description of the statistic returned
    protocol_steps: Sequence[str]
    data_requirements: Dict[str, Any]
    systematics: Sequence[str]
    params: Dict[str, Any] = field(default_factory=dict)
    references: Sequence[str] = ()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = "1.0"
        return d
# Curated protocols: concrete estimators + concrete readout steps.
_PROTOCOLS: List[Protocol] = [
    Protocol(
        id="analogue.bec.density_g2_k",
        title="BEC: equal-time density correlator g2(k) for dispersive microstructure",
        platform="BEC / atom-chip",
        priority=100,
        observables=["delta_n(x,t)", "g2(k,t)=<|delta_n_k|^2>/<n>^2"],
        estimator="Fit deviation of g2(k) from hydrodynamic prediction; extract k* crossover",
        protocol_steps=[
            "Prepare quasi-1D BEC; calibrate sound speed c_s and healing length xi",
            "Quench/drive to generate phonon population; hold time t_hold",
            "Acquire in-situ phase-contrast images; reconstruct density n(x)",
            "FFT to n_k; compute ensemble-averaged g2(k) and covariance",
            "Infer crossover scale k* and spectral tilt; map to ell_d via dispersion model",
        ],
        data_requirements={"shots": 1_000, "length_um": 200, "pixel_um": 0.5, "k_range": [0.0, 8.0]},
        systematics=[
            "Finite imaging resolution (MTF) and atom-number fluctuations",
            "Trap inhomogeneity; windowing/edge effects in FFT",
            "Nonlinear phonon-phonon interactions at high occupation",
        ],
        params={
            "targets": ["ell_d", "alpha_disp"],
            "likelihood": "Gaussian on binned g2(k); includes MTF nuisance",
            "mapping": "k* ~ 1/ell_d after rescaling by xi and c_s",
        },
        references=["analogue gravity density correlators", "dispersive phonons"],
    ),
    Protocol(
        id="analogue.sqc.two_mode_logneg",
        title="Superconducting circuit: two-mode squeezing and logarithmic negativity",
        platform="superconducting microwave / cQED",
        priority=95,
        observables=["I/Q quadratures", "covariance matrix V", "E_N"],
        estimator="Compute Gaussian log-negativity from calibrated quadrature covariance",
        protocol_steps=[
            "Implement parametric modulation to realize two-mode squeezing of itinerant modes",
            "Heterodyne-detect both outputs; calibrate gain, added noise, and phase",
            "Estimate 4x4 covariance matrix V from time streams; bootstrap errors",
            "Compute log-negativity E_N(V) and compare vs frequency-dependent dispersion",
        ],
        data_requirements={"bandwidth_MHz": 50, "records": 10_000, "calibration": ["gain", "noise", "phase"]},
        systematics=[
            "Added amplifier noise and drift; imperfect mode matching",
            "Finite detection bandwidth (filtering) biases V",
            "Non-Gaussian tails from rare switching events",
        ],
        params={
            "targets": ["kappa_nonlocal", "ell_d"],
            "likelihood": "Wishart/approx-Gaussian on V elements with calibration nuisances",
            "mapping": "frequency-dependent squeezing rolloff encodes nonlocal kernel scale",
        },
        references=["Gaussian entanglement diagnostics", "microwave two-mode squeezing"],
    ),
    Protocol(
        id="analogue.opt.lat.entropy_scaling",
        title="Optical lattice: entropy scaling and mutual information vs block size",
        platform="cold atoms in optical lattice",
        priority=90,
        observables=["R'enyi-2 entropy S2(L)", "mutual information I(A:B)"],
        estimator="Fit S2(L) to area/log-law + oscillatory corrections; constrain discreteness scale",
        protocol_steps=[
            "Prepare 1D/2D lattice near criticality; perform randomized measurements",
            "Estimate R'enyi-2 entropies for blocks of size L; compute I(A:B)",
            "Fit scaling forms with finite-size corrections and dispersion-induced UV cutoff",
        ],
        data_requirements={"random_unitaries": 200, "samples_per_unitary": 100, "L_values": [1, 2, 4, 8, 16]},
        systematics=[
            "State-preparation and measurement (SPAM) errors",
            "Finite temperature and residual harmonic confinement",
            "Estimator bias from limited random-unitary ensemble",
        ],
        params={
            "targets": ["d_s", "ell_d"],
            "likelihood": "Student-t on S2(L) with correlated covariance from bootstrap",
            "mapping": "UV cutoff from ell_d modifies short-L entanglement scaling",
        },
        references=["randomized measurements", "entanglement scaling in lattices"],
    ),
    Protocol(
        id="astro.cmb.bispectrum_nonlocal",
        title="CMB: squeezed-limit bispectrum and nonlocal kernel constraints",
        platform="CMB (temperature/polarization)",
        priority=85,
        observables=["B_l1l2l3", "f_NL(k_L,k_S)", "running"],
        estimator="Project bispectrum onto squeezed templates; infer scale-dependent f_NL",
        protocol_steps=[
            "Compute binned bispectrum from cleaned maps (T,E)",
            "Project onto local + nonlocal-running templates",
            "Jointly fit foreground/systematic nuisance parameters",
            "Translate running to causal-set/nonlocal kernel scale parameters",
        ],
        data_requirements={"lmax": 2000, "masks": ["galactic", "point_sources"], "simulations": 500},
        systematics=[
            "Foreground residuals; beam/transfer-function uncertainty",
            "Mode-coupling from masks; anisotropic noise",
        ],
        params={
            "targets": ["kappa_nonlocal", "rho"],
            "likelihood": "Gaussian in bispectrum coefficients with MC-derived covariance",
            "mapping": "nonlocal kernel induces scale-dependent squeezed enhancement/suppression",
        },
        references=["bispectrum estimators", "nonlocal inflationary signatures"],
    ),
    Protocol(
        id="astro.gw.dispersion_phase",
        title="Gravitational waves: dispersion/phase residuals across a population",
        platform="GW interferometers",
        priority=80,
        observables=["waveform phase Psi(f)", "residual delta_Psi(f)", "arrival-time lags"],
        estimator="Hierarchical fit of dispersion parameter controlling delta_Psi(f) ~ f^n",
        protocol_steps=[
            "For each event, sample waveform posterior with extra dispersion term",
            "Aggregate events with hierarchical Bayesian model",
            "Report constraints translated to ell_d and/or spectral dimension running",
        ],
        data_requirements={"events": 50, "fmin_Hz": 20, "fmax_Hz": 1024, "waveform": "IMR"},
        systematics=[
            "Waveform modeling error; calibration uncertainty",
            "Selection effects in detected population",
        ],
        params={
            "targets": ["ell_d", "n_disp"],
            "likelihood": "Population hierarchical Bayes with event-level posteriors",
            "mapping": "ell_d sets high-frequency phase residual scale via modified dispersion",
        },
        references=["parametrized GW tests", "Lorentz-violating dispersion"],
    ),
]
def list_protocols(platform: Optional[str] = None, min_priority: int = 0) -> List[Dict[str, Any]]:
    """Return protocols as dicts, filtered and sorted by descending priority."""
    prots: Iterable[Protocol] = _PROTOCOLS
    if platform:
        p = platform.lower()
        prots = [x for x in prots if p in x.platform.lower()]
    prots = [x for x in prots if x.priority >= min_priority]
    return [x.to_dict() for x in sorted(prots, key=lambda z: z.priority, reverse=True)]


def get_protocol(protocol_id: str) -> Dict[str, Any]:
    """Fetch a protocol by id; raises KeyError if missing."""
    for p in _PROTOCOLS:
        if p.id == protocol_id:
            return p.to_dict()
    raise KeyError(f"Unknown protocol id: {protocol_id}")


def export_protocols_json() -> str:
    """Export the full registry as a JSON string (stable key ordering)."""
    return json_dumps(list_protocols())


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"
