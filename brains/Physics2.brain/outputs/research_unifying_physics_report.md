# COSMO Technical Report (Baseline → Frameworks → Prototypes → Limits → Roadmap)

**Date:** 2025-12-22  
**Scope constraint:** This report uses **only** the facts explicitly provided in the “KNOWLEDGE FROM MEMORY” block. Where a typical technical report would include additional domain details (e.g., explicit spin-foam amplitudes, causal-set dynamics, or cosmology model formulas), those are **intentionally not invented** here.

---

## Abstract

COSMO’s core finding is methodological: robust computational research workflows emerge from treating experiments and benchmarks as **end-to-end reproducible artifacts** with **explicit schemas**, **reference outputs**, **deterministic I/O**, **fixed hashing/serialization**, and **numerical tolerance policies**, continuously safeguarded via **automated tests and CI** so changes preserve both **data validity** and **numerical results**. We translate that into candidate framework designs and prototypes: (i) schema-driven benchmark tooling (`qg_bench`, `outputs/src/benchmarks`) and (ii) a continuum-recovery diagnostics API for spin-foam/GFT renormalization (`sf_gft_diagnostics`). We also include a small toy RG script describing a φ⁴-like one-loop flow model in \(d=4-\varepsilon\). We critically analyze what is *not yet provided by the knowledge base*: missing empirical results/plots, incomplete contract specification text, and incomplete cross-program normalization conventions. We conclude with a prioritized 1-/3-/5-year roadmap centered on reproducible benchmark contracts, CI-enforced golden tests, and differential experimental designs that separate technical noise from any residual environment-insensitive decoherence signatures (including gravitational-potential-dependent scaling).

---

## 1. Literature and Baseline (2020–2025)

### 1.1 Baseline: reproducible computational research as artifact engineering

Across consolidated COSMO findings, the baseline claim is consistent:

- Robust computational research workflows come from treating **experiments and benchmarks** as **end-to-end reproducible artifacts**, defined by:
  - **Explicit schemas** (inputs/outputs and metadata),
  - **Reference outputs** (“goldens”),
  - **Reusable utilities** (I/O, hashing, validation),
  - **Continuous verification** via **automated tests and CI**  
  so that changes reliably preserve both **data validity** and **numerical results**.  
  (Consolidated points 1–5)

A concise operational statement used repeatedly is:

> Standardize experiments as **deterministic, schema-defined, CLI-driven pipelines** whose complete state and expected outputs are captured as reproducible artifacts and continuously safeguarded by reusable tooling plus automated tests/CI to ensure changes preserve both validity and numerical results.  
(Consolidated points 2–4)

### 1.2 Quantum gravity research landscape (snapshot references only)

Two baseline “literature map” anchors were provided:

1. **Handbook reference (multi-approach snapshot):** A “Handbook of Quantum Gravity” (Springer) exists as a multi-approach 2020–2025 snapshot, first released 2023, with a major dated release **Dec 3–4, 2024**, organized by program (string/holography, loop/spinfoams, asymptotic safety, CDT, effective/perturbative QG, nonlocal/ghost-free models, etc.). (Fact 29)

2. **RG/coarse-graining as cross-program thread:** Renormalization-group/coarse-graining ideas are explicitly presented (circa **2021 special-issue framing**, e.g. arXiv:2103.14605) as a unifying conceptual and technical thread relating microscopic spacetime models to emergent semiclassical behavior and phenomenology. (Facts 27, 16/59)

### 1.3 Spin-foam LQG trend (2018–2025)

A specific directional claim is provided:

- Spin-foam LQG (2018–2025) shifted from primarily kinematical results toward **continuum recovery** via **background-independent renormalization/coarse-graining**, including **tensor-network-inspired methods**, aimed at diagnosing continuum limits and restoring **effective diffeomorphism symmetry**. (Fact 13)

### 1.4 Observable classes that appear across the translation layer

The translation guide (v0.1) restricts itself to observable *types* needed for benchmarks (no extra normalization claims). Observable classes explicitly mentioned include: (Facts 16/59)

- Hawking-like emission / correlations in analogue systems with emphasis on systematics/backreaction.
- Causal-set QFT observables: entanglement entropy, in-in correlators/scattering.
- Decoherence observables: decoherence rates/spectra and scaling with gravitational potential differences; noise PSD and filter-function outputs (CPMG/spin-echo).

### 1.5 Decoherence: engineering vs potential gravity-induced residuals

A consistency review (Cycle 1) establishes a tension between:
- Decoherence as **information leakage to environment** (engineering + control; mitigatable),
vs
- Gravity-induced dephasing tied to potential differences (possibly **irreducible**), with a proposed qualitative ordering (“superpositions of *when* decohere before those of *where*”) and dependencies on gravitational potential differences. (Fact 6)

Recommended action sequence from that review:
1. Perform noise spectroscopy (CPMG, spin-echo, filter-function analysis) to extract dephasing PSD; implement dynamical decoupling (Uhrig/concatenated/optimized) and quantify residual budgets.
2. Then run differential experiments varying gravitational potential differences while holding local environment constant; look for residual environment-insensitive scaling. (Fact 6)

---

## 2. Candidate Frameworks (Design Targets)

COSMO’s candidate frameworks are not “theories of quantum gravity” here; they are **computational research frameworks** for producing, validating, and comparing diagnostics across approaches.

### 2.1 Framework A: Schema-driven benchmark artifacts + deterministic CLIs + CI golden tests

**Core design:** build a schema-driven, CLI-accessible pipeline whose outputs are deterministically reproducible (fixed serialization/hashing and numerical tolerances) and continuously enforced through automated tests and CI. (Consolidated point 3)

**Why:** enables exporting the *complete state* (code, configs, inputs, expected outputs) so the project can be reconstructed identically outside the original environment. (Consolidated point 4)

**Concrete instantiations present in artifacts:**

- `qg_bench` package (schema, dataset, CLI, hashing, tests). (Fact 14)
- A second benchmark scaffold under `outputs/` with JSON schema, examples, expected outputs, CLI, tests, and GitHub Actions CI. (Fact 15)
- Additional CI/testing harness: deterministic recompute tests, numerical tolerance tests, schema validation tests, scripts to recompute outputs. (Fact 17)

#### 2.1.1 Contract-first extension (v0.1 benchmark contracts)

A planned/partial specification exists:

> For each v0.1 benchmark, add a contract section: required metadata, reference algorithm/pseudocode, output invariants, tolerance policy, and a canonical test vector; require that every contributed implementation reports contract compliance (pass/fail + diagnostics). (Facts 8, 53)

This contract notion is central to making benchmarks cross-implementation comparable.

---

### 2.2 Framework B: Continuum-recovery diagnostics for spin-foam/GFT renormalization

A dedicated diagnostics package exists:

- `sf_gft_diagnostics` with modules:
  - `observables.py`, `scaling.py`, `metrics.py`, `rg_io.py`, `benchmarks.py`, `reporting.py`, plus `main.py` and `README.md`. (Fact 11)

The explicit goal (from introspection prompt) is:

> Conceptual design and specification for continuum-recovery diagnostics and cross-validation tests for spin-foam/GFT renormalization; produce a prioritized list of candidate continuum observables, scaling quantities, and mutually comparable metrics suitable for tensor-network coarse-graining, etc. (Fact 40)

This directly matches the spin-foam trend toward continuum recovery (2018–2025). (Fact 13)

---

### 2.3 Framework C: Translation layer across communities (only for benchmark computability)

A translation document exists:

- `translation_layer_v0_1.md` mapping key terms/conventions across communities only insofar as needed to compute the benchmarks (RG/coarse-graining terms, observables, normalization conventions). (Facts 12, 16, 59, 65)

**Important explicit limitation in that document:**
- It is out-of-scope to claim detailed formulas, beta functions, critical exponents, partition function normalizations, AdS/CFT dictionary normalizations, or LQG/spinfoam amplitude conventions. (Facts 16/59)

This is both a limitation and a guardrail: comparisons must be based on computable outputs defined by schema + contract, not on assumed normalization equivalences.

---

## 3. Prototype Experiments and Implementations (What exists; what was validated)

This section documents prototypes *as far as the provided facts permit*. The knowledge base includes file manifests, CI configuration presence, and one explicit equation set from a toy RG script header.

### 3.1 Prototype 1: `outputs/` benchmark pipeline with schema + expected outputs + CI

**Artifact set includes:** (Fact 15)
- `.github/workflows/ci.yml` (GitHub Actions CI)
- `outputs/schemas/benchmark.schema.json