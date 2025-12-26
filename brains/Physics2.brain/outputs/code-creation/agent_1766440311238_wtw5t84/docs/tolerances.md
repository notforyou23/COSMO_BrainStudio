# Tolerance policy (v0.1 benchmarks)

This project uses **centralized comparison utilities** to decide whether a candidate run matches the reference run.
Every v0.1 task must declare **per-observable tolerance choices** in its benchmark contract; CI enforces that contract.

## Core concepts

### Observables and paths
An *observable* is any value produced by a benchmark that is compared (e.g., `metrics.rmse`, `state.positions`, `summary.score`).
Observables are addressed by a stable **path** (dot / index notation) and compared independently, each with its own tolerance spec.

### Absolute vs relative tolerance
Numeric comparisons use both:
- **Absolute tolerance** `atol`: allowed absolute error.
- **Relative tolerance** `rtol`: allowed error relative to the reference magnitude.

A value `x` (candidate) is considered equal to `y` (reference) when:

`|x - y| <= atol + rtol * |y|`

Notes:
- Use `atol` for small-magnitude values where relative error is unstable.
- Use `rtol` for scale-proportional error where values vary in magnitude.

### Defaults and overrides
Policy:
- Each observable must explicitly declare `atol` and `rtol` (no silent global defaults in CI).
- Nested/structured observables may provide **per-field overrides** (e.g., `state.positions.atol` differs from `state.velocities.atol`).
- Non-numeric types (strings, booleans, enums) use **exact equality** unless the observable is explicitly excluded from comparison.

## Type/shape and structural rules

Before applying tolerances, comparisons enforce:
- **Type compatibility**: numeric vs non-numeric mismatches fail (except where the contract defines coercion; v0.1 assumes no coercion).
- **Shape equality** for arrays/tensors (rank and dimensions must match).
- **Key-set equality** for mappings/dicts (unless the contract declares an allowlist/ignorelist for keys).

These structural checks produce deterministic, CI-friendly mismatch messages (first mismatch path + a short diff summary).

## NaN/Inf handling

Floating-point special values are handled explicitly per observable via a `nan_policy` field:

- `nan_policy: "forbid"` (recommended default)
  - Any NaN in either candidate or reference fails the comparison.
- `nan_policy: "allow_equal"`
  - NaN is allowed **only if both** candidate and reference are NaN at the same positions.
- `nan_policy: "allow_any"`
  - NaNs are ignored for that observable (use sparingly; must be justified).

Infinity handling:
- `+inf` and `-inf` are treated as valid numeric values, but must match exactly in sign and location.
- A finite number never matches an infinity, regardless of tolerances.

## Choosing tolerances (how to justify)

Tolerances should be **tight enough to catch regressions** and **loose enough to be stable** across platforms, BLAS/LAPACK variants, and minor nondeterminism.

Recommended workflow:
1. Run the reference algorithm across representative seeds/inputs and record typical numeric variability.
2. Identify the observable’s scale (units/range). Prefer `rtol` when scale varies; prefer `atol` when values can be near zero.
3. Set tolerances slightly above observed variability (e.g., 2–10× the maximum observed deviation), then re-run in CI.
4. If tolerances must be large, add a note explaining *why* (stochasticity, ill-conditioning, chaotic dynamics, GPU nondeterminism, etc.).
5. Prefer tightening tolerances on **aggregate metrics** (scores, losses) and allowing slightly larger tolerances on **raw intermediate fields** (states, gradients).

Anti-patterns:
- Using `allow_any` to “make tests pass” without a domain reason.
- Setting huge `atol`/`rtol` without stating expected range/units.
- Relying on a single global tolerance for all outputs.

## Per-observable tolerance table (to include in each task’s docs)

Use a table like the following in each v0.1 task’s documentation (or in the contract’s `tolerances` section), and keep it updated when observables change.

| Observable path | Type / shape | Units / scale | Expected range | atol | rtol | nan_policy | Rationale / notes |
|---|---|---:|---:|---:|---:|---|---|
| `metrics.rmse` | float | same as target | ~1e-3–1e0 | 1e-6 | 1e-4 | forbid | Deterministic metric; small platform drift only. |
| `state.positions` | array (N,3) | meters | ~1e-2–1e2 | 1e-7 | 1e-5 | forbid | ODE solver differences; compare per-element. |
| `debug.intermediate` | array (...) | n/a | n/a | 0.0 | 0.0 | allow_equal | NaNs represent masked regions; must match exactly. |

Interpretation:
- “Expected range” should reflect typical magnitudes; it anchors whether `atol`/`rtol` are sensible.
- If an observable is stochastic, document the seed control strategy; prefer comparing *statistics* (mean/quantiles) over raw samples.

## CI enforcement expectations

CI will fail a benchmark when:
- A task omits tolerance specs for an observable that is compared.
- Any observable violates its declared tolerance or special-value policy.
- The output structure changes (missing/extra keys, shape mismatch) unless the contract explicitly permits it.

This ensures tolerance choices are reviewed, traceable, and consistent across tasks.
