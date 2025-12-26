#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
from datetime import date

BASE_DIR = Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution")
OUTPUTS_DIR = BASE_DIR / "outputs"

DEFAULT_FILENAME = "roadmap_scope_success_criteria.md"

SCOPE_BOUNDARIES = [
    ("In scope", [
        "A written roadmap document describing scope boundaries, subtopics, prioritization, Definition of Done, and a 20-cycle milestone outline",
        "Milestones expressed as cycles (Cycle 1..20) with clear goals and tangible deliverables per cycle",
        "Generalizable practices for planning, prioritization, and completion criteria",
    ]),
    ("Out of scope", [
        "Building the actual product, codebase, or features described by the roadmap",
        "Detailed engineering estimates, staffing plans, vendor selection, or budgeting",
        "Legal/HR/compliance commitments beyond high-level risk notes",
        "Dependencies on external systems not described in the roadmap document",
    ]),
    ("Assumptions", [
        "The roadmap is a planning artifact meant to be revised as feedback is gathered",
        "Cycles represent consistent, time-boxed iterations (e.g., weekly/biweekly) but duration is not fixed here",
        "Milestones should be understandable without needing additional project context",
    ]),
]

SUBTOPICS = [
    "Problem statement & target audience",
    "Success criteria & measurable outcomes",
    "Scope boundaries (in/out/assumptions)",
    "Stakeholder map & decision rights",
    "User needs discovery plan",
    "Requirements & constraints (functional/non-functional)",
    "Risks, dependencies, and mitigations",
    "Data, privacy, and security considerations",
    "Architecture overview (conceptual)",
    "Delivery plan (20-cycle milestones)",
    "Quality strategy (testing/reviews/acceptance)",
    "Operations & observability (monitoring, logging, runbooks)",
    "Documentation & knowledge transfer",
    "Launch and iteration plan (beta, feedback loops, rollout)",
]

PRIORITIZATION_POLICY = [
    "Prioritize work that reduces uncertainty earliest (discovery, risks, dependencies).",
    "Favor user-visible value over internal refactors unless refactors unlock near-term delivery.",
    "Sequence by critical path: prerequisites before dependent work; unblock future cycles first.",
    "Use a simple scoring rubric per item: Impact (1-5) + Confidence (1-5) + Urgency (1-5) - Effort (1-5).",
    "Maintain a WIP limit per cycle; defer rather than overcommit.",
    "Explicitly record trade-offs when de-scoping; do not silently drop commitments.",
]

DEFINITION_OF_DONE = [
    "Roadmap document generated and saved under outputs/ with correct filename",
    "Contains: scope boundaries, subtopic list, prioritization policy, Definition of Done, and 20-cycle milestone outline",
    "Milestones are specific (deliverables stated), ordered (Cycle 1..20), and testable (clear completion signals)",
    "Document is readable Markdown with headings and lists; no placeholder or TODO text",
    "Script can be run repeatedly and overwrites the output deterministically (aside from date stamp)",
]

MILESTONES = [
    (1, "Kickoff & alignment", ["Confirm goals, non-goals, and stakeholders", "Create initial problem statement and success metrics draft"]),
    (2, "Discovery plan", ["Draft research questions", "Schedule/prepare interviews or surveys", "Define data to collect"]),
    (3, "User needs & pain points", ["Synthesize findings into needs list", "Capture key constraints and edge cases"]),
    (4, "Scope boundaries v1", ["Document in-scope/out-of-scope/assumptions", "Identify major dependencies and owners"]),
    (5, "Requirements v1", ["Draft functional requirements", "Draft non-functional requirements (performance, reliability, security)"]),
    (6, "Risk register", ["Enumerate risks with probability/impact", "Define mitigations and triggers", "Set review cadence"]),
    (7, "Conceptual architecture", ["High-level components and data flow", "Identify integration points and interfaces"]),
    (8, "Prioritization framework", ["Define scoring rubric and decision process", "Backlog skeleton aligned to milestones"]),
    (9, "Prototype / proof of concept", ["Validate key technical assumptions", "Document findings and implications"]),
    (10, "MVP definition", ["Select MVP scope", "Define acceptance criteria and demo narrative"]),
    (11, "Quality strategy", ["Testing approach, review gates, and release criteria", "Definition of Done for deliverables"]),
    (12, "Operational readiness plan", ["Monitoring/logging expectations", "Runbook outline", "Incident/rollback plan"]),
    (13, "Security & privacy review", ["Threat model at high level", "Data handling rules and access controls"]),
    (14, "Implementation plan v1", ["Break MVP into increment deliverables", "Confirm dependencies and sequencing"]),
    (15, "Beta planning", ["Beta cohort definition", "Feedback channels and metrics instrumentation plan"]),
    (16, "Documentation plan", ["User/admin docs outline", "Developer notes and handoff checklist"]),
    (17, "Release readiness", ["Go/no-go checklist", "Finalize acceptance tests and operational checks"]),
    (18, "Beta release & learn", ["Conduct beta release", "Collect feedback and measure success metrics"]),
    (19, "Iteration & hardening", ["Address top beta issues", "Performance/reliability improvements as needed"]),
    (20, "V1 launch & retrospective", ["Launch v1 (or readiness decision)", "Retrospective and roadmap v2 inputs captured"]),
]

def render_markdown(filename: str) -> str:
    today = date.today().isoformat()
    lines: list[str] = []
    lines.append(f"# Roadmap: Scope, Success Criteria, and 20-Cycle Milestones\n")
    lines.append(f"_Generated: {today}_\n")
    lines.append("## Scope boundaries\n")
    for title, items in SCOPE_BOUNDARIES:
        lines.append(f"### {title}\n")
        for it in items:
            lines.append(f"- {it}")
        lines.append("")
    lines.append("## Subtopic list\n")
    for s in SUBTOPICS:
        lines.append(f"- {s}")
    lines.append("")
    lines.append("## Prioritization policy\n")
    for p in PRIORITIZATION_POLICY:
        lines.append(f"- {p}")
    lines.append("")
    lines.append("## Definition of Done\n")
    for d in DEFINITION_OF_DONE:
        lines.append(f"- {d}")
    lines.append("")
    lines.append("## 20-cycle milestone outline\n")
    lines.append("| Cycle | Milestone | Deliverables (completion signals) |")
    lines.append("|---:|---|---|")
    for cycle, title, deliverables in MILESTONES:
        bullets = "<br>".join(f"- {x}" for x in deliverables)
        lines.append(f"| {cycle} | {title} | {bullets} |")
    lines.append("")
    lines.append("## Notes\n")
    lines.append("- Cycles are intended to be time-boxed; adjust scope per feedback and capacity.")
    lines.append("- Reprioritize using the policy above whenever new information changes impact, confidence, urgency, or effort.")
    lines.append("")
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a roadmap markdown document into outputs/.")
    parser.add_argument("--output", default=DEFAULT_FILENAME, help="Output markdown filename (stored under outputs/).")
    args = parser.parse_args()

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS_DIR / Path(args.output).name

    md = render_markdown(out_path.name)
    out_path.write_text(md, encoding="utf-8")
    print(str(out_path))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
