from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import sys
import re

REQUIRED = [
    ("Report", ["REPORT.md", "report.md", "Report.md", "outputs_report.md", "*report*.md"]),
    ("Pilot case study", ["PILOT_CASE_STUDY.md", "pilot_case_study.md", "*case*study*.md", "*pilot*.md"]),
    ("Rights log", ["RIGHTS_LOG.md", "rights_log.md", "*rights*log*.md", "*rights*.md"]),
    ("Schemas", ["schemas/**/*.json", "schemas/**/*.yaml", "schemas/**/*.yml", "*schema*.json", "*schemas*.md"]),
    ("QA outputs", ["qa/**/*", "*qa*.*", "QA/**/*"]),
    ("Tracker", ["TRACKER.md", "tracker.md", "*tracker*.md", "*tracking*.md"]),
]

DEFAULT_INDEX_NAME = "ARTIFACT_INDEX.md"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _outputs_dir(root: Path) -> Path:
    return root / "outputs"


def _iter_files(outputs: Path):
    for p in sorted(outputs.rglob("*")):
        if p.is_file():
            yield p


def _match_glob(outputs: Path, pat: str):
    return sorted(outputs.glob(pat))


def _find_required(outputs: Path, patterns: list[str]) -> Path | None:
    for pat in patterns:
        hits = _match_glob(outputs, pat) if any(ch in pat for ch in "*?[]") else [outputs / pat]
        for h in hits:
            if h.exists():
                if h.is_file():
                    return h
                if h.is_dir():
                    files = [p for p in sorted(h.rglob("*")) if p.is_file()]
                    return files[0] if files else h
    return None


def _rel_from_outputs(outputs: Path, p: Path) -> str:
    try:
        rel = p.relative_to(outputs).as_posix()
    except Exception:
        rel = p.as_posix()
    return rel


def _md_link(text: str, rel_path: str) -> str:
    safe = rel_path.replace(" ", "%20")
    if not safe.startswith("./"):
        safe = "./" + safe
    return f"[{text}]({safe})"


def _build_index(outputs: Path, index_path: Path) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines = []
    lines.append("# Artifact Index")
    lines.append("")
    lines.append(f"_Auto-generated from `outputs/` on {now}._")
    lines.append("")
    lines.append("## Required deliverables")
    lines.append("")
    lines.append("| Deliverable | Status | Link |")
    lines.append("|---|---:|---|")

    for name, patterns in REQUIRED:
        found = _find_required(outputs, patterns)
        if found and found.exists():
            rel = _rel_from_outputs(outputs, found)
            status = "FOUND"
            link = _md_link(rel, rel)
        else:
            status = "MISSING"
            link = "—"
        lines.append(f"| {name} | {status} | {link} |")

    lines.append("")
    lines.append("## Discovered files (under `outputs/`)")
    lines.append("")
    files = [_rel_from_outputs(outputs, p) for p in _iter_files(outputs)]
    if not files:
        lines.append("_No files found under outputs/._")
    else:
        for rel in files:
            if rel == index_path.name:
                continue
            lines.append(f"- {_md_link(rel, rel)}")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate outputs/ARTIFACT_INDEX.md by scanning ONLY outputs/.")
    ap.add_argument("--root", default=None, help="Project root (default: inferred from this script location).")
    ap.add_argument("--index", default=DEFAULT_INDEX_NAME, help="Index filename inside outputs/ (default: ARTIFACT_INDEX.md).")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else _repo_root()
    outputs = _outputs_dir(root)
    if not outputs.exists() or not outputs.is_dir():
        print(f"ERROR: outputs/ directory not found at: {outputs}", file=sys.stderr)
        return 2

    index_path = outputs / args.index
    content = _build_index(outputs, index_path)
    index_path.write_text(content, encoding="utf-8")
    print(f"WROTE:{index_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
