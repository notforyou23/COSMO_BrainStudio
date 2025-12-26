## Update to Spec: “Benchmark Contract” Sections (v0.1)

This update defines a standardized, tool-supported **benchmark contract** for each v0.1 task. The contract is designed so every implementation can automatically validate and report **clear pass/fail compliance with diagnostics**, and so benchmark computation is reproducible as a pipeline with standardized schemas, a CLI, and automated tests/CI.

This is grounded in COSMO’s consolidated findings that each v0.1 task needs: **required metadata, a reference algorithm, output invariants, tolerance rules, and canonical test vectors**, supported by validators and automated tests/CI.

---

# 1) Benchmark Contract: Required Sections and Fields

A benchmark contract MUST be representable in a machine-validated schema and MUST be checkable by tooling (validator + tests). The repo artifacts already reflect this direction with:

- A JSON Schema for benchmark cases: `outputs/schemas/benchmark.schema.json`
- Example benchmark case: `outputs/examples/benchmark_case_001.json`
- Expected outputs for reproducibility checks: `outputs/expected/benchmark_case_001.expected.json`
- Python schema/validator tooling: `outputs/src/benchmarks/schema.py`
- CLI wrapper: `outputs/src/benchmarks/cli.py`
- Compute/reference implementation module: `outputs/src/benchmarks/compute.py`
- Existing tests:  
  - `outputs/tests/test_schema_conformance.py`  
  - `outputs/tests/test_benchmark_reproducibility.py`  
- CI workflow: `.github/workflows/ci.yml` (in the code-creation outputs)

## 1.1 Contract document structure (normative)

Each v0.1 benchmark contract MUST define these sections:

### A) Metadata (required)
Minimum required metadata fields (must be present and validated):

- `contract_version` (benchmark contract format version; required to lock semantics for validation)
- `task_id` (v0.1 task identifier; required)
- `case_id` (unique case identifier; required)
- `description` (human-readable description; required)
- `reference` (reference algorithm identifier and/or module entrypoint; required)

Rationale (from consolidated findings): benchmarks must include **required metadata** and be **tool-supported** so every implementation can validate and report compliance.

### B) Inputs (required)
Each benchmark case MUST include an “inputs” section conforming to the contract schema. This must be machine-validatable (JSON Schema) and supported by standardized I/O modules/CLI.

Rationale: contracts must be checkable automatically, and designs should be implemented as reproducible pipelines with standardized I/O schemas and a CLI.

### C) Reference algorithm (required)
The contract MUST specify a reference algorithm used to generate expected outputs and invariants. This may be expressed as:

- A named implementation entrypoint in code (e.g., compute module), and
- Canonical expected outputs (“golden” outputs), and
- Any deterministic requirements (seedability where relevant)

This is consistent with the existing structure that includes `outputs/src/benchmarks/compute.py` and tests for reproducibility.

### D) Outputs + invariants (required)
The contract MUST define:

- The output fields produced by the reference algorithm
- Output invariants that must hold across implementations (e.g., reproducibility checks against expected outputs, required output shape/keys)

Rationale (from consolidated benchmark-contract finding): define **output invariants** and **canonical test vectors** so implementations can automatically validate.

### E) Tolerance rules and uncertainty reporting (required)
The contract MUST define:

- Numerical tolerance rules (how comparisons are done and what deviations are permitted)
- Uncertainty reporting requirements (what uncertainty fields must exist, where applicable)

This aligns with the mission requirement (“allowed ranges, uncertainty reporting, and acceptance tests”) and the overall benchmark-contract concept (tolerance rules).

### F) Acceptance tests (required)
Each contract MUST declare acceptance tests that can be run automatically:

- Schema conformance validation
- Deterministic reproducibility test(s) against canonical expected output
- Tolerance-based numerical comparison tests

Existing repository direction shows multiple test modules for schema validation, deterministic recomputation, and numerical tolerances (see the separate test suite files listed in memory, including `tests/test_numerical_tolerances.py` and `tests/test_deterministic_recompute.py` in another generated test set). This spec update makes these contract-mandated.

---

# 2) Allowed Ranges (Inputs) and Required Output Constraints

Because the only concrete, tool-level facts provided are the presence of the JSON Schema file and associated validator/tests, the allowed ranges MUST be enforced via the JSON Schema used by the validator. Concretely:

## 2.1 Inputs allowed ranges (normative)
- Every numeric input field that can affect benchmark computation MUST have an allowed range defined in the schema (e.g., JSON Schema numeric bounds).
- Every categorical input MUST be constrained (e.g., enumerations) in the schema.
- Every required input MUST be listed as required in the schema.

Implementation anchoring (existing): `outputs/schemas/benchmark.schema.json` is the contract’s machine-readable mechanism.

## 2.2 Output constraints/invariants (normative)
- The output object MUST contain the required keys defined by the contract.
- The output MUST satisfy invariants defined by the contract and validated by tests.
- The output MUST be reproducible against canonical expected outputs under the reference algorithm, within the contract tolerances.

Implementation anchoring (existing): `outputs/expected/benchmark_case_001.expected.json` + reproducibility test `outputs/tests/test_benchmark_reproducibility.py`.

---

# 3) Uncertainty Reporting (Contract Requirement)

The benchmark contract MUST explicitly state how uncertainty is represented and validated.

## 3.1 Minimum requirement
- If a benchmark output includes quantities that are compared using tolerance rules, the contract MUST define whether uncertainty is:
  - explicitly reported in the output payload, and/or
  - implicitly handled via contract tolerances, and/or
  - both

This is required by the mission (“uncertainty reporting”) and fits the benchmark-contract requirement for tolerance rules and output invariants.

## 3.2 Validation requirement
- The validator MUST check presence/shape of any uncertainty fields that the contract declares as required.
- Acceptance tests MUST include at least one case that fails when uncertainty reporting fields are missing or malformed, if uncertainty is required by that contract.

(Where uncertainty fields exist in schema, this is enforceable via JSON Schema + validator.)

---

# 4) Acceptance Tests (Contract-Mandated Test Set)

Each benchmark contract MUST ship with at least these acceptance tests, implemented as automated tests and runnable in CI:

## 4.1 Schema conformance test (required)
- Load the benchmark case JSON.
- Validate against the benchmark schema (contract schema).
- Fail with diagnostics if schema violations occur.

Repository anchoring: `outputs/tests/test_schema_conformance.py` already exists as a schema conformance test.

## 4.2 Reproducibility test against canonical expected outputs (required)
- Run the reference compute pipeline on the canonical input case(s).
- Compare produced output to the canonical expected output JSON.

Repository anchoring: `outputs/tests/test_benchmark_reproducibility.py` exists and is explicitly aimed at reproducibility.

## 4.3 Tolerance-based numerical comparison (required where numeric outputs exist)
- Compare numeric outputs within contract-defined tolerance rules (absolute/relative as defined in contract).
- Report diagnostics indicating which fields exceeded tolerances.

Repository anchoring: separate generated tests include `tests/test_numerical_tolerances.py` (listed in memory), which is consistent with this requirement; this update makes it mandatory per contract.

## 4.4 Negative test case(s) (required)
At least one negative test MUST exist per contract suite to confirm the validator rejects invalid cases.

Mission requirement: “add at least one negative test case.”

---

# 5) Implement Contract Checks in the Validator

This section defines exactly what “contract checks” means in validator behavior, and how to implement them using the existing tooling layout.

## 5.1 Validator responsibilities (normative)
The validator MUST:

1. **Validate schema conformance** of benchmark case JSON using the canonical contract schema.
2. **Validate required contract sections** exist (metadata, inputs, reference algorithm identifier, output/tolerance specification if present in the case format).
3. **Validate allowed ranges** via schema bounds and enumerations.
4. **Validate uncertainty reporting requirements** as declared by the contract (schema-enforced where possible).
5. **Validate acceptance conditions** by supporting tests that recompute outputs and compare against canonical expected outputs within tolerance rules.

Repository anchoring:
- The schema check capability is represented by `outputs/src/benchmarks/schema.py`.
- CLI-based execution is represented by `outputs/src/benchmarks/cli.py`.
- Compute/reference algorithm is represented by `outputs/src/benchmarks/compute.py`.

## 5.2 Diagnostics requirement (normative)
When validation fails, the validator MUST report:
- Which contract requirement failed (schema vs tolerance vs missing required section)
- Which field/path triggered the failure

This is part of “clear pass/fail compliance with diagnostics” from the consolidated benchmark-contract finding.

---

# 6) Add a Negative Test Case (Required by Mission)

At least one negative test must be added. The most direct, contract-grounded negative test is schema rejection.

## 6.1 Negative test: schema violation (recommended minimal addition)
Add a test that loads a deliberately invalid benchmark JSON (e.g., missing a required metadata field, or containing a value outside schema range) and asserts validation fails.

### Files to add (concrete)
1) `outputs/examples