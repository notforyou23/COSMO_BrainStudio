# Goal 2 — Test Matrix + Design Rules (Template + Acceptance Criteria)

## Purpose
Define the required **test matrix** and **design rules** used to verify that the system meets requirements across functional, performance, reliability, safety, and compliance dimensions. This document is the single index for Goal 2 artifacts and review readiness.

## Scope
- Applies to all deliverables placed under: `outputs/tests/` and any referenced evidence under `outputs/sim/`, `outputs/compliance/`, `outputs/ops/`, `outputs/models/`.
- Defines required fields, coverage expectations, and sign-off criteria for the Goal 2 pack.

## Definitions (minimal)
- **Requirement ID**: Stable identifier for an externally or internally stated requirement.
- **Test Case ID**: Stable identifier for an executable test (simulation, bench, integration, field).
- **Design Rule**: Constraint or convention imposed on implementation to reduce risk and ensure testability/compliance.
- **Evidence**: Immutable artifact proving test execution/results (logs, reports, plots, traces, configs, seeds).

## Inputs (must be referenced in this pack)
- Requirements source: PRD/SRS/contract/spec (identify name + version/date).
- Architecture baseline: diagrams, interfaces, data contracts (identify name + version/date).
- Risk register and hazards (if applicable): identify name + version/date.
- Verification strategy: identify name + version/date.
## Goal 2 Deliverables (what must exist)
1. **Test Matrix** (this file contains the required schema and a table you will populate).
2. **Design Rules** (this file contains the required schema and a ruleset you will publish).
3. **Evidence Index** (section below mapping Test Case IDs to evidence paths under `outputs/`).

The completed Goal 2 pack is considered ready when all Acceptance Criteria in the final section are met.

---

# Part A — Test Matrix

## Test Matrix Schema (required columns)
Each test row MUST specify:

- **Test Case ID**: e.g., `T-FUNC-001`
- **Requirement ID(s)**: one or more, e.g., `REQ-12`, `REQ-45`
- **Objective**: what is proven
- **Method**: simulation / unit / integration / system / field / inspection / analysis
- **Setup**: environment, model version, dataset, config, seeds, HW/SW versions
- **Stimulus**: inputs, scenarios, parameter ranges
- **Expected Result / Pass Criteria**: numeric thresholds and invariants
- **Metrics**: what is measured and how computed
- **Coverage Tags**: functional area + risk tags + interface tags
- **Evidence Path(s)**: relative paths under `outputs/` (must exist when executed)
- **Owner**: responsible individual/team
- **Status**: planned / implemented / executed / waived (waiver requires rationale + approver)

## Test Matrix (populate for project execution)
| Test Case ID | Requirement ID(s) | Objective | Method | Setup | Stimulus | Pass Criteria | Metrics | Coverage Tags | Evidence Path(s) | Owner | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-FUNC-001 | REQ-001 | Demonstrate baseline functional behavior for nominal scenario | simulation | model=vX.Y; config=...; seed=... | scenario set A | all checks true; no errors | success_rate; error_count | func; nominal | outputs/sim/... | TBD | planned |
| T-PERF-001 | REQ-0XX | Verify performance within limits under load | integration | sw=vX.Y; hw=... | load sweep | p95 latency < N ms | latency_p95; throughput | perf; stress | outputs/tests/... | TBD | planned |
| T-SAFE-001 | HAZ-0XX, REQ-0YY | Validate safety constraint enforcement | system | build=vX.Y; guards enabled | fault injection | constraint never violated | violation_count | safety; fault | outputs/tests/... | TBD | planned |

Note: Replace `TBD` with actual owners; keep IDs stable over time.
## Coverage Expectations (must be satisfied)
Minimum coverage requirements for the completed matrix:

1. **Requirement Coverage**
   - 100% of *in-scope* requirements have at least one associated Test Case ID.
   - Each high-severity/high-risk requirement has >= 2 independent verification methods OR a justified single method with enhanced evidence.

2. **Interface Coverage**
   - Every external interface (API, file format, message, hardware IO) has tests for:
     - nominal behavior,
     - malformed/invalid inputs,
     - boundary conditions (min/max/empty/overflow),
     - backwards/forwards compatibility where applicable.

3. **Scenario Coverage (for simulation/behavioral systems)**
   - Nominal scenarios: representative set of expected operating conditions.
   - Edge cases: rare but plausible conditions derived from hazards/risks.
   - Stress conditions: worst-case load, contention, timing jitter, or resource exhaustion.

4. **Non-Functional Coverage**
   - Performance: latency/throughput/resource bounds with explicit thresholds.
   - Reliability: soak/repeatability; flake-rate tracked and bounded.
   - Security/Privacy (if applicable): authz/authn checks; data handling rules.

5. **Traceability**
   - Each test links to requirement(s) AND to evidence artifacts.
   - Evidence must capture configuration, versioning, and reproducibility information.

---

# Part B — Design Rules

## Design Rules Schema (required for each rule)
Each rule MUST include:
- **Rule ID**: e.g., `DR-ARCH-001`
- **Statement**: mandatory constraint ("MUST"/"MUST NOT"/"SHOULD")
- **Rationale**: why it reduces risk or improves testability/compliance
- **Verification**: how compliance is checked (lint, review, test, analysis)
- **Applicability**: components/modules/interfaces it applies to
- **Exceptions**: allowed only with documented waiver + approver + expiration

## Design Rules (publish the project ruleset)
### Architecture & Interfaces
- **DR-ARCH-001** — Interfaces MUST be versioned and backwards-compatible within a major version.
  - Rationale: prevents breaking integrations and enables staged rollout.
  - Verification: interface contract tests + review of versioning notes.
  - Applicability: all APIs/messages/file formats.
  - Exceptions: allowed with migration plan and deprecation window approved by tech lead.

- **DR-ARCH-002** — Configuration MUST be externalized (no hard-coded environment endpoints or secrets).
  - Rationale: supports reproducible tests and secure operations.
  - Verification: static scan + config review + deployment checklist.
  - Applicability: all runtime components.
  - Exceptions: none for secrets; limited for fixed constants with justification.

### Determinism & Reproducibility
- **DR-REP-001** — Simulation/tests MUST record seeds, configs, and exact model/software versions in evidence.
  - Rationale: ensures reruns reproduce results and supports audits.
  - Verification: evidence checklist + automated metadata extraction.
  - Applicability: all test methods.
  - Exceptions: none.

- **DR-REP-002** — Numerical algorithms SHOULD define tolerances and avoid unstable comparisons.
  - Rationale: reduces flaky tests across platforms.
  - Verification: unit tests + cross-platform runs.
  - Applicability: numeric/ML/signal processing code.
  - Exceptions: allowed with documented error analysis.

### Safety & Guardrails (if applicable)
- **DR-SAFE-001** — Safety constraints MUST be enforced by a single authoritative module with explicit interfaces.
  - Rationale: avoids duplicated logic and inconsistent enforcement.
  - Verification: design review + dedicated safety tests.
  - Applicability: safety-critical constraints.
  - Exceptions: none without safety review board approval.

### Observability & Evidence
- **DR-OBS-001** — All tests MUST emit structured logs and a summarized report suitable for archival in `outputs/`.
  - Rationale: enables quick triage and audit-ready evidence.
  - Verification: CI check for artifact presence + schema validation.
  - Applicability: all automated tests.
  - Exceptions: manual tests require signed test record + attachments.

---

# Part C — Evidence Index (required structure)
List evidence artifacts by Test Case ID. Paths MUST be relative to repository/project root and located under `outputs/`.

| Test Case ID | Evidence Type | Evidence Path | Notes |
|---|---|---|---|
| T-FUNC-001 | report/log/plot | outputs/sim/... | includes config + seed + version |
| T-PERF-001 | report/metrics | outputs/tests/... | includes load profile + thresholds |
| T-SAFE-001 | report/trace | outputs/tests/... | includes fault injection details |

---

# Acceptance Criteria (Goal 2 completion)
The Goal 2 pack is accepted only if ALL are true:

1. **Completeness**
   - Test Matrix table contains all in-scope Requirement IDs and associated Test Case IDs.
   - Design Rules section contains a published ruleset with Rule IDs and verification methods.

2. **Coverage**
   - Coverage Expectations section is demonstrably met (provide counts/percentages in matrix notes or an appended summary).
   - Any gaps are explicitly waived with rationale, approver, and expiry.

3. **Traceability & Evidence**
   - Every executed test row includes valid Evidence Path(s) under `outputs/` and evidence contains version/config/seed metadata where applicable.
   - Evidence paths are stable and uniquely attributable to the test case and run.

4. **Reproducibility**
   - For simulation/automated tests: rerunning with recorded inputs/config produces consistent outcomes within stated tolerances.

5. **Review Checklist (sign-off ready)**
   - Requirements list/version is referenced and unambiguous.
   - Test IDs and Requirement IDs are stable and consistently formatted.
   - Pass criteria are quantitative where possible; otherwise clearly falsifiable.
   - Owners and statuses are populated; waivers documented where used.
   - Design rules have rationales and verification mechanisms.
   - Evidence index includes all executed tests; paths resolve under `outputs/`.
   - Peer review completed by at least: (a) test owner, (b) domain reviewer, (c) quality/compliance reviewer (if applicable).

## Sign-off Record
- Prepared by: ____________________  Date: __________
- Reviewed by (Domain): ____________  Date: __________
- Reviewed by (QA/Compliance): ______  Date: __________
- Approved by: ____________________  Date: __________
