from __future__ import annotations
from pathlib import Path
import re

BASE_DIR = Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution")
OUT_PATH = BASE_DIR / "outputs" / "CASE_STUDY_RUBRIC.md"

PROJECT_CONTEXT = {
  "workflow_principle": "Standardized, schema-driven workflow for collecting case studies using shared templates and a single intake index.",
  "equity_risk_notes": [
    "Measurement design can become a hidden equity lever (and risk).",
    "A self-reinforcing selection loop can emerge when institutions rely on cheap, high-velocity proxies."
  ],
  "media_expectations": [
    "Prefer authoritative sources: official org pages, regulators, courts, academic publishers, reputable investigative outlets.",
    "Archive links when possible; provide publication date and publisher."
  ]
}

TAXONOMY = {
  "theme": ["equity", "measurement", "governance", "accountability", "transparency", "privacy", "safety", "access", "labor", "education", "health", "finance", "justice"],
  "sector": ["public_sector", "private_sector", "nonprofit", "education", "healthcare", "finance", "employment", "housing", "criminal_justice", "consumer"],
  "geography": ["global", "north_america", "latam", "europe", "mena", "sub_saharan_africa", "south_asia", "east_asia", "oceania"],
  "actor": ["government", "company", "ngo", "community", "researchers", "media", "court_regulator"],
  "method": ["policy", "product", "procurement", "audit", "investigation", "litigation", "research", "organizing"],
  "outcome": ["harm", "benefit", "mixed", "policy_change", "product_change", "accountability_action", "no_change"],
  "risk": ["selection_bias", "proxy_measurement", "feedback_loop", "rights_ambiguity", "surveillance", "discrimination"],
  "media_type": ["report", "dataset", "court_filing", "regulatory_action", "press_release", "news", "academic_paper", "blog"],
  "rights": ["public_domain", "cc_by", "cc_by_sa", "cc_by_nc", "all_rights_reserved", "permission_granted", "unknown"]
}

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")

def tag(cat: str, value: str) -> str:
    c = slugify(cat)
    v = slugify(value)
    if c not in TAXONOMY:
        raise ValueError(f"Unknown taxonomy category: {cat}")
    if v not in TAXONOMY[c]:
        raise ValueError(f"Unknown taxonomy value for {cat}: {value} -> {v}")
    return f"{c}:{v}"

def md_table(headers, rows) -> str:
    h = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([h, sep] + body)

def build_md() -> str:
    lines = []
    lines += ["# CASE STUDY RUBRIC", "", "Purpose: enable consistent intake, scoring, and tagging of case studies using a single schema-driven workflow.", ""]
    lines += ["## Scope", ""]
    lines += [f"- Workflow principle: {PROJECT_CONTEXT['workflow_principle']}",
              "- A case study is eligible if it describes a real-world intervention, deployment, decision, or incident with traceable evidence and clear actors.",
              ""]
    lines += ["## Inclusion criteria (must meet all)", ""]
    lines += [
        "- **Real-world specificity:** names at least one organization/actor, place (or jurisdiction), and time window.",
        "- **Mechanism + evidence:** explains what happened and why it happened; includes at least **2** authoritative supporting URLs.",
        "- **Outcome described:** documents harms/benefits or policy/product/accountability outcomes, including uncertainty where applicable.",
        "- **Taggable to taxonomy:** can be tagged with required taxonomy categories (see Tagging Rules).",
        "- **Rights clarity for media:** any included media asset (image/video/document excerpt) has a known rights status or clear lawful basis for use.",
        ""
    ]
    lines += ["## Exclusion criteria (any one disqualifies)", ""]
    lines += [
        "- **Purely hypothetical** scenarios with no real-world anchor.",
        "- **Unverifiable claims** without authoritative sources or traceable primary/secondary reporting.",
        "- **Marketing-only narratives** with no independent corroboration and no concrete outcomes.",
        "- **Rights-unclear media** that requires copying/rehosting without permission (linking is fine).",
        "- **Duplicate** of an existing case study with no new evidence, angle, or updated outcomes.",
        ""
    ]

    lines += ["## Scoring rubric (1–5 per dimension)", ""]
    lines += ["Score each dimension from 1 (weak) to 5 (strong). Use the notes to justify scores in the intake record.", ""]
    rows = [
        ["Impact", "1: localized/minor or speculative; 3: material impact on a program or population; 5: large-scale, systemic, or precedent-setting."],
        ["Relevance to themes", "1: peripheral; 3: clearly connects to ≥1 theme; 5: central exemplar for multiple themes or a canonical mechanism."],
        ["Authoritative media URLs", "1: none/low quality; 3: 2–3 solid sources; 5: multiple authoritative sources incl. primary docs (court/regulator/official/peer-reviewed)."],
        ["Rights clarity", "1: unknown/unsafe to reuse; 3: link-only OK but reuse unclear; 5: explicit license/permission/public-domain/clear fair-use rationale documented."]
    ]
    lines += [md_table(["Dimension", "What to consider"], rows), ""]
    lines += ["### Suggested overall score", ""]
    lines += [
        "Compute a simple weighted score if desired:",
        "- Impact **35%**",
        "- Relevance to themes **30%**",
        "- Authoritative media URLs **20%**",
        "- Rights clarity **15%**",
        "",
        "Overall = 0.35*Impact + 0.30*Relevance + 0.20*Media + 0.15*Rights (round to 1 decimal).",
        ""
    ]

    lines += ["## Evidence and media URL rules", ""]
    lines += [
        "- Provide **at least 2 URLs**; prefer at least **1** primary/official source when feasible.",
        "- Record publisher, date, and jurisdiction for each key source when available.",
        "- Avoid link rot: include stable permalinks; add archive links when possible.",
        "- Media assets: do not embed/rehost unless rights are clear; linking to the source is acceptable.",
        ""
    ]
    lines += ["Authoritative sources commonly include:", ""]
    lines += [
        "- Official government/regulator/court documents, filings, decisions, enforcement actions.",
        "- Organization press releases when paired with independent reporting or primary documentation.",
        "- Peer-reviewed papers, academic publishers, institutional repositories.",
        "- Reputable investigative outlets with transparent sourcing.",
        ""
    ]

    lines += ["## Rights clarity rules", ""]
    lines += [
        "- Tag rights using the `rights:*` taxonomy values (see Taxonomy section).",
        "- Acceptable high-clarity cases include: public domain, Creative Commons, explicit written permission, or well-documented fair-use rationale (quote limits, attribution, transformative purpose).",
        "- If rights are unknown, default to **link-only** and score Rights clarity ≤3.",
        ""
    ]

    lines += ["## Tagging rules (taxonomy-mapped)", ""]
    lines += ["Tags must use the format `category:value` and must match the approved taxonomy values below.", ""]
    required = ["theme", "sector", "geography", "actor", "outcome"]
    optional = ["method", "risk", "media_type", "rights"]
    lines += ["### Required tags (minimum)", ""]
    lines += ["- " + ", ".join([f"`{c}:*`" for c in required]), ""]
    lines += ["### Optional but recommended tags", ""]
    lines += ["- " + ", ".join([f"`{c}:*`" for c in optional]), ""]
    lines += [
        "Rules:",
        "- Use **1–3** `theme:*` tags; include `theme:equity` when disparate impact, access, or fairness is material.",
        "- Include at least **1** `risk:*` tag when mechanisms suggest systemic failure modes (e.g., selection bias, proxy measurement, feedback loops).",
        "- Choose the **closest** geographic region; if multi-region, include `geography:global` plus the most affected region.",
        "- If rights are unknown, set `rights:unknown` and avoid rehosting media.",
        ""
    ]

    lines += ["### Taxonomy (approved values)", ""]
    for cat in sorted(TAXONOMY.keys()):
        vals = ", ".join([f"`{tag(cat, v).split(':',1)[1]}`" for v in TAXONOMY[cat]])
        lines += [f"- **{cat}**: {vals}"]
    lines += [""]

    lines += ["## Examples", ""]
    ex_tags = [
        tag("theme", "equity"), tag("theme", "measurement"),
        tag("risk", "proxy_measurement"), tag("risk", "feedback_loop"),
        tag("sector", "public_sector"), tag("actor", "government"),
        tag("geography", "north_america"), tag("method", "audit"),
        tag("outcome", "policy_change"), tag("media_type", "report"),
        tag("rights", "unknown")
    ]
    lines += ["Example tag set:", "", "- " + "\n- ".join([f"`{t}`" for t in ex_tags]), ""]
    lines += ["Notes on common mechanisms to capture:", ""]
    lines += [f"- {PROJECT_CONTEXT['equity_risk_notes'][0]}", f"- {PROJECT_CONTEXT['equity_risk_notes'][1]}", ""]
    lines += ["---", "", "Generated by `scripts/create_case_study_rubric.py`.", ""]
    return "\n".join(lines)

def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_md(), encoding="utf-8")
    print(f"OK:WROTE:{OUT_PATH}")

if __name__ == "__main__":
    main()
