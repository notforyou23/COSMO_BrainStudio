from __future__ import annotations
import os
os.chdir(r'/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')


from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence
from pathlib import Path


@dataclass
class PlanInputs:
    project_name: str = "Provenance-Aware Primary-Source Psychology Protocols"
    scope: str = (
        "Community-endorsed protocols (checklists, metadata schemas) and lightweight "
        "software/plugins to detect and annotate edition/translation provenance, variant "
        "pagination/paragraph markers, and public-domain repository citations for primary-source "
        "psychology scholarship."
    )
    target_corpora: Sequence[str] = field(
        default_factory=lambda: [
            "Foundational works in experimental psychology (19th–early 20th c.)",
            "Public-domain monographs and journal articles in psychology and adjacent fields",
            "Canonical translations and multi-edition textbooks with known variants",
        ]
    )
    repositories: Sequence[str] = field(
        default_factory=lambda: [
            "Internet Archive",
            "HathiTrust (public-domain items)",
            "Project Gutenberg",
            "Wikimedia Commons / Wikisource",
            "Local institutional repositories",
        ]
    )
    stakeholder_groups: Sequence[str] = field(
        default_factory=lambda: [
            "Primary-source psychology scholars (historians, methodologists, translators)",
            "Librarians/archivists and special collections",
            "Repository operators / digital scholarship staff",
            "Publishers/editors for critical editions",
            "Tooling maintainers (Zotero, Pandoc/Quarto, JATS/TEI communities)",
            "Research integrity and reproducibility advocates",
        ]
    )
    output_format: str = "markdown"
    acceptance_prefix: str = "AC"


def _md_list(items: Iterable[str], ordered: bool = False) -> str:
    items = list(items)
    if not items:
        return ""
    if ordered:
        return "\n".join(f"{i+1}. {it}" for i, it in enumerate(items))
    return "\n".join(f"- {it}" for it in items)


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    h = "| " + " | ".join(headers) + " |"
    s = "| " + " | ".join(["---"] * len(headers)) + " |"
    r = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join([h, s, r]) if rows else "\n".join([h, s])


def _ac(idx: int, prefix: str) -> str:
    return f"{prefix}-{idx:03d}"


def generate_plan_md(inputs: Optional[PlanInputs] = None) -> str:
    inp = inputs or PlanInputs()
    acn = 1

    def ac(text: str) -> str:
        nonlocal acn
        tag = _ac(acn, inp.acceptance_prefix)
        acn += 1
        return f"[{tag}] {text}"

    md: List[str] = []
    md.append(f"# {inp.project_name}")
    md.append(f"_Generated: {date.today().isoformat()}_")
    md.append("## Mission summary")
    md.append(inp.scope)

    md.append("## 1) Stakeholder engagement plan")
    md.append("### 1.1 Stakeholders in scope")
    md.append(_md_list(inp.stakeholder_groups))
    md.append("### 1.2 Governance and decision-making")
    md.append(
        _md_list(
            [
                "Create a Steering Group (6–10 people) with balanced representation across stakeholder groups.",
                "Create two Working Groups: (A) Protocols & Schemas, (B) Tools & Integrations.",
                "Define a lightweight RFC process: proposal → review → pilot → endorsement → versioned release.",
                "Adopt a code of conduct and conflict-of-interest disclosure for endorsers.",
            ]
        )
        + "\n\n"
        + _md_list(
            [
                ac("Steering Group roster published with roles, terms, and COI statements."),
                ac("RFC process documented with timelines and voting/consensus rules."),
                ac("Endorsement criteria explicitly require pilot evidence and audit results."),
            ]
        )
    )
    md.append("### 1.3 Engagement activities (deliverables-driven)")
    md.append(
        _md_list(
            [
                "Discovery interviews (n=20–30) to map current citation/provenance practices and pain points.",
                "Protocol design workshops (3 sessions) to co-author checklists and schema fields.",
                "Tooling design sprints (2 sprints) to align detection/annotation outputs with workflows.",
                "Public comment period (30–45 days) on draft protocol package (v0.9).",
                "Endorsement roundtable to finalize v1.0 with sign-on statements.",
            ],
            ordered=True,
        )
        + "\n\n"
        + _md_list(
            [
                ac("Interview guide + anonymized thematic summary published; requirements trace to themes."),
                ac("Workshop outputs include edited checklist and schema diffs with rationale."),
                ac("Public comment log with dispositions (accept/reject/defer) is published."),
            ]
        )
    )

    md.append("## 2) Protocol package (checklists + metadata schemas)")
    md.append("### 2.1 Protocols to produce (community-endorsed)")
    md.append(
        _md_list(
            [
                "**Edition/Translation Provenance Checklist**: minimum fields and verification steps.",
                "**Variant Marker Checklist**: pagination, paragraph/section markers, and alignment rules.",
                "**Repository Citation Checklist**: durable identifiers, access dates, and rights/public-domain signals.",
            ]
        )
        + "\n\n"
        + _md_list(
            [
                ac("Each checklist has: purpose, applicability, required/optional items, examples, and failure modes."),
                ac("Each checklist includes a ‘minimum-compliance’ profile for low-burden adoption."),
            ]
        )
    )
    md.append("### 2.2 Metadata schema requirements")
    schema_rows = [
        ["edition.provenance", "Publisher, year, edition statement, printings; verify from title page/colophon"],
        ["translation.provenance", "Translator(s), source language, basis edition, notes on modernization"],
        ["source.identifiers", "DOI/Handle/ARK/IA ID/Hathi ID; OCLC/ISBN when available"],
        ["repository.citation", "Repository name, stable URL, access date, file checksum if captured"],
        ["variant.markers", "Page mapping strategy; paragraph/section anchor scheme; alignment confidence"],
        ["rights.pd_signal", "Public-domain basis (jurisdiction/date/notice) and repository rights statement"],
        ["extraction.pipeline", "OCR source, version, post-correction steps; segmentation method"],
    ]
    md.append(
        "Target outputs:\n"
        + _md_list(
            [
                "JSON Schema (machine validation)",
                "YAML profile (human-authored frontmatter)",
                "Crosswalks: CSL, BibTeX, TEI, JATS, and Zotero Extra fields mapping",
            ]
        )
        + "\n\n"
        + _md_table(["Field/Concept", "Normative requirement"], schema_rows)
        + "\n\n"
        + _md_list(
            [
                ac("Provide JSON Schema with examples that validate under CI."),
                ac("Publish crosswalk tables with at least CSL + TEI + JATS coverage for core fields."),
                ac("Define required vs optional fields and acceptable value formats (IDs, dates, languages)."),
            ]
        )
    )

    md.append("## 3) Lightweight software/plugins (detect + annotate)")
    md.append("### 3.1 Functional requirements")
    md.append(
        _md_list(
            [
                "Detect edition/translation signals from PDFs/EPUBs: title page patterns, imprint lines, translator credits.",
                "Extract and normalize stable repository identifiers and URLs; recommend canonical citation strings.",
                "Generate variant anchors: page-image → logical page mapping; paragraph/section IDs; alignment hints.",
                "Emit provenance annotations as: (a) YAML/JSON sidecar, (b) embedded TEI/JATS fragments, (c) CSL JSON notes.",
                "Support round-trip editing (human corrections) with deterministic merges.",
            ]
        )
        + "\n\n"
        + _md_list(
            [
                ac("Tooling outputs are schema-valid and include provenance confidence scores + evidence snippets."),
                ac("At least one plugin path: Zotero translator/connector enhancement OR Pandoc/Quarto filter."),
                ac("Provide ‘dry-run’ mode that reports what would be annotated without modifying sources."),
            ]
        )
    )
    md.append("### 3.2 Non-functional requirements")
    md.append(
        _md_list(
            [
                "Privacy: no upload required by default; local-first processing with optional opt-in telemetry.",
                "Reproducibility: deterministic outputs given same inputs; record tool versions and hashes.",
                "Interoperability: stable IDs, UTF-8, language tags (BCP 47), and open licenses for protocols.",
                "Usability: defaults + progressive disclosure; explainable warnings and evidence display.",
                "Maintainability: modular parsers; test fixtures from multiple repositories and edition types.",
            ]
        )
        + "\n\n"
        + _md_list(
            [
                ac("All outputs include tool/version metadata and input file hash in a standard block."),
                ac("A conformance test suite (fixtures + expected JSON) is published and runnable in CI."),
            ]
        )
    )

    md.append("## 4) Validation and evaluation studies")
    md.append("### 4.1 Survey study (perceived burden, clarity, and trust)")
    md.append(
        _md_list(
            [
                "Population: scholars, librarians, and digital scholarship practitioners (target n=150–250).",
                "Design: mixed Likert + scenario tasks comparing current practice vs protocol-driven practice.",
                "Outcomes: perceived clarity, time cost, willingness to adopt, trust in provenance claims, and tooling usability.",
                "Analysis: pre-registered hypotheses; subgroup comparisons by role and experience; open instrument release.",
            ]
        )
        + "\n\n"
        + _md_list(
            [
                ac("Survey instrument and codebook are published; includes at least 3 realistic citation/provenance scenarios."),
                ac("Define adoption intent KPI (e.g., ≥60% ‘likely/very likely’ to use minimum profile within 6 months)."),
            ]
        )
    )
    md.append("### 4.2 Audit study (accuracy and completeness of annotations)")
    md.append(
        _md_list(
            [
                "Sample: stratified corpus of 200 items across repositories, decades, and known multi-edition/translation cases.",
                "Gold standard: expert adjudication of edition/translation and marker correctness (double-coded, resolve disputes).",
                "Compare: baseline (manual typical practice) vs protocol + tooling assisted workflow.",
                "Metrics: precision/recall for detected provenance fields; marker alignment accuracy; citation completeness; time-on-task.",
                "Report: error taxonomy (OCR artifacts, ambiguous imprint, repository metadata conflicts) with mitigations.",
            ]
        )
        + "\n\n"
        + _md_list(
            [
                ac("Audit achieves inter-rater reliability target (e.g., Cohen’s κ ≥ 0.75 on key fields)."),
                ac("Tool-assisted workflow improves citation completeness and reduces critical provenance errors vs baseline."),
                ac("Publish anonymized audit dataset (where permissible) + full methods and analysis scripts."),
            ]
        )
    )

    md.append("## 5) Phased rollout plan with measurable milestones")
    rollout = [
        ("Phase 0 (0–2 mo)", "Set up governance, interview study, initial requirements", "Roster, RFC process, interview synthesis"),
        ("Phase 1 (2–5 mo)", "Draft protocols + schema v0.9; prototype plugins/filters", "Draft package, schema + examples, prototype"),
        ("Phase 2 (5–8 mo)", "Pilots with 3–5 labs/libraries; run survey", "Pilot reports, revised v1.0 candidates"),
        ("Phase 3 (8–12 mo)", "Audit study + endorsement roundtable; release v1.0", "Validated v1.0, conformance suite, endorsements"),
        ("Phase 4 (12–18 mo)", "Scale adoption + integrations + maintenance", "More connectors, training materials, v1.1 based on issues"),
    ]
    md.append(_md_table(["Phase", "Goal", "Exit artifacts"], rollout))
    md.append(
        _md_list(
            [
                ac("At least 5 independent organizations sign the v1.0 endorsement statement."),
                ac("Adoption KPI: ≥500 protocol downloads OR ≥200 active plugin installs within 6 months of v1.0."),
                ac("Impact KPI: ≥30 published works cite the protocol package within 12 months."),
                ac("Maintenance KPI: <30 days median time-to-triage for reported issues; quarterly minor releases."),
            ]
        )
    )

    md.append("## 6) Traceability matrix (requirements → evidence)")
    md.append(
        _md_table(
            ["Category", "Evidence artifact", "Acceptance criteria coverage"],
            [
                ["Engagement", "Interview synthesis + comment log", "AC-001..AC-006"],
                ["Protocols/Schemas", "Checklists + JSON Schema + crosswalks", "AC-007..AC-011"],
                ["Tooling", "Plugin/filter + conformance tests + fixtures", "AC-012..AC-016"],
                ["Validation", "Survey prereg + audit dataset + analysis", "AC-017..AC-021"],
                ["Rollout", "Endorsements + adoption dashboard", "AC-022..AC-025"],
            ],
        )
    )

    return "\n\n".join(s for s in md if s.strip()) + "\n"


def write_plan(output_path: str | Path, inputs: Optional[PlanInputs] = None) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_plan_md(inputs), encoding="utf-8")
    return out


if __name__ == "__main__":
    # Minimal manual entrypoint for local testing
    default_out = Path.cwd() / "protocol_plan.md"
    write_plan(default_out)
    print(str(default_out.resolve()))
