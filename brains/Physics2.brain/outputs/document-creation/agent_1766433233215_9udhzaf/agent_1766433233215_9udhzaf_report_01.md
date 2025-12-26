Below are the complete contents for the two files you asked for—**`benchmarks_v0_1.md`** and **`schema.json`**—defined using **only** the facts/themes present in the provided COSMO memory (2019–2025): operational/testable foundations; decoherence/noise spectroscopy with a gravity-sensitive residual channel; RG/coarse-graining as a cross-program thread (notably special-issue framing circa 2021, e.g. arXiv:2103.14605); causal-set push toward QFT observables (entanglement entropy, in-in correlators/scattering); analogue-gravity (BEC) Hawking-like emission/correlations with explicit attention to robustness/systematics/backreaction; and spin-foam/LQG’s shift toward continuum recovery via background-independent renormalization/coarse-graining and diagnosing restoration of effective diffeomorphism symmetry.

No detailed formulas, beta functions, or community-specific normalizations are assumed (explicitly noted as out-of-scope in the translation guide memory).

---

## `benchmarks_v0_1.md`

```markdown
# COSMO Benchmarks v0.1 (2019–2025 research-grounded)

This benchmark spec turns COSMO’s 2019–2025 accumulated themes into *machine-checkable* observables with explicit tolerances, required metadata, and explicit failure modes.

Grounding constraints from the knowledge base used here:
- **Operational/testable frameworks** are prioritized in foundations work (incl. causal modeling and indefinite causal order).
- **Noise spectroscopy + dynamical decoupling** style analysis is used to characterize decoherence/noise, including a **gravity-sensitive residual channel** (described as scaling with gravitational potential differences).
- **RG / coarse-graining** is explicitly framed (notably in 2021 cross-approach special-issue/editorial mappings, e.g. arXiv:2103.14605) as a *unifying thread* across quantum-gravity programs linking microscopic models to emergent semiclassical behavior/phenomenology.
- **Causal sets** have pushed toward predictive, QFT-like observables: **entanglement entropy** and **in-in correlators/scattering**.
- **Analogue gravity (BEC)** emphasizes Hawking-like emission and correlation signals *plus* robustness checks: systematics and backreaction.
- **Spin-foam LQG (2018–2025)** shifts from kinematics toward continuum recovery via **background-independent renormalization/coarse-graining**, including tensor-network-inspired methods to diagnose continuum limits and **restoration of effective diffeomorphism symmetry**.

Important limitation (from translation-layer memory):
- Detailed formulas, explicit beta functions, and canonical numeric values for exponents/coefficients are not provided in the knowledge base and are therefore not assumed. Benchmarks are designed around *internal consistency*, cross-checks, metadata completeness, and robustness/systematics structure.

---

## 0) Common output conventions (v0.1)

All benchmark outputs MUST be JSON objects with:

- `benchmark_id` (string; one of the IDs below)
- `version` (string; MUST equal `"0.1"`)
- `run_id` (string; user-provided unique run label)
- `metadata` (object; required, shared fields)
- `inputs` (object; benchmark-specific)
- `results` (object; benchmark-specific)
- `checks` (array of objects `{check_id, passed, details}`)
- `failure_modes` (array of objects; required even if empty)
- `notes` (string; optional)

### 0.1 Shared required metadata (ALL benchmarks)

The following metadata fields are required for every benchmark because COSMO’s accumulated knowledge emphasizes that conclusions depend on coarse-graining/RG choices, truncations, and regulators (cross-program RG thread; spin-foam coarse-graining/continuum recovery; robustness/systematics in analogue gravity).

Required fields:
- `program_context` (string; e.g., `"analogue_gravity_BEC"`, `"causal_set_QFT"`, `"spin_foam_LQG"`, `"foundations_noise_spectroscopy"`, or other user-specified)
- `rg_scheme` (string; REQUIRED even if `"none"`; because RG/coarse-graining is a cross-cutting thread)
- `coarse_graining_description` (string; what degrees of freedom were integrated/blocked/aggregated)
- `truncation` (string; REQUIRED even if `"none"`; explicit about what was retained/dropped)
- `regulator` (string; REQUIRED even if `"none"`; explicit about the regulator choice where applicable)
- `numerics` (object with at least `method` string and `tolerances` object; can be `"analytic"` if no numerics)
- `data_provenance` (object; includes `source_type` string such as `"simulation"`, `"experiment"`, `"derived"`, and `source_ref` string)

Additionally required:
- `timestamp_utc` (string; ISO-8601)
- `code_version` (string; commit hash or equivalent)
- `random_seed` (integer OR null; required field even if null)

### 0.2 Pass/fail rule

A benchmark PASSES iff:
1) The JSON validates against `schema.json`.
2) Every check in `checks` has `passed: true`.

---

## 1) Observable Benchmark: RG/Coarse-graining Scaling Collapse Proxy (internal consistency)

### 1.1 Why this is in-scope (memory grounding)
- COSMO notes that **RG/coarse-graining** is a cross-program technical thread (explicitly highlighted in 2021 cross-approach framing, e.g. arXiv:2103.14605) aimed at relating micro models to emergent semiclassical behavior.
- Spin-foam LQG (2018–2025) specifically emphasizes **background-independent renormalization/coarse-graining** as a route to continuum recovery.

Because shared, numeric critical exponents are *not* provided, this benchmark enforces a **data-collapse consistency test** rather than “match known exponent X”.

### 1.2 Observable definition
Given a set of runs at different coarse-graining levels or scales, the user provides:
- raw curves `O_i(x)` each tagged by a scale label `s_i` (e.g., block size, RG step count, or another monotone scale proxy),
- a chosen rescaling ansatz (user-specified; recorded),
- and the *collapsed* curves `Ō_i(u)` on a common domain `u`.

The benchmark computes **collapse error**: a normalized RMS dispersion across curves on the overlap domain.

### 1.3 Required inputs/results
Inputs MUST include:
- `scales`: array of scale labels (strings or numbers)
- `raw_curves`: array of `{scale, x: [...], y: [...]}` objects
- `collapse_mapping`: freeform object describing the rescaling used (explicitly recorded)
- `collapsed_curves`: array of `{scale, u: [...], y: [...]}`

Results MUST include:
- `collapse_error_rms` (number)
- `overlap_fraction` (number in [0,1]) describing how much common domain is shared
- `n_curves` (integer)

### 1.4 Acceptance checks (explicit tolerances)
Because COSMO’s memory does not fix a universal numeric target, tolerances here are internal-quality thresholds:
- **CHECK RG_SCALING_001 (collapse quality):**
  - Pass if `collapse_error_rms <= 0.10`
- **CHECK RG_SCALING_002 (overlap adequacy):**
  - Pass if `overlap_fraction >= 0.70`
- **CHECK RG_SCALING_003 (minimum evidence):**
  - Pass if `n_curves >= 3`

### 1.5 Required failure-mode fields (must be populated when applicable)
Failure modes are mandatory structured records. This benchmark expects (at minimum) the following possible categories:
- `insufficient_overlap` (e.g., curves do not share domain after rescaling)
- `nonmonotone_scale_label` (scale proxy not consistent with ordering)
- `collapse_sensitive_to_truncation` (collapse changes materially when truncation changes; must cite truncation string)
- `regulator_dependence_flag` (collapse changes materially under regulator changes; must cite regulator string)
- `numerical_instability` (e.g., interpolation artifacts)

---

## 2) Observable Benchmark: Two-point function shape + scaling (QFT-style correlator diagnostic)

### 2.1 Why this is in-scope (memory grounding)
- COSMO’s translation-layer notes list **in-in correlators/scattering** as explicit causal-set QFT observable types.
- Two-point functions are the minimal correlator-shape diagnostic that can be computed across discrete/continuum-like approaches without requiring external normalization constants.

### 2.2 Observable definition
User provides two-point function samples at multiple coarse-graining/RG conditions:
- `G_i(r)` with `r` a separation proxy (graph distance, embedding distance, or experimental distance), and
- an optional scaling map that rescales `r` and/or `G` to compare shapes across runs.

This benchmark checks:
1) **Shape agreement** under the user-recorded scaling map,
2) **Self-consistency** of the scaling across multiple coarse-graining levels.

### 2.3 Required inputs/results
Inputs MUST include:
- `separation_definition` (string; e.g. "graph_distance", "embedding_distance",