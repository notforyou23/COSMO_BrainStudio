# generated_script_1766440494796

This repository defines a small, testable “benchmark contract” workflow: unit tests validate utilities and schema handling, and a benchmark runner produces artifacts and diffs them against golden references within stated tolerances.

## Acceptance criteria (exact)

### A. Tests
- Command: `python -m pytest`
- Pass condition: **pytest exits with code 0** (no failing tests).

### B. Benchmark
- Command (canonical): `python -m src.run_benchmark --contract benchmarks/contracts/v0_1.json`
- Pass condition: the runner reports **diff within tolerance** and **exits with code 0**.

### C. Contract + file paths (v0.1)
The benchmark runner must treat `benchmarks/contracts/v0_1.json` as the single source of truth for:
- `task_version`: must be `"v0.1"`.
- `reference_impl`: module/function to execute (the “reference algorithm”).
- `inputs`: paths to required input artifacts (relative to repo root unless absolute).
- `outputs`: required output artifact paths the runner must write.
- `golden`: paths to golden/reference outputs to diff against.
- `tolerances`: numeric tolerance policy used by `src.diff` and enforced by `src.run_benchmark`.

Unless overridden by the contract, the project-level defaults are:
- Numeric scalar/array tolerances: `abs_tol = 1e-6`, `rel_tol = 1e-6`
- Non-numeric fields (strings, booleans, enums, keys): **exact match**.
- Missing/extra required keys in structured outputs: **fail**.
- NaN handling: NaN equals NaN only if both sides are NaN at the same position; otherwise fail.

### D. Diff decision rule
A benchmark is considered passing iff **all** required output artifacts exist and every compared numeric value satisfies:
- `|a - b| <= abs_tol + rel_tol * |b|`
where `a` is the produced value and `b` is the golden value, and all structured/non-numeric comparisons are exact as defined above.

## Golden path

Run from the repository root:

```bash
python -m pytest
python -m src.run_benchmark --contract benchmarks/contracts/v0_1.json
```

Expected outcomes:
- The first command exits `0`.
- The second command writes benchmark outputs to the contract-specified `outputs` paths, writes/prints a diff summary, and exits `0` only when the diff is within tolerance.
