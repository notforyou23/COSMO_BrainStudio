# Roadmap: Scope, Success Criteria, and 20-Cycle Milestones

**Document purpose:** Define scope boundaries, subtopics, prioritization policy, Definition of Done (DoD), and a 20-cycle milestone outline for a roadmap-driven build.

**Audience:** Contributors, reviewers, and stakeholders who need a shared contract for what will (and will not) be built, how work is chosen, and what “done” means.
## 1) Scope Boundaries

### In scope (what we will do)
- Produce and maintain a roadmap artifact that is actionable and reviewable.
- Establish clear scope boundaries (in/out), explicit success criteria, and measurable DoD.
- Identify subtopics (workstreams) and how they fit together.
- Define a prioritization policy (how items are selected and ordered).
- Outline 20 development cycles with goals, expected outputs, and review gates.

### Out of scope (what we will not do)
- Building the full product implementation beyond what is needed to validate the roadmap process.
- Organization-specific commitments (dates, staffing, budget) unless explicitly supplied.
- Non-roadmap documentation (e.g., full architecture spec, full user manual), except brief supporting notes embedded in the roadmap.
- Unbounded research with no decision outcome; research must produce a decision, artifact, or testable hypothesis.

### Assumptions
- “Cycle” is a short, fixed cadence (e.g., 1–2 weeks) with planning, execution, and review.
- Milestones are defined by deliverables and acceptance criteria rather than calendar dates.
- Every cycle ends with a checkpoint: decision, demo, or measurable artifact.
## 2) Subtopic List (Workstreams)

1. **Problem framing & success criteria**
   - Goals, non-goals, personas/stakeholders, measurable outcomes.

2. **Requirements & scope control**
   - Functional requirements, non-functional requirements (NFRs), change control, traceability.

3. **Information architecture for the roadmap**
   - Backlog taxonomy, epics/themes, cycle planning format, cross-dependencies.

4. **Prioritization & governance**
   - Scoring model, decision rights, escalation paths, review cadence.

5. **Quality system (DoD, validation, and review)**
   - Acceptance criteria templates, review checklists, artifact standards, auditability.

6. **Risk management**
   - Risk register, mitigations, contingency triggers, “kill/continue/pivot” criteria.

7. **Delivery enablement**
   - Tooling assumptions, reporting, communication plan, stakeholder updates.

8. **Lifecycle & iteration**
   - How updates are made, versioning, deprecation, and post-cycle retrospectives.
## 3) Prioritization Policy

### Objectives
Prioritize items that maximize learning and user value while minimizing risk and rework.

### Inputs (what we consider)
- **User value / impact:** measurable benefit to target users or stakeholders.
- **Risk reduction:** security, compliance, reliability, technical uncertainty.
- **Dependency unlocking:** work that unblocks multiple downstream items.
- **Effort / cost:** estimated time/complexity; prefer small, testable slices.
- **Time criticality:** external deadlines only if confirmed and documented.
- **Confidence:** evidence level supporting the item (data, interviews, prototypes).

### Method (how we decide)
- Use a simple weighted scoring rubric (example weights):
  - Impact 30%, Risk reduction 25%, Dependency unlocking 20%, Effort (inverse) 15%, Confidence 10%.
- Items must include: problem statement, proposed outcome, acceptance criteria, and minimal validation plan.
- Each cycle includes:
  - **Committed scope (70–80%)**: highest-scoring items with clear acceptance criteria.
  - **Discovery buffer (20–30%)**: research/prototyping to raise confidence for future cycles.

### Rules of engagement
- No item enters a cycle without acceptance criteria.
- If an item’s scope changes materially mid-cycle, it is either:
  - reduced to an MVP slice that still meets acceptance criteria, or
  - moved back to backlog with a recorded decision rationale.
## 4) Definition of Done (DoD)

An item is **Done** only when all applicable criteria are met:

### Delivery criteria
- Clear acceptance criteria met and verified (demo, tests, or documented validation).
- Outputs are written down (artifact exists) and are discoverable (linked in roadmap/backlog).
- Stakeholders can understand what changed and why (short change note).

### Quality criteria
- Validation performed appropriate to the item:
  - Document: peer review completed, contradictions resolved, and versioned.
  - Process: exercised on at least one cycle planning/review loop.
  - Decision: recorded with alternatives considered and evidence cited.
- No critical gaps: scope boundaries, success metrics, and owners are explicit.

### Governance criteria
- Risks and dependencies updated (risk register and dependency notes).
- Retro notes captured: what to keep/change next cycle.
- If metrics were defined, a baseline or measurement plan exists.

### “Not Done” examples
- “Looks good” without acceptance criteria.
- Work completed but not documented, linked, or reviewable.
- Research completed with no decision, artifact, or next-step commitment.
## 5) Success Criteria (Project-Level)

This roadmap effort is successful when:

1. **Clarity:** Scope boundaries, subtopics, prioritization policy, and DoD are unambiguous and internally consistent.
2. **Actionability:** The 20-cycle outline can be used to run planning immediately (each cycle has objectives and artifacts).
3. **Traceability:** Each milestone maps to at least one deliverable with acceptance criteria and review gates.
4. **Governance:** A repeatable change process exists (how new requests enter, are scored, and scheduled).
5. **Quality:** Reviews consistently detect and resolve contradictions; decisions are recorded with rationale.
## 6) 20-Cycle Milestone Outline

**Legend:** Each cycle ends with: (a) artifact(s), (b) review gate, (c) updated backlog.

### Cycle 1 — Kickoff & framing
- Deliverables: project goals/non-goals, stakeholder list, initial success metrics.
- Gate: stakeholder alignment sign-off on goals and non-goals.

### Cycle 2 — Scope boundaries v1
- Deliverables: in-scope/out-of-scope, assumptions, constraints, glossary.
- Gate: scope reviewed; unresolved ambiguities logged as risks.

### Cycle 3 — Workstream breakdown
- Deliverables: subtopic/workstream map, ownership model, dependency draft.
- Gate: agreement on taxonomy (themes/epics/cycles).

### Cycle 4 — Prioritization rubric v1
- Deliverables: scoring model + examples, decision rights, intake checklist.
- Gate: run rubric on 10 sample backlog items; adjust weights.

### Cycle 5 — DoD v1 + review checklist
- Deliverables: DoD, acceptance criteria template, review checklist.
- Gate: trial review of cycles 1–4 artifacts using the checklist.

### Cycle 6 — Backlog seed & sizing approach
- Deliverables: initial backlog (themes/epics), sizing heuristics, WIP limits.
- Gate: backlog meets entry criteria (problem, outcome, acceptance criteria).

### Cycle 7 — Risk register v1
- Deliverables: risk register, mitigation plan, triggers, owners.
- Gate: top risks have mitigation or explicit acceptance rationale.

### Cycle 8 — Dependency & integration plan
- Deliverables: dependency graph, sequencing proposal, integration gates.
- Gate: identify critical path and alternative sequencing.

### Cycle 9 — Measurement plan
- Deliverables: metrics definitions, baseline plan, reporting cadence.
- Gate: metrics are measurable, owned, and tied to success criteria.

### Cycle 10 — Roadmap v1 (cycles 11–20 draft)
- Deliverables: consolidated roadmap narrative and cycle outlines.
- Gate: roadmap consistency review (scope ↔ milestones ↔ DoD).

### Cycle 11 — Validation pass: “run the process”
- Deliverables: simulate a planning session using roadmap v1; capture issues.
- Gate: list of process improvements prioritized.

### Cycle 12 — Governance hardening
- Deliverables: change control process, escalation paths, decision log format.
- Gate: change request flows from intake → scoring → scheduling in a dry run.

### Cycle 13 — Quality & auditability improvements
- Deliverables: versioning rules, document structure standards, link hygiene.
- Gate: random audit can trace decision → artifact → acceptance evidence.

### Cycle 14 — Stakeholder communication package
- Deliverables: one-page executive summary, update template, FAQ.
- Gate: stakeholders confirm readability and completeness.

### Cycle 15 — Roadmap v2 (refined sequencing)
- Deliverables: updated cycle goals, refined dependencies, updated risk posture.
- Gate: reconcile all open contradictions; residuals logged as known issues.

### Cycle 16 — Continuous improvement loop
- Deliverables: retro-driven adjustments, updated rubrics/checklists, playbook.
- Gate: reduced cycle overhead and improved review pass rate (measured).

### Cycle 17 — Scenario planning
- Deliverables: 2–3 scenarios (best/base/worst), scope cut-lines, contingency plan.
- Gate: explicit triggers for pivot/de-scope documented.

### Cycle 18 — Final consistency & coverage review
- Deliverables: coverage matrix (scope items ↔ milestones ↔ DoD ↔ metrics).
- Gate: no orphaned items; all milestones have artifacts and gates.

### Cycle 19 — Publication-ready release
- Deliverables: final markdown roadmap, changelog, version tag, distribution plan.
- Gate: publication checklist complete; stakeholder sign-off.

### Cycle 20 — Handoff & sustainability
- Deliverables: maintenance plan, ownership transfer, next-20-cycle backlog seed.
- Gate: new owner can run cycle planning using only the published artifacts.
## 7) Maintenance & Change Process (Summary)

- Updates are made via a recorded change request (CR) with:
  - problem, proposed change, impact, dependencies, scoring, and acceptance criteria.
- Changes are reviewed in a fixed cadence (each cycle review).
- Roadmap versions use semantic-style labels: v1.0, v1.1 (minor), v2.0 (major resequencing/scope shift).
