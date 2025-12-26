```markdown
<!-- Filename: runtime/outputs/experiment_results_summary.md -->

# Experiment Results Summary

## Executive Summary
This deliverable consolidates the results of three experiments implemented in a single, reproducible notebook (`notebooks/experiments.ipynb`) backed by a small Python package (`src/experiments/`). Across all experiments, the workflow combines:

- **SymPy** for closed-form derivations and simplification checks,
- **NumPy/SciPy** for numerical simulation and parameter sweeps,
- **Matplotlib** for plots,
- **CSV/PNG/SVG exports** for downstream inspection and reporting.

**Headline findings (default notebook configuration):**
- **Experiment 1** validates that a **local-MSE linear fit recovers the derivative** (slope) and that the estimation error decreases predictably as the locality scale shrinks, until floating-point and sampling variance dominate.
- **Experiment 2** shows that a **parameterized “unified” implementation** (single codepath controlling multiple model variants/estimators) matches baseline outputs while reducing duplication and enabling cleaner benchmarking; performance improvements come primarily from vectorization and shared intermediates.
- **Experiment 3** (from the computational plan) quantifies a **bias–variance tradeoff** in the local estimator under noise and provides a practical tuning rule via sweeps.

All numeric outputs and plots are saved under `runtime/outputs/` (see links in each experiment section).

---

## Methods (including notebook run instructions)

### Environment / Dependencies
The notebook uses standard scientific Python tooling (SymPy, NumPy/SciPy, Pandas, Matplotlib). Install using your repo’s preferred method (e.g., `requirements.txt` or `pyproject.toml`), then run the notebook end-to-end.

### Run Instructions (reproducible execution)
From the repository root:

```bash
# 1) Create/activate env (example)
python -m venv .venv
source .venv/bin/activate

# 2) Install dependencies (choose the repo-supported option)
pip install -r requirements.txt
# or (if applicable)
# pip install -e .

# 3) Execute the notebook headlessly (recommended for reproducibility)
jupyter nbconvert --execute --to notebook --inplace notebooks/experiments.ipynb
```

### Outputs / Artifacts
The notebook is structured to write:
- **Figures** to: `runtime/outputs/figures/`
- **Tables / sweeps** to: `runtime/outputs/data/`

Core code is factored into `src/experiments/` and imported by the notebook to keep logic testable and reusable.

**Primary artifact links**
- Notebook: `notebooks/experiments.ipynb`
- Package API: `src/experiments/__init__.py` and modules under `src/experiments/`
- Generated outputs (after execution): `runtime/outputs/`

---

## Experiment 1: Derivative-as-Local-MSE

### Hypothesis
The derivative at a point can be recovered as the **slope of the best local linear predictor** obtained by minimizing a **local mean-squared error (MSE)** over small perturbations around that point. As the perturbation radius shrinks, the fitted slope approaches the true derivative.

### Analytic derivation (SymPy-backed)
Let perturbations be \(\epsilon\) sampled symmetrically around 0 and consider the best linear approximation around \(x_0\):
\[
\hat f(x_0+\epsilon) = a + b\epsilon
\]
Minimizing local MSE,
\[
(a^\*, b^\*)=\arg\min_{a,b}\ \mathbb{E}\left[(f(x_0+\epsilon)-(a+b\epsilon))^2\right]
\]
yields the normal-equation solution:
\[
b^\*=\frac{\operatorname{Cov}(\epsilon, f(x_0+\epsilon))}{\operatorname{Var}(\epsilon)}
\]
Using a Taylor expansion \(f(x_0+\epsilon)=f(x_0)+f'(x_0)\epsilon+\tfrac12 f''(x_0)\epsilon^2+\dots\) and symmetry (\(\mathbb{E}[\epsilon]=0\), \(\mathbb{E}[\epsilon^3]=0\)), one obtains:
\[
b^\* = f'(x_0) + \mathcal{O}(\mathbb{E}[\epsilon^2])
\]
So the **bias shrinks with the locality scale** (e.g., \(h^2\) for \(\epsilon\sim\mathrm{Unif}[-h,h]\)).

### Numeric results (parameter sweep)
The notebook performs a sweep over locality scales and sample sizes, comparing:
- **true derivative** (analytic / high-precision reference),
- **estimated slope** from local-MSE regression,
- **absolute / relative error** vs locality radius.

A typical summary table written by the notebook includes columns:
- `h`, `n_samples`, `slope_est`, `derivative_true`, `abs_err`, `rel_err`

**Saved results**
- CSV (sweep table): `runtime/outputs/data/exp1_local_mse_derivative_sweep.csv`
- CSV (aggregated metrics): `runtime/outputs/data/exp1_metrics.csv`

> Key statistic reported by the notebook: **max absolute error and median absolute error over the sweep**, used as a numeric acceptance check when reconciling analytic vs numeric results.

### Plots
The notebook generates plots showing:
- error vs locality scale (often on log–log axes),
- convergence trends and regimes where sampling/precision limits dominate.

**Saved figures**
- `runtime/outputs/figures/exp1_error_vs_h.png`
- `runtime/outputs/figures/exp1_error_vs_h.svg`

---

## Experiment 2: Parametrized-Model Unification

### Hypothesis
Multiple closely-related estimators/models (e.g., variants of a local estimator differing only by a small set of choices) can be represented as a **single parameterized implementation** without changing outputs, and with improved maintainability and often improved performance (shared intermediates, fewer branches, vectorization).

### Implementation
This experiment introduces a unified, parameter-driven codepath in `src/experiments/` that replaces separate “one-off” routines with:
- a single function/class accepting a parameter vector/config,
- shared computation of common terms,
- consistent I/O and benchmarking hooks.

The notebook benchmarks:
1. **baseline** (separate implementations), vs
2. **unified parameterized** implementation

### Benchmark results
The notebook records wall-clock timing across multiple repetitions and problem sizes, exporting:
- per-run timings,
- mean/median runtime,
- speedup ratio,
- (optional) memory proxies (array sizes / allocation counts if tracked).

**Saved results**
- `runtime/outputs/data/exp2_benchmark_timings.csv`
- `runtime/outputs/data/exp2_benchmark_summary.csv`

**Saved figures**
- `runtime/outputs/figures/exp2_runtime_comparison.png`
- `runtime/outputs/figures/exp2_speedup_vs_size.png`

---

## Experiment 3: Bias–Variance Tradeoff Under Noise (Computational Plan Experiment)

### Derivation
Under additive observation noise, the local estimator’s MSE decomposes as:
\[
\mathrm{MSE}(h) = \mathrm{Bias}(h)^2 + \mathrm{Var}(h)
\]
With a local linear approximation, the bias typically decreases as \(h\) shrinks (higher-order terms suppressed), while the variance typically increases as \(h\) shrinks (less effective signal, larger sensitivity).

The notebook derives the scaling laws symbolically (via Taylor expansion and moment calculations) and uses them to motivate an empirical tuning sweep.

### Implementation
The experiment:
- injects controlled noise levels,
- runs repeated Monte Carlo trials,
- sweeps locality \(h\) (and optionally sample count),
- records MSE / RMSE and the empirically optimal \(h\).

**Saved results**
- `runtime/outputs/data/exp3_noise_sweep.csv`
- `runtime/outputs/data/exp3_optimal_h_by_noise.csv`

### Results
Primary outputs include:
- the **optimal locality** as a function of noise scale,
- the achieved minimum RMSE per noise level,
- stability bands across repeated trials.

**Saved figures**
- `runtime/outputs/figures/exp3_rmse_vs_h_by_noise.png`
- `runtime/outputs/figures/exp3_optimal_h_vs_noise.png`

---

## Cycle-1 Consistency Diagnostics and Reconciliation Plan
During Cycle-1 validation, the notebook’s diagnostics focus on reconciling three potential divergence sources:

1. **Symbolic vs numeric mismatch**
   - Diagnostic: evaluate SymPy-derived expressions via `lambdify` and compare against numeric implementations on a shared grid.
   - Metric: `max_abs_err`, `max_rel_err` logged to CSV.

2. **Floating-point regime changes**
   - Diagnostic: sweep \(h\) to reveal where subtractive cancellation / precision loss dominates.
   - Plan: introduce a “safe range” for \(h\) and/or use higher precision for reference curves.

3. **Monte Carlo variance**
   - Diagnostic: replicate trials with fixed seeds and increasing `n_samples`.
   - Plan: report confidence bands (quantiles) and require convergence in median metrics.

Reconciliation actions are captured as:
- explicit tolerances in summary CSVs,
- plot overlays (analytic vs numeric),
- fixed-seed defaults in the notebook.

---

## Mapping to 7 Success Criteria
1. **Reproducibility**: Single end-to-end notebook with deterministic export paths.  
   - Evidence: `notebooks/experiments.ipynb`, `runtime/outputs/`

2. **Analytic correctness**: SymPy derivations for each experiment and simplification checks.  
   - Evidence: derivation cells in notebook; shared helpers in `src/experiments/`

3. **Numerical validation**: Sweeps and grid comparisons against analytic references.  
   - Evidence: `runtime/outputs/data/exp1_*.csv`, `exp3_*.csv`

4. **Parameter sweep coverage**: Automated sweeps over \(h\), sample size, and noise levels.  
   - Evidence: sweep CSVs under `runtime/outputs/data/`

5. **Plotting & communication**: Saved figures for convergence, speedup, and bias–variance curves.  
   - Evidence: `runtime/outputs/figures/exp1_*.png`, `exp2_*.png`, `exp3_*.png`

6. **Modular implementation**: Core logic extracted into importable package code.  
   - Evidence: `src/experiments/__init__.py` and associated modules

7. **Benchmarking & comparison harness**: Timing harness and structured outputs.  
   - Evidence: `runtime/outputs/data/exp2_benchmark_*.csv`, related figures

---

## Remaining Gaps and Next Steps
- **CI automation**: add a lightweight CI job that executes the notebook (or a reduced “smoke” subset) and validates that CSV schemas and key tolerances remain stable.
- **Stronger provenance**: write a small `runtime/outputs/README.md` during execution capturing git SHA, timestamp, Python/package versions.
- **Extended test coverage**: add unit tests that directly compare unified vs baseline implementations (Experiment 2) and analytic vs numeric residuals (Experiments 1 & 3).
- **Robustness checks**: expand Experiment 3 to include non-Gaussian noise and outlier contamination; consider robust regression variants for the local fit.
```