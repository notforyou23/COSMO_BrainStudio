"""verify_build_artifacts.py

Command-line verifier that asserts required build artifact files exist under
runtime/_build (reports JSON, tables CSV, figures) and are non-empty.

Intended usage (from repo root):
  python verify_build_artifacts.py
  python verify_build_artifacts.py --root /path/to/repo

Exit codes:
  0 = success
  2 = verification failed (missing/empty/invalid artifacts)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclass
class Finding:
    kind: str  # missing, empty, invalid
    path: str
    detail: str = ""


def _iter_files(base: Path, pattern: str) -> List[Path]:
    return sorted(p for p in base.glob(pattern) if p.is_file())


def _file_nonempty(p: Path) -> bool:
    try:
        return p.stat().st_size > 0
    except FileNotFoundError:
        return False


def _validate_json(p: Path) -> Optional[str]:
    try:
        txt = p.read_text(encoding="utf-8")
        if not txt.strip():
            return "empty content"
        json.loads(txt)
        return None
    except Exception as e:
        return f"json parse error: {e.__class__.__name__}: {e}"


def _validate_csv(p: Path) -> Optional[str]:
    try:
        txt = p.read_text(encoding="utf-8")
        if not txt.strip():
            return "empty content"
        # Ensure at least one row can be read.
        reader = csv.reader(txt.splitlines())
        first = next(reader, None)
        if first is None:
            return "no rows"
        return None
    except Exception as e:
        return f"csv parse error: {e.__class__.__name__}: {e}"


def verify_build_artifacts(root: Path, strict_parse: bool = True) -> Tuple[bool, List[Finding]]:
    findings: List[Finding] = []
    build_dir = root / "runtime" / "_build"

    if not build_dir.exists():
        findings.append(Finding("missing", str(build_dir), "build directory does not exist"))
        return False, findings
    if not build_dir.is_dir():
        findings.append(Finding("missing", str(build_dir), "build path exists but is not a directory"))
        return False, findings

    expected = [
        ("reports", "reports", "*.json"),
        ("tables", "tables", "*.csv"),
        ("figures", "figures", "*"),
    ]

    for label, subdir, pat in expected:
        d = build_dir / subdir
        if not d.exists() or not d.is_dir():
            findings.append(Finding("missing", str(d), f"required {label} directory missing"))
            continue

        files = _iter_files(d, pat)
        if not files:
            findings.append(Finding("missing", str(d / pat), f"no matching {label} files found"))
            continue

        for f in files:
            if not _file_nonempty(f):
                findings.append(Finding("empty", str(f), "file is empty (0 bytes)"))
                continue
            if strict_parse:
                if f.suffix.lower() == ".json":
                    err = _validate_json(f)
                    if err:
                        findings.append(Finding("invalid", str(f), err))
                elif f.suffix.lower() == ".csv":
                    err = _validate_csv(f)
                    if err:
                        findings.append(Finding("invalid", str(f), err))

    ok = len(findings) == 0
    return ok, findings


def _format_report(findings: Iterable[Finding]) -> str:
    grouped = {"missing": [], "empty": [], "invalid": [], "other": []}
    for f in findings:
        grouped.get(f.kind, grouped["other"]).append(f)

    lines: List[str] = []
    for key in ("missing", "empty", "invalid", "other"):
        items = grouped[key]
        if not items:
            continue
        lines.append(f"{key.upper()} ({len(items)}):")
        for it in items:
            detail = f" - {it.detail}" if it.detail else ""
            lines.append(f"  - {it.path}{detail}")
    return "\n".join(lines).strip()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Verify required build artifacts exist and are non-empty.")
    ap.add_argument("--root", type=str, default=".", help="Repository root containing runtime/_build (default: .)")
    ap.add_argument("--no-parse", action="store_true", help="Only check existence/non-empty; skip JSON/CSV parsing.")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    ok, findings = verify_build_artifacts(root=root, strict_parse=not args.no_parse)

    if ok:
        print(f"OK: verified build artifacts under {root / 'runtime' / '_build'}")
        return 0

    report = _format_report(findings)
    sys.stderr.write("ERROR: build artifacts verification failed\n")
    if report:
        sys.stderr.write(report + "\n")
    sys.stderr.write("Hint: ensure the build step writes reports/*.json, tables/*.csv, figures/* under runtime/_build.\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
