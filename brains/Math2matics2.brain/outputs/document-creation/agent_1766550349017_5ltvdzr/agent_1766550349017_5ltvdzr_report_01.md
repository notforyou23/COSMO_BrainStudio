## /outputs/src/run_experiment.py — deterministic seeding + fixed output schema (implementation plan)

This change has two concrete goals:

1) **Deterministically control all variability** (random seeds and plotting settings) so repeated runs produce the same artifacts.  
2) **Enforce a single, canonical “results contract”** (a fixed output schema) so downstream tooling and CI can validate outputs against baselines.

These are directly aligned with the consolidated findings that reliable, reproducible outputs come from (a) explicitly specifying and versioning the expected results contract (schema) and (b) deterministically controlling variability, then enforcing both through code and automated verification.

### A. Add one unified RNG seed and propagate it everywhere

**What to implement in `run_experiment.py`:**

- Accept a single seed value (CLI arg or config input) and treat it as the *one propagated RNG seed* for the entire run.
- Set all relevant seeds at the start of the run, before any computation or plotting.

**Determinism enforcement actions (code-level):**
- Create a `seed_everything(seed: int)` function and call it once, at the top of the entrypoint.
- Inside `seed_everything`:
  - Seed Python’s `random` module.
  - Seed NumPy RNG (if NumPy is used anywhere in the experiment).
  - If the experiment uses any other RNG surface, route it through the same seed (the reliability finding emphasizes *one unified configuration surface* and *one propagated RNG seed*).

**Why this is required (grounded in research):**
- Reliable automation depends on “a unified configuration surface (one output-directory utility and one propagated RNG seed) so the pipeline produces byte-identical, reproducible artifacts across runs and environments.”
- Reliability in experimentation systems comes from making each run “deterministic and self-describing,” continuously verifying reproducible artifacts (results files and plots) against baselines.

### B. Deterministic plotting settings (so plot artifacts are reproducible)

**What to implement in `run_experiment.py`:**
- Set plotting settings deterministically before any figure creation:
  - Fix figure size, DPI, font settings, and any style parameters that could vary.
  - Ensure plots are generated from deterministically ordered data (e.g., sort keys before iterating).

**Why this is required (grounded in research):**
- The consolidated finding explicitly calls out “random seeds and plotting settings” as sources of variability that must be deterministically controlled to make outputs reliable and reproducible.

### C. Enforce a fixed output schema (a versioned “output contract”)

**What to implement in `run_experiment.py`:**
- Write results to a **single canonical path** under the output directory (one output-directory utility; fixed paths).
- Emit a **single JSON (or similarly structured) results file** whose keys are stable and documented.
- Include a **schema version field** and enforce presence of required fields before writing.

**Required properties of the output contract (based on the consolidated research):**
- **Explicit**: fields are named, stable, and documented.
- **Versioned**: schema version included in the artifact, enabling controlled evolution.
- **Deterministic**: the contents should be stable for the same inputs and seed (and plotting settings).
- **Enforceable**: code validates required fields and types before writing, and CI/tests can compare against baselines.

**Practical enforcement steps in code:**
- Define a `RESULTS_SCHEMA_VERSION = "1"` constant in `run_experiment.py`.
- Build a `results: dict` with only stable, documented fields (see README section below).
- Validate:
  - All required keys exist.
  - Values are JSON-serializable.
- Serialize deterministically:
  - Use stable key ordering when writing JSON (e.g., `sort_keys=True`).
  - Use consistent numeric formatting where applicable (avoid nondeterministic float repr drift by standardizing formatting if needed).

### D. Make the run self-describing (but keep “stable fields” separate from “metadata”)

The reliability findings emphasize “deterministic and self-describing.” That does **not** mean every field is stable across runs; it means the artifact contains enough information to audit and reproduce the run.

So implement two categories:

1) **Stable fields**: expected to be identical across runs given same inputs + seed.
2) **Run metadata**: useful for audit, but not expected to be byte-identical (timestamps, host info). If included, keep it clearly separated so tests can ignore it.

---

## /outputs/README.md — document stable fields + how determinism is enforced

Update `/outputs/README.md` to explicitly define:

1) The **expected results contract** (schema), including a schema version.
2) Which fields are **stable** (deterministic) vs **non-stable metadata**.
3) The exact mechanisms used to enforce determinism (seed + plotting settings + fixed paths).

Below is content to add (or adapt) into `/outputs/README.md`, written as a concrete “results contract.”

---

# Outputs: deterministic experiment artifacts and fixed schema

This project enforces reproducible experimentation by combining:

- A **versioned, explicit output schema** (“output contract”) for results.
- **Deterministic control of variability** (a single propagated RNG seed plus deterministic plotting settings).
- A **single canonical output path** so tools and CI can locate and validate artifacts consistently.

These choices follow the consolidated findings that reliable, reproducible outputs require explicitly specifying and versioning the expected results contract (schema) and deterministically controlling variability (random seeds and plotting settings), then enforcing both through code and automated validation.

## 1) Canonical output paths (fixed)

All run artifacts are written under the configured output directory using fixed, documented filenames. This supports artifact-based validation (including baseline comparisons in CI) because paths do not drift across runs.

## 2) Results schema (“output contract”)

### 2.1 Schema version
Every results file contains a schema version:

- `schema_version` (string): version identifier for this results contract.

### 2.2 Required top-level fields (stable)
The following fields are part of the stable contract: for the same code, same configuration, same input data, same seed, and same plotting settings, these fields are expected to be identical across runs.

- `schema_version` (string)  
- `seed` (integer): the single propagated RNG seed used for the entire run.
- `metrics` (object): summary numeric outputs produced by the experiment.  
  - Contents must be deterministic given inputs and `seed`.
- `artifacts` (object): references (paths/names) to generated artifacts (e.g., plots).  
  - Paths are fixed and canonical (not run-id dependent).

**Stability expectation:** these fields are the basis for reproducibility checks and baseline comparisons.

### 2.3 Optional run metadata (not stable)
Some information can be included for auditability, but is **not expected to be stable** (and should not be used for “byte-identical artifact” assertions):

- `run_metadata` (object), e.g.:
  - wall-clock timestamps
  - machine/environment identifiers

This preserves the “self-describing” requirement (auditability) without weakening determinism guarantees for stable outputs.

## 3) How determinism is enforced

Determinism is enforced by controlling all known variability at the start of the run and by standardizing artifact generation.

### 3.1 Single propagated RNG seed
Each run uses one seed value, and that value is applied to all randomness surfaces used by the experiment. This follows the consolidated reliability finding that a unified configuration surface with one propagated RNG seed is required to make the pipeline produce reproducible artifacts across runs and environments.

### 3.2 Deterministic plotting settings
Plots are generated with fixed plotting parameters (style/size/DPI and any other settings that can introduce drift). This directly addresses the consolidated finding that reproducible outputs require deterministic control of both random seeds and plotting settings.

### 3.3 Fixed output schema + fixed paths
The experiment writes a results file conforming to the schema above (including `schema_version`) to canonical paths. This implements the “explicit, versioned output contract” requirement and enables artifact-based validation (results files and plots) against baselines.

## 4) Reproducibility expectations and verification

The intent is that repeated runs with the same inputs and `seed` produce:
- The same stable results fields.
- The same artifact references/paths.
- Reproducible artifacts suitable for baseline comparison.

This matches the consolidated recommendation that reproducible systems continuously verify results files and plots against baselines in CI, treating the workflow as a deterministic, versioned, end-to-end pipeline with a clear output contract.

---

## Conclusion

To implement deterministic seeding and a fixed output schema in `/outputs/src/run_experiment.py`, the core requirements are:

- **One propagated RNG seed**, applied once at run start to eliminate uncontrolled randomness.
- **Deterministic plotting settings**, since plots are a documented source of output variability.
- A **versioned, explicit output contract** with stable fields, written to **canonical paths**, so results are both reproducible and enforceable through automated baseline validation.

The `/outputs/README.md` update should formally document the schema (including which fields are stable), and precisely state how determinism is enforced (seed propagation + plotting determinism + fixed schema/paths). This directly instantiates the consolidated research findings that reliability comes from deterministic, self-describing runs with a versioned output contract, enforced end-to-end through code and artifact-based checks.