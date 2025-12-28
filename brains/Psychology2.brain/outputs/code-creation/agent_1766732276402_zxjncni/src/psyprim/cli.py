"""psyprim CLI: generate standardized workflows/checklists/instruments + detect primary-source citation signals."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _write_out(obj: Any, out: Optional[Path]) -> None:
    s = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(s + "\n", encoding="utf-8")
    else:
        print(s)


def _today() -> str:
    return str(date.today())


@dataclass
class DetectionHit:
    feature: str
    pattern: str
    count: int
    examples: List[str]


def _snips(text: str, spans: List[Tuple[int, int]], window: int = 60, max_n: int = 5) -> List[str]:
    out: List[str] = []
    for a, b in spans[:max_n]:
        lo, hi = max(0, a - window), min(len(text), b + window)
        out.append(text[lo:hi].replace("\n", " ").strip())
    return out


def detect_primary_source_signals(text: str) -> Dict[str, Any]:
    features: List[Tuple[str, str]] = [
        ("edition_provenance", r"\b(?:ed\.|eds\.|edition|revised\s+edition|rev\.|2nd\s+ed\.|3rd\s+ed\.|vol\.|volume)\b"),
        ("translation_provenance", r"\b(?:trans\.|translated\s+by|translation\s+of|translator|tr\.)\b"),
        ("variant_pagination", r"\b(?:p\.|pp\.|pages?)\s*\d+(?:\s*[-–]\s*\d+)?\b"),
        ("variant_pagination", r"\b(?:pagination|page\s+numbers?\s+vary|different\s+pagination|numbering\s+differs)\b"),
        ("repository_citation", r"\b(?:doi\s*:\s*10\.|jstor\b|hathitrust\b|internet\s+archive\b|archive\.org\b|worldcat\b|oclc\b|proquest\b|gale\b|psycinfo\b|hdl\.handle\.net\b|zenodo\b|osf\.io\b)"),
        ("primary_source_cue", r"\b(?:original\s+publication|first\s+published|facsimile|reprint|collected\s+works|complete\s+works|critical\s+edition)\b"),
    ]
    lower = text.lower()
    hits: Dict[str, DetectionHit] = {}
    for feat, pat in features:
        rx = re.compile(pat, re.IGNORECASE)
        spans = [(m.start(), m.end()) for m in rx.finditer(lower)]
        key = f"{feat}:{pat}"
        if spans:
            hits[key] = DetectionHit(feat, pat, len(spans), _snips(text, spans))
    by_feature: Dict[str, Dict[str, Any]] = {}
    for h in hits.values():
        cur = by_feature.setdefault(h.feature, {"count": 0, "patterns": []})
        cur["count"] += h.count
        cur["patterns"].append({"pattern": h.pattern, "count": h.count, "examples": h.examples})
    score = sum(1 for f in ("edition_provenance", "translation_provenance", "variant_pagination", "repository_citation") if f in by_feature)
    return {"score_0_4": score, "features": by_feature}
def generate_workflow() -> Dict[str, Any]:
    return {
        "schema": "psyprim.workflow.v1",
        "generated_on": _today(),
        "name": "Primary-source scholarship workflow (psychology)",
        "steps": [
            {"id": "scope", "title": "Define primary-source target", "outputs": ["target_work", "target_edition_or_translation"]},
            {"id": "locate", "title": "Locate authoritative manifestation", "checks": ["edition/translation provenance", "repository identifier", "scan completeness"]},
            {"id": "verify", "title": "Verify citation-level details", "fields": ["author", "year", "title", "edition", "translator", "publisher", "place", "series", "volume", "page span"]},
            {"id": "capture", "title": "Capture stable access info", "fields": ["DOI/handle", "archive URL", "WorldCat/OCLC", "library call number", "repository name"]},
            {"id": "quote", "title": "Quote and contextualize", "fields": ["exact page/section", "variant pagination note", "translation note"]},
            {"id": "report", "title": "Report with reproducibility appendix", "outputs": ["metadata checklist", "bibliography entries", "audit trail"]},
        ],
        "recommended_repositories": ["HathiTrust", "Internet Archive", "JSTOR", "WorldCat", "PsycINFO", "institutional repositories"],
    }


def generate_metadata_checklist() -> Dict[str, Any]:
    return {
        "schema": "psyprim.metadata_checklist.v1",
        "generated_on": _today(),
        "required": [
            "work_title", "primary_author", "original_year", "cited_year",
            "edition_statement", "translator(s)", "editor(s)", "publisher", "place",
            "volume/issue (if applicable)", "page_span_or_locator", "stable_identifier (DOI/handle/URL)",
            "repository_name", "access_date", "notes_on_variant_pagination",
        ],
        "optional": ["series", "call_number", "scan_quality_notes", "OCR_source", "language_of_text", "reprint_series_info"],
        "validation_rules": [
            {"field": "stable_identifier (DOI/handle/URL)", "rule": "must be present for digital sources; prefer DOI/handle when available"},
            {"field": "edition_statement", "rule": "must specify edition/printing when citing primary historical texts"},
            {"field": "page_span_or_locator", "rule": "must include page range or section/paragraph locator; note when pagination differs across editions"},
            {"field": "translator(s)", "rule": "required if not citing original-language edition"},
        ],
    }


def generate_instruments() -> Dict[str, Any]:
    return {
        "schema": "psyprim.instruments.v1",
        "generated_on": _today(),
        "survey": {
            "purpose": "Assess researcher practices + perceived barriers for primary-source use/citation in psychology.",
            "design": {"mode": "online", "sampling": "psychology researchers/graduate students; stratify by subfield + career stage"},
            "measures": [
                {"id": "ps_usage", "prompt": "In your last 3 papers, how often did you consult primary sources?", "type": "Likert_5"},
                {"id": "ps_citation_detail", "prompt": "How often do you record edition/translation and repository identifiers?", "type": "Likert_5"},
                {"id": "barriers", "prompt": "Select top barriers (access, time, language, uncertainty about editions, etc.).", "type": "multi_select"},
                {"id": "confidence", "prompt": "Confidence in identifying authoritative editions/translations.", "type": "Likert_5"},
                {"id": "tool_interest", "prompt": "Interest in lightweight detection/checklist tools.", "type": "Likert_5"},
            ],
            "outputs": ["de-identified CSV", "codebook", "pre-registered hypotheses"],
        },
        "audit_study": {
            "purpose": "Audit published psychology papers for primary-source citation completeness + reproducibility.",
            "design": {
                "sampling_frame": "journals in history/theory + methods + general psychology",
                "sample_size_guidance": "n≈100-300 papers; stratified by year and journal",
                "unit_of_analysis": "each primary-source citation instance",
            },
            "coding": {
                "variables": [
                    "primary_source_present (y/n)", "edition_statement_present (y/n)",
                    "translation_provenance_present (y/n)", "page_locator_present (y/n)",
                    "repository_identifier_present (y/n)", "sufficient_to_retrieve (y/n)",
                ],
                "reliability": {"double_code_fraction": 0.2, "metric": "Cohen_kappa"},
            },
            "outputs": ["coding spreadsheet schema", "interrater reliability report", "summary tables"],
        },
    }
def generate_roadmap() -> Dict[str, Any]:
    return {
        "schema": "psyprim.roadmap.v1",
        "generated_on": _today(),
        "mission": "Standardized workflows, metadata checklists, and lightweight detection tools for primary-source scholarship in psychology.",
        "workstreams": [
            {"name": "Standards", "deliverables": ["workflow JSON", "metadata checklist JSON", "reporting templates"], "validation": ["expert review", "pilot users"]},
            {"name": "Measurement", "deliverables": ["survey instrument", "audit coding guide"], "study_designs": ["survey", "audit study"], "analysis": ["descriptives", "predictors of completeness", "IRR (kappa)"]},
            {"name": "Detection tooling", "deliverables": ["CLI detector", "feature library"], "features": ["edition/translation provenance", "variant pagination", "repository citations"]},
            {"name": "Repositories + data", "sources": ["Crossref DOI", "WorldCat/OCLC", "HathiTrust/IA metadata", "journal PDFs/text"], "storage": ["OSF/Zenodo for instruments + codebooks"]},
        ],
        "specialist_agents": [
            {"role": "Psychology methods lead", "tasks": ["survey design", "audit protocol", "preregistration text"]},
            {"role": "Bibliographic metadata specialist", "tasks": ["checklist fields", "edition/translation edge cases", "repository identifier standards"]},
            {"role": "NLP/IR engineer", "tasks": ["regex/heuristics", "evaluation harness", "false-positive analysis"]},
            {"role": "Statistician", "tasks": ["power guidance", "IRR plan", "analysis scripts spec"]},
            {"role": "Research librarian", "tasks": ["repository coverage", "retrievability criteria", "sampling frame support"]},
        ],
        "validation_plan": {
            "survey": {"outcomes": ["current practice rates", "barriers", "tool acceptance"], "target_n": ">=200"},
            "audit": {"outcomes": ["citation completeness", "retrievability"], "target_units": ">=300 citations", "IRR": "kappa>=0.7"},
            "detector_eval": {"gold_labels": "subset of audit-coded citations", "metrics": ["precision", "recall", "error taxonomy"]},
        },
    }


def _cmd_generate(kind: str, out: Optional[Path]) -> None:
    gen = {"workflow": generate_workflow, "checklist": generate_metadata_checklist, "instruments": generate_instruments, "roadmap": generate_roadmap}[kind]
    _write_out(gen(), out)


def _cmd_detect(paths: List[Path], out: Optional[Path]) -> None:
    results = {"schema": "psyprim.detection_results.v1", "generated_on": _today(), "files": []}
    for p in paths:
        t = _read_text(p)
        det = detect_primary_source_signals(t)
        results["files"].append({"path": str(p), "bytes": len(t.encode("utf-8", "ignore")), **det})
    _write_out(results, out)
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="psyprim", description="Primary-source scholarship workflow generator + lightweight citation-signal detection.")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate JSON artifacts (workflow/checklist/instruments/roadmap).")
    g.add_argument("kind", choices=["workflow", "checklist", "instruments", "roadmap"])
    g.add_argument("-o", "--out", type=Path, default=None, help="Write output JSON to file (default: stdout).")

    d = sub.add_parser("detect", help="Detect primary-source citation signals in text files.")
    d.add_argument("paths", nargs="+", type=Path, help="One or more UTF-8-ish text files to scan.")
    d.add_argument("-o", "--out", type=Path, default=None, help="Write output JSON to file (default: stdout).")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "generate":
        _cmd_generate(args.kind, args.out)
    elif args.cmd == "detect":
        _cmd_detect(args.paths, args.out)
    else:
        raise SystemExit(f"Unknown command: {args.cmd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
