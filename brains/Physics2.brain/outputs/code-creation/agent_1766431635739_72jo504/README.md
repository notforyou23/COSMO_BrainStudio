# sf_gft_diagnostics — Continuum-recovery diagnostics for Spin-Foams / GFT RG

This project specifies a *focused* set of continuum-recovery diagnostics and cross-validation tests for renormalization studies in spin-foam models and Group Field Theory (GFT), designed to be mutually comparable across:
- tensor-network / lattice RG (coarse-graining flows, fixed points, scaling),
- GFT FRG / effective field theory flows (beta functions, universality),
- semiclassical / effective-geometry benchmarks (Regge/continuum limits).

The emphasis is on **operational observables**, **scaling quantities**, and **metrics** that can be computed from either (i) ensembles of discrete geometries/spin-network/spin-foam data, (ii) coarse-graining maps (isometries, tensors), or (iii) effective distributions over geometric variables.

## Conceptual design goals

1. **Continuum recovery diagnostics**
   - detect approach to scale-invariant regimes (fixed points / plateaus in effective exponents),
   - test emergence of smooth geometry (spectral/Hausdorff dimension, curvature distributions),
   - quantify suppression of lattice/discretization artifacts.

2. **Cross-validation**
   - compare RG trajectories from different schemes (tensor networks vs. FRG truncations),
   - compare discrete observables to semiclassical expectations (Regge/EH scaling, heat-kernel),
   - provide distances/consistency scores on *distributions* and *flows*.

3. **Numerical practicality**
   - estimators defined for finite samples and finite volume,
   - bootstrap/jackknife uncertainty and finite-size scaling (FSS) utilities,
   - data schemas that allow mixing inputs from different pipelines.

## Prioritized candidate observables (with intended estimators)

Priority is ordered by (a) broad applicability, (b) discriminating power for phases, (c) numerical tractability.

### A. Universal / near-universal continuum diagnostics
1. **Spectral dimension** `d_s(σ)` from diffusion/heat-kernel return probability:
   - estimate `P(σ)=⟨K(x,x;σ)⟩` (random walks on dual 2-complex / adjacency graph),
   - `d_s(σ) = -2 d log P(σ) / d log σ`; look for plateaus indicating effective dimension.
2. **Hausdorff / volume-growth dimension** `d_H(R)`:
   - ball volume `V(R)` vs geodesic distance `R` on combinatorial/weighted graphs,
   - `d_H(R)= d log V(R)/d log R` with plateau tests.
3. **Two-point correlation length** `ξ` (where definable):
   - from connected correlators of geometric operators (e.g., area/volume, group fields),
   - used for FSS and universal ratios (Binder-like cumulants).
4. **Entanglement scaling across coarse-graining cuts** (tensor networks / boundary states):
   - Renyi entropies `S_n` vs boundary size; extract central-charge-like scaling in 2D cases
     or area-law deviations; compare across RG steps.

### B. Geometry-specific semiclassical checks
5. **Curvature / deficit-angle statistics** (Regge-like):
   - distribution of deficits, mean/variance, scaling with refinement.
6. **Effective Einstein–Hilbert scaling surrogate**
   - regression of effective action density against `(R, Λ)` proxies extracted from observables,
   - compare sign/flow trends (not absolute normalization).
7. **Volume/area spectra moments**
   - moments and tail behavior of spin/representation distributions (`⟨j⟩, ⟨j^2⟩`, Gini),
   - check universality under coarse graining and relation to effective length scale.

### C. RG-flow and fixed-point indicators (scheme-comparable)
8. **Step-scaling function** `Σ(g; s)` for chosen couplings/observables:
   - compare discrete RG map vs FRG beta-function integration.
9. **Relevant/irrelevant directions from linearized flow**
   - eigenvalues of stability matrix (when couplings are defined) or data-driven Jacobians.
10. **C-theorem / monotone candidates** (model-dependent):
   - e.g., entropy-like monotones, complexity measures; used as sanity checks.

## Scaling quantities and cross-checks

- **Effective exponents** from local log-derivatives:
  - `ν_eff(L)`, `η_eff(L)`, `d_s,eff(σ)`, etc., with plateau detection.
- **Finite-size scaling collapse**
  - fit `O(L,t) = L^{y_O} f(t L^{1/ν})` with bootstrap uncertainty.
- **Hyperscaling consistency**
  - check relations among exponents and dimension estimates (e.g., `2β/ν + γ/ν = d_eff`).
- **Universality tests**
  - compare dimension plateaus, exponent ratios, and distribution shapes across schemes.

## Mutually comparable metrics (distributions, curves, and flows)

The metrics are chosen to compare outputs from heterogeneous pipelines.

### Distribution distances (histograms / samples)
- **Jensen–Shannon distance (JSD)**: symmetric, finite; robust for sparse histograms.
- **Wasserstein-1 (Earth mover)**: compares geometry/scale distributions with meaningful order.
- **Energy distance / MMD (kernel)**: works on samples without binning; choose kernels on spins,
  group variables, or geometric invariants.
- **KL-surrogates**: use JSD or cross-entropy with pseudocounts when KL diverges.

### Trajectory / curve distances (RG flows vs RG flows)
- **Dynamic time warping (DTW)** on sequences of observables across RG steps.
- **Fréchet / Hausdorff distances** between parametric curves in observable space.
- **Angle and norm tests** for beta-function vectors (when couplings are defined):
  cosine similarity, integrated squared deviation.

### Semiclassical consistency scores
- **Chi-square / likelihood ratio** against semiclassical predictions with propagated errors.
- **Scale-window agreement**: overlap of plateau intervals for `d_s`/`d_H` across runs.

## Data format expectations (minimal JSON lines)

Inputs may be aggregated as JSONL records, one per configuration or RG step.

Required fields (recommended):
- `run_id`: string
- `scheme`: e.g. `"TN"`, `"lattice_RG"`, `"FRG"`
- `scale`: numeric (lattice spacing proxy, RG step index, or diffusion time `σ`)
- `observables`: dict of scalar values (e.g., `{"P_sigma": ..., "V_R": ...}`)
- `samples`: optional dict of arrays (e.g., spins, deficits); store as lists
- `meta`: optional dict (model parameters, truncation, bond dimension, etc.)

Example JSONL record:
```json
{"run_id":"r1","scheme":"TN","scale":4,"observables":{"P_sigma":0.0123,"V_R":120},"meta":{"D":32}}
```

## Numerical prototype: how to run

The package is structured for a small prototype pipeline:
- `sf_gft_diagnostics.observables`: estimator specs + canonical names/units
- `sf_gft_diagnostics.scaling`: exponent extraction, FSS collapse, bootstrap tools
- `sf_gft_diagnostics.metrics`: distances for distributions and RG trajectories

Typical workflow (once `src/` is present):
1. Load JSONL/CSV into a pandas DataFrame.
2. Compute estimators (e.g., `d_s(σ)`, plateau windows, `ξ`).
3. Run scaling analysis (effective exponents, collapses).
4. Compare schemes with distribution/trajectory metrics.
5. Export a compact report: best-fit exponents, plateau ranges, distances.

If you have a local checkout with `src/` installed:
```bash
python -m pip install -e .
python -c "import sf_gft_diagnostics as d; print(d.__all__)"
```

## Benchmark comparisons (recommended)

1. **Known lattice models** (sanity): Ising/O(N) on graphs → verify exponent extraction and FSS.
2. **Toy spin-foam / random complex ensembles**: reproduce expected `d_s` plateaus (e.g. ~2 in 2D).
3. **FRG truncation vs TN coarse-graining**: compare step-scaling and trajectory distances on
   matched coupling proxies (mass term, interaction strength, wavefunction renorm surrogate).
4. **Semiclassical regime**: compare curvature-statistics scaling to Regge-like expectations and
   check that continuum dimension estimators stabilize with refinement.

License: MIT (intended).
