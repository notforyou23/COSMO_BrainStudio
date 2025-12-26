# dgpipe — Discrete-Gravity Pipeline (theory → simulation → measurement → inference)

**Mission:** build an integrated pipeline connecting discrete-gravity microstructure (causal sets, discrete spectra / modified propagators) to *measurable* signatures in (i) analogue quantum platforms and (ii) astrophysical probes. The repository provides: (1) forward models that map microstructure parameters → predicted correlators/entanglement observables, (2) controlled simulations to quantify finite-size + dispersive systematics, and (3) statistical inference to translate measured data into constraints.

## Scientific scope (what this package targets)

**Microstructure knobs (examples):**
- causal-set-inspired nonlocality scale `ℓ` / discreteness density `ρ`, spectral dimension running, or discrete d’Alembertian parameters.
- phenomenological dispersion/propagator modifications (UV regulator, nonlocal kernels, lattice-like spectra).

**Observable classes:**
- **Two-point correlators:** equal-time `G(x,x')`, dynamical structure factor `S(k,ω)`, response/Green’s functions, noise spectra.
- **Higher-point / non-Gaussianity:** connected `⟨φ^4⟩_c` proxies via cumulants of readout fields.
- **Entanglement diagnostics:** Rényi-2 entropy from randomized measurements, mutual information from correlator matrices, logarithmic negativity (Gaussian-state approximations), entanglement growth after quenches.

**Platforms / probes:**
- Analogue: cold atoms/BEC phonons, trapped ions, superconducting circuits, optomechanical arrays.
- Astrophysical: GW dispersion / birefringence tests, photon time-of-flight (with systematics control), cosmology-style correlators when a perturbative route is supplied (e.g., causal-set perturbations to power spectra).

## Prioritized measurement protocols (concrete and action-oriented)

1) **Dynamic structure factor `S(k,ω)` (highest priority):**
- *Measure:* Bragg spectroscopy (cold atoms), cavity transmission (circuits), or motional sidebands (ions).
- *Compare to model:* fits to pole structure / linewidths encode modified dispersion and nonlocal damping.
- *Why robust:* directly targets propagator modifications and is less sensitive to absolute calibration.

2) **Equal-time correlator matrix `C_ij=⟨X_i X_j⟩` + spectrum:**
- *Measure:* spatially resolved snapshots (atoms) or quadrature correlations (circuits).
- *Diagnostics:* eigenvalue flow vs distance; compare to predicted correlator kernel from discrete operators.
- *Why:* enables geometry-agnostic signatures (e.g., altered scaling, spectral gaps).

3) **Rényi-2 entanglement via randomized measurements (mid priority):**
- *Measure:* local random unitaries + projective readout; estimate `Tr(ρ_A^2)` and mutual information.
- *Use:* discriminate UV-modified vacuum structure vs thermal/technical noise using cross-checks below.

4) **Quench-induced correlator/entanglement growth (mid priority):**
- *Measure:* post-quench `C_ij(t)` and entanglement proxy growth rate.
- *Signature:* modified “light cone” / Lieb–Robinson velocity from dispersive microstructure models.

5) **Astrophysical dispersion constraints (complementary):**
- *Measure:* frequency-dependent arrival times / phase lags (GW/photons) with nuisance modeling.
- *Signature:* parameterized dispersion `ω^2=k^2[1+α(k/k_*)^n]` or kernel-induced group delay.

## Systematics plan: controlled simulations (finite-size + dispersion)

**A. Forward-model validation (unit-level):**
- validate discrete operators by recovering continuum limits of `G(k)` and known scalings.
- cross-check: real-space kernel ↔ Fourier-space response consistency.

**B. Finite-size studies (end-to-end):**
- vary system size `N`, boundary conditions, sampling resolution, and measurement window.
- produce scaling curves for bias/variance of extracted parameters (e.g., `α, k_*, ℓ`).

**C. Dispersive + readout systematics:**
- include platform-specific transfer functions (imaging PSF, detector bandwidth, classical noise floors).
- inject controlled dispersion and fit back to quantify identifiability + degeneracies.

**D. Synthetic-data challenge suite:**
- generate “truth” datasets at multiple SNRs with known nuisance parameters.
- require the inference module to recover posteriors with calibrated coverage.

## Statistical inference strategy (data → constraints)

**Model:** `y = f(θ, η) + ε`
- `θ`: discrete-structure parameters (e.g., nonlocality scale `ℓ`, dispersion parameters `α,n,k_*`).
- `η`: nuisance/systematics (temperature, damping, PSF, calibration, background spectra).
- `ε`: measurement noise (Gaussian for averaged spectra; Poisson/binomial for counts where relevant).

**Recommended workflow:**
1. **Likelihoods:** spectral-domain likelihood for `S(k,ω)`; multivariate Gaussian for correlator matrices; entropy estimators with bootstrap uncertainty.
2. **Priors:** weakly informative priors on `θ`; hierarchical priors on nuisance shared across runs.
3. **Sampling:** MCMC (NUTS) when gradients available; otherwise SMC/ensemble + emulator.
4. **Emulation:** train surrogate (GP/NN) on simulation grid for rapid inference; validate on held-out seeds.
5. **Outputs:** posterior on `θ`, Bayes factors for “discrete vs continuum” models, and derived constraints (e.g., bounds on `ℓ` in platform units converted to physical scale).

## Installation

This project is packaged as a standard Python package.
- Create an environment (Python ≥ 3.10 recommended).
- Install editable for development:
```bash
pip install -e .
```

## CLI usage (typical end-to-end runs)

The package exposes a CLI entrypoint (defined in `pyproject.toml`). Typical commands follow:
```bash
# 1) simulate correlator/structure-factor datasets under a microstructure model
dgpipe simulate --config configs/sim.yaml --out runs/sim_001/

# 2) compute derived observables (correlators → S(k,ω), entanglement proxies, etc.)
dgpipe analyze --in runs/sim_001/ --out runs/ana_001/

# 3) perform inference (posterior on θ with nuisance marginalization)
dgpipe infer --data runs/ana_001/observables.json --model cset_nonkernel --out runs/inf_001/
```
All commands are designed to be deterministic given a `--seed` and to save a machine-readable record of parameters.

## Data-model conventions (interchange format)

Artifacts are written as directories containing:
- `metadata.json`: version, git SHA (if available), seed, platform/probe tag, and units.
- `observables.json`: canonical schema for spectra/correlators/entropy estimates.
- `samples.csv` or `posterior.npz`: inference outputs (samples + summary stats).
- `plots/` (optional): diagnostic figures (not required for inference).

**Units:** store both “native platform units” and a `unit_map` for conversion to physical units where applicable.

## CI/CD notes

GitHub Actions workflows (`.github/workflows/ci.yml`, `cd.yml`) run lint/tests and build versioned artifacts on tags. The CLI is smoke-tested in CI to ensure the full pipeline (simulate→analyze→infer) executes on a minimal example.

## Citation / scientific attribution

If you use this pipeline to produce constraints on discrete microstructure, cite the platform/probe datasets you analyze and the discrete-operator/propagator models you adopt (e.g., causal-set d’Alembertian/nonlocal kernels; perturbative cosmology-style routes where used).
