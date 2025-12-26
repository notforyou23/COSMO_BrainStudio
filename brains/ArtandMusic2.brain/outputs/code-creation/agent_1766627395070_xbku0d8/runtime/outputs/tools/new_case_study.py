#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"['’]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "untitled"


def build_stub(slug: str, title: str, org: str | None, author: str | None) -> dict:
    t = now_iso()
    return {
        "schema": "CASE_STUDY",
        "schema_version": "0.1.0",
        "id": slug,
        "slug": slug,
        "title": title,
        "one_liner": f"A brief case study about {title}.",
        "summary": (
            f"This is an auto-generated starter record for the case study “{title}”. "
            "Replace the stub text with a concise description of the setting, intervention, and outcomes."
        ),
        "tags": ["case-study", "stub"],
        "status": "draft",
        "created_at": t,
        "updated_at": t,
        "authors": [a for a in [author] if a],
        "organization": org or "",
        "context": {
            "domain": "",
            "location": "",
            "timeframe": "",
            "stakeholders": [],
        },
        "problem": {
            "statement": "Describe the problem being addressed.",
            "constraints": [],
            "baseline": "What was happening before the intervention?",
        },
        "intervention": {
            "overview": "What was done? Summarize the intervention.",
            "implementation": "How was it implemented? Include process, tooling, and decision points.",
            "resources": [],
        },
        "measurement": {
            "primary_outcomes": [],
            "metrics": [],
            "design_notes": "Describe how outcomes were measured and any known biases or limitations.",
        },
        "results": {
            "outcomes": "Summarize observed outcomes.",
            "evidence": [],
            "unintended_effects": [],
        },
        "limitations": [],
        "replication": {
            "what_to_copy": [],
            "what_to_avoid": [],
            "prerequisites": [],
        },
        "sources": {
            "bibliography_file": "sources.bib",
            "citations": [],
        },
        "rights": {
            "notes_file": "rights.md",
            "license": "",
            "attribution": "",
        },
    }


def write_text(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="new_case_study",
        description="Create a new case study stub under runtime/outputs/case_studies/<slug>/",
    )
    ap.add_argument("title", help="Case study title")
    ap.add_argument("--slug", help="Directory slug (defaults to a slugified title)")
    ap.add_argument("--org", default="", help="Organization / lab / team (optional)")
    ap.add_argument("--author", default="", help="Primary author name (optional)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing files if present")
    args = ap.parse_args()

    slug = slugify(args.slug) if args.slug else slugify(args.title)
    title = args.title.strip()

    outputs_dir = Path(__file__).resolve().parents[1]
    case_dir = outputs_dir / "case_studies" / slug
    case_json = case_dir / "case_study.json"
    bib_path = case_dir / "sources.bib"
    rights_path = case_dir / "rights.md"

    stub = build_stub(slug, title, args.org.strip() or None, args.author.strip() or None)
    write_text(case_json, json.dumps(stub, ensure_ascii=False, indent=2) + "\n", args.force)

    bib = (
        f"@misc{{{slug},\n"
        f"  title        = {{{title}}},\n"
        f"  author       = {{{args.author.strip() or 'Unknown'}}},\n"
        f"  howpublished = {{Unpublished case study stub}},\n"
        f"  year         = {{{datetime.now().year}}},\n"
        f"  note         = {{Replace with authoritative sources and citations.}}\n"
        f"}}\n"
    )
    write_text(bib_path, bib, args.force)

    rights = (
        f"# Rights & Licensing\n\n"
        f"Case study: **{title}** (`{slug}`)\n\n"
        f"## License\n\n"
        f"Specify the license for the case study text and any included assets.\n\n"
        f"## Attribution\n\n"
        f"Provide required attribution for datasets, figures, quotes, and external materials.\n\n"
        f"## Notes\n\n"
        f"Document permissions, restrictions, and any third-party content considerations.\n"
    )
    write_text(rights_path, rights, args.force)

    print(str(case_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
