# COSMO v0.1 Benchmark Contract Spec (Contract section)

This document defines the standardized **Contract** section that MUST be present for every benchmark in `benchmarks_v0_1.md` and the compliance reporting required for every contributed implementation.

## 1. Contract section placement and shape
Each benchmark entry MUST contain a top-level subsection named exactly `## Contract` (or `### Contract` if nested under the benchmark heading) containing a single fenced YAML block:

```yaml
contract:
  version: "v0.1"
  benchmark_id: "..."
  title: "..."
  scope: "..."
  io:
    inputs: [...]
    outputs: [...]
  required_metadata: {...}
  reference_algorithm:
    kind: "pseudocode"  # or "math"
    body: |-
      ...
  output_invariants:
    - id: "inv_..."
      statement: "..."
      severity: "MUST"  # MUST|SHOULD
  tolerance_policy: {...}
  canonical_test_vector: {...}
  compliance_reporting: {...}
```

Normative keywords **MUST/SHOULD/MAY** are used as in RFC 2119.

## 2. Required fields (schema-level requirements)
All keys below MUST be present unless explicitly marked MAY.

- `contract.version` MUST equal `"v0.1"`.
- `contract.benchmark_id` MUST match the benchmark identifier used in the document (stable, lowercase, `[a-z0-9_]+`).
- `contract.title` human-readable name for the benchmark.
- `contract.scope` one-paragraph description of what is in/out of scope (include exclusions).
- `contract.io.inputs` list of input descriptors, each:
  - `name` (string), `type` (string), `units` (string or `null`), `shape` (string), `domain` (string), `required` (bool).
- `contract.io.outputs` list of output descriptors, each:
  - `name`, `type`, `units`, `shape`, `range` (string), and `determinism` (`deterministic|stochastic`).
- `contract.required_metadata` MUST include:
  - `dataset` (id or `"none"`), `dataset_version` (string or `null`)
  - `license` (string), `citation` (string)
  - `randomness` (`none|seeded|stochastic`), `required_seed_fields` (list, possibly empty)
  - `hardware_assumptions` (string, MAY be `"none"`)
  - `dependencies` (list of `{name, version_spec}`), MAY be empty
- `contract.reference_algorithm` MUST specify the authoritative computation:
  - `kind`: `"pseudocode"` or `"math"`.
  - `body`: minimal but complete description sufficient to reproduce outputs.
- `contract.output_invariants` list of invariants; each invariant MUST include `id`, `statement`, `severity`.
- `contract.tolerance_policy` defines pass/fail semantics for numeric comparisons (see §3).
- `contract.canonical_test_vector` defines a small, deterministic test that every implementation MUST pass (see §4).
- `contract.compliance_reporting` defines how contributors report compliance (see §5).
## 3. Tolerance policy (comparison semantics)
Implementations MUST evaluate outputs against the contract using the policy below. The policy is expressed per output field; if absent for a field, `default` applies.

```yaml
tolerance_policy:
  default:
    mode: "exact"  # exact|abs|rel|abs_rel|ulps|custom
    abs: 0.0
    rel: 0.0
    ulps: 0
    nan_equal: false
    inf_equal: true
  per_output:
    output_name:
      mode: "abs_rel"
      abs: 1e-8
      rel: 1e-6
```

Modes:
- `exact`: values MUST be bitwise-equal for scalars; for arrays, elementwise equality.
- `abs`: pass if `|a-b| <= abs`.
- `rel`: pass if `|a-b| <= rel*max(|a|,|b|)`.
- `abs_rel`: pass if `|a-b| <= max(abs, rel*max(|a|,|b|))`.
- `ulps`: pass if ULP distance <= `ulps` (IEEE-754 floats only).
- `custom`: allowed only if `reference_algorithm.body` defines the comparator unambiguously.

Special values:
- `nan_equal`: if true, NaN compares equal to NaN; otherwise any NaN yields failure for that element.
- `inf_equal`: if true, +inf==+inf and -inf==-inf; otherwise any inf yields failure.

Aggregation for arrays/tensors:
- The comparison MUST be elementwise; failure occurs if ANY element fails unless the policy includes
  `aggregate: "all"` (default) or `aggregate: "fraction"` with `max_fail_fraction` in `[0,1]`.
- Shape/dtype mismatches are always failures independent of tolerances.

Non-numeric outputs:
- MUST be compared with `exact` semantics unless `reference_algorithm` defines a different, deterministic canonicalization.
## 4. Canonical test vector (CTV) rules
Each benchmark MUST include exactly one `canonical_test_vector` with:
- `id`: stable id string (e.g., `"ctv_001"`).
- `purpose`: what the vector validates.
- `inputs`: fully specified inputs (no ellipses; no external files).
- `expected_outputs`: expected outputs from the reference algorithm.
- `notes` (MAY): clarifications, edge cases, or numerical caveats.
- `tolerance_overrides` (MAY): per-output overrides that supersede `tolerance_policy` ONLY for the CTV.

CTV requirements:
1. Deterministic: if randomness exists, the CTV MUST specify seed fields listed in `required_seed_fields`.
2. Minimal: small enough to run quickly (seconds) on commodity hardware.
3. Representative: exercises at least one non-trivial code path (not a degenerate identity case).
4. Self-contained: any constants used MUST be embedded as literals.
5. Canonical encoding: numbers in decimal; arrays in JSON-like lists; strings in UTF-8.

If a benchmark is stochastic by design, the CTV MUST specify either:
- a fixed seed that makes outputs deterministic, OR
- a distributional invariant in `output_invariants` plus a tolerance policy that compares summary statistics (must be defined under `custom`).
## 5. Output invariants (required checks)
Invariants are additional checks beyond direct output matching. Examples:
- shape and dtype constraints (e.g., “output logits shape == (N,K)”)
- monotonicity / boundedness (e.g., “all probabilities in [0,1] and sum to 1 within 1e-6”)
- conservation constraints, symmetry, ordering, or schema constraints

Severity:
- `MUST`: failing invariant => benchmark FAIL even if tolerances pass.
- `SHOULD`: failing invariant => benchmark WARN; does not change pass/fail unless an implementation opts-in to stricter mode.

Every benchmark MUST include at least:
- one invariant about output shape/schema, and
- one invariant about value validity (range, normalization, finiteness, etc.), if applicable.

## 6. Compliance reporting (required for contributors)
Every contributed implementation MUST report contract compliance for each benchmark it claims to support.

Required report fields (machine-readable JSON recommended):
- `benchmark_id`, `contract_version`
- `implementation_id` (name/version), `runtime` (language + version), `platform` (OS/CPU/GPU)
- `result`: `pass|fail|warn`
- `checks` list, each: `{name, status, details}` where `status` is `pass|fail|warn|skip`
- `diagnostics` on failure: mismatched outputs with indices, max abs/rel error, invariant failures, seed used, and input hash.

Minimum checks to report:
1. Contract parsing/validation of required fields.
2. CTV execution and output comparison using tolerance policy (+ overrides).
3. Evaluation of all `MUST` invariants (and `SHOULD` if supported).

If an implementation cannot support a benchmark, it MUST report `skip` with a reason (e.g., missing dependency/hardware).
## 7. Canonical Contract example (compact)
```yaml
contract:
  version: "v0.1"
  benchmark_id: "example_bench"
  title: "Example Benchmark"
  scope: "Compute y = a*x + b for scalar x."
  io:
    inputs:
      - {name: x, type: float64, units: null, shape: "()", domain: "finite real", required: true}
      - {name: a, type: float64, units: null, shape: "()", domain: "finite real", required: true}
      - {name: b, type: float64, units: null, shape: "()", domain: "finite real", required: true}
    outputs:
      - {name: y, type: float64, units: null, shape: "()", range: "finite real", determinism: deterministic}
  required_metadata:
    dataset: "none"
    dataset_version: null
    license: "CC-BY-4.0"
    citation: "COSMO Benchmarks v0.1"
    randomness: "none"
    required_seed_fields: []
    hardware_assumptions: "none"
    dependencies: []
  reference_algorithm:
    kind: "pseudocode"
    body: |-
      y = a*x + b
  output_invariants:
    - {id: inv_shape, statement: "y is a scalar float64", severity: MUST}
    - {id: inv_finite, statement: "y is finite (not NaN/Inf)", severity: MUST}
  tolerance_policy:
    default: {mode: abs_rel, abs: 0.0, rel: 0.0, ulps: 0, nan_equal: false, inf_equal: true}
    per_output: {y: {mode: abs_rel, abs: 1e-12, rel: 1e-12}}
  canonical_test_vector:
    id: "ctv_001"
    purpose: "Basic affine mapping."
    inputs: {x: 2.0, a: 3.0, b: 4.0}
    expected_outputs: {y: 10.0}
  compliance_reporting:
    required: true
    format: "json"
    minimum_fields: ["benchmark_id","contract_version","implementation_id","result","checks","diagnostics"]
```
