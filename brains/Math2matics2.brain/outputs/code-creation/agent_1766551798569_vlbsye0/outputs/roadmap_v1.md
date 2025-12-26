# Roadmap v1 — Reproducible Pipeline Artifacts

This roadmap tracks deliverables for a deterministic, verifiable end-to-end pipeline with stable artifact schemas and fixed random seeds.
## Deliverable 1 (COMPLETED): Deterministic pipeline artifacts (Stage 1)

**Goal:** Provide a single deterministic pipeline entrypoint that writes the canonical artifacts and makes them easy to verify in CI/CD.

### Canonical artifacts (linked)
- Results (stable JSON schema): [results.json](./results.json)
- Figure (deterministic render): [figure.png](./figure.png)
- Run metadata stamp (reproducibility + provenance): [run_stamp.json](./run_stamp.json)
- Run-scoped logs directory: [logs/](./logs/)
### Coverage matrix (requirements → evidence)

| Requirement | Evidence artifact(s) | What to verify |
|---|---|---|
| Deterministic end-to-end run | [run_stamp.json](./run_stamp.json), [results.json](./results.json) | Fixed seeds recorded; identical metrics across repeated runs |
| Stable output schema | [results.json](./results.json), [run_stamp.json](./run_stamp.json) | Keys present; types consistent; versioned schema fields (if present) |
| Deterministic visualization | [figure.png](./figure.png) | Figure generated with controlled style; file exists and is reproducible |
| Traceable execution logs | [logs/](./logs/) | At least one *.log file with consistent formatting and run identifiers |
| CI/CD readiness | All artifacts above | Pipeline can be invoked non-interactively and produces the same artifacts |
### Notes on verification
- The linked artifacts are intended to be produced by a deterministic entrypoint (e.g., `scripts/run_pipeline.py`) that sets fixed seeds and writes the files exactly to `outputs/`.
- CI can validate reproducibility by running the pipeline twice and comparing artifact hashes (or comparing parsed JSON fields for expected stability).
## Next deliverables (planned)
1. Deterministic entrypoint implementation (`scripts/run_pipeline.py`) that produces the canonical artifacts in `outputs/`.
2. Core pipeline module (`src/pipeline/core.py`) with deterministic data generation/processing and metric computation.
3. Logging utilities (`src/pipeline/logging_utils.py`) to ensure consistent log formatting and run scoping under `outputs/logs/`.
4. Plotting module (`src/pipeline/plotting.py`) for deterministic matplotlib rendering to `outputs/figure.png`.
