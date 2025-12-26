#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

ROADMAP_DEFAULT = "roadmap_scope_success_criteria.md"
MANIFEST_NAME = "manifest.md"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def outputs_dir(root: Path) -> Path:
    d = root / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def roadmap_markdown(title: str) -> str:
    sections = [
        f"# {title}",
        "",
        "## Thesis / Through-line",
        "This roadmap defines a clear scope and success criteria for producing reliable, repeatable project outputs: we prioritize artifacts that are deterministic, reviewable, and directly support incremental delivery, while explicitly deferring work that does not improve correctness, clarity, or repeatability.",
        "",
        "## Explicit scope",
        "### Inclusions",
        "- A single source-of-truth roadmap document describing scope and success criteria",
        "- Clear boundaries: what is in-scope vs out-of-scope",
        "- Enumerated subtopics (what work exists) with an explicit prioritization policy (how work is ordered)",
        "- A Definition of Done (DoD) checklist that can be applied to each artifact and to the roadmap itself",
        "- A deterministic outputs manifest that links to this roadmap",
        "",
        "### Exclusions",
        "- Shipping production features beyond generating and indexing these documents",
        "- Non-deterministic content in generated artifacts (e.g., timestamps, random IDs, machine-specific paths)",
        "- Unbounded “research” sections without actionable deliverables",
        "- Opinions without measurable verification steps",
        "",
        "## Subtopic list (work breakdown)",
        "1. Roadmap document structure",
        "   - Thesis / through-line",
        "   - Inclusions / exclusions",
        "   - Subtopics list",
        "   - Prioritization policy",
        "   - DoD checklist",
        "2. Outputs manifest",
        "   - Stable, human-readable index of generated artifacts",
        "   - Deterministic linking to the roadmap file",
        "3. CLI generation workflow",
        "   - Idempotent generation (running twice yields identical content)",
        "   - Minimal, understandable behavior and clear errors",
        "",
        "## Prioritization policy",
        "- Determinism first: prefer changes that make outputs stable across runs and machines.",
        "- Clarity second: prefer content that reduces ambiguity (explicit scope, checklists, acceptance criteria).",
        "- Smallest useful increment: ship the smallest complete artifact that can be reviewed end-to-end.",
        "- Avoid churn: do not reformat or reorder content without a concrete benefit.",
        "",
        "## Definition of Done (DoD) checklist",
        "- [ ] Document contains: thesis/through-line, inclusions, exclusions, subtopic list, prioritization policy, and DoD checklist",
        "- [ ] Content is deterministic (no timestamps, random values, or environment-specific paths)",
        "- [ ] File renders correctly as Markdown (headings, lists, links)",
        "- [ ] Outputs manifest exists and includes a working relative link to this roadmap",
        "- [ ] Generation is idempotent (two runs produce byte-identical outputs)",
        "- [ ] CLI returns exit code 0 on success and non-zero on error",
        "",
    ]
    return "\n".join(sections)


def manifest_markdown(roadmap_rel: str) -> str:
    lines = [
        "# Outputs Manifest",
        "",
        "This file is a deterministic, human-readable index of generated artifacts.",
        "",
        "## Generated artifacts",
        f"- [Roadmap (scope & success criteria)]({roadmap_rel})",
        "",
    ]
    return "\n".join(lines)


def write_text_if_changed(path: Path, text: str) -> bool:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate outputs roadmap and deterministic manifest.")
    p.add_argument("--outputs-dir", default=None, help="Override outputs directory (default: <repo>/outputs)")
    p.add_argument("--roadmap-name", default=ROADMAP_DEFAULT, help=f"Roadmap filename (default: {ROADMAP_DEFAULT})")
    p.add_argument("--title", default="Roadmap: Scope & Success Criteria", help="Roadmap document title")
    args = p.parse_args(argv)

    root = repo_root()
    out_dir = Path(args.outputs_dir).expanduser().resolve() if args.outputs_dir else outputs_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)

    roadmap_path = out_dir / args.roadmap_name
    manifest_path = out_dir / MANIFEST_NAME

    roadmap_text = roadmap_markdown(args.title)
    roadmap_rel = roadmap_path.relative_to(out_dir).as_posix()
    manifest_text = manifest_markdown(roadmap_rel)

    changed_roadmap = write_text_if_changed(roadmap_path, roadmap_text)
    changed_manifest = write_text_if_changed(manifest_path, manifest_text)

    # Essential status only: stable, compact output
    if changed_roadmap or changed_manifest:
        print(f"OK:generated:{roadmap_rel};manifest:{MANIFEST_NAME}")
    else:
        print(f"OK:unchanged:{roadmap_rel};manifest:{MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
