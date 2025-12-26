"""Single-command QA gate runner.

Usage:
  python -m qa.run
  python -m qa.run --report DRAFT_REPORT_v0.md --artifacts pilot_artifacts
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_text(path: Path, limit: int = 2_000_000) -> Tuple[str, Optional[str]]:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return "", "File not found"
    except Exception as e:
        return "", f"Read error: {type(e).__name__}: {e}"
    if len(data) > limit:
        return data[:limit], f"Truncated to {limit} chars"
    return data, None


def _discover_artifacts(root: Optional[Path]) -> Tuple[Optional[Path], List[Path], Optional[str]]:
    if root is None:
        return None, [], None
    root = root.expanduser().resolve()
    if not root.exists():
        return root, [], "Artifacts path does not exist"
    if root.is_file():
        return root.parent, [root], None
    files: List[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and not any(part.startswith(".") for part in p.parts):
            files.append(p)
    files.sort(key=lambda p: str(p))
    return root, files, None


@dataclass
class CheckResult:
    id: str
    title: str
    status: str  # PASS | FAIL | WARN
    errors: List[str]
    remediation: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "errors": self.errors,
            "remediation": self.remediation,
        }


def _pass(cid: str, title: str) -> CheckResult:
    return CheckResult(cid, title, "PASS", [], [])


def _fail(cid: str, title: str, errors: List[str], remediation: List[str]) -> CheckResult:
    return CheckResult(cid, title, "FAIL", errors, remediation)


def _warn(cid: str, title: str, errors: List[str], remediation: List[str]) -> CheckResult:
    return CheckResult(cid, title, "WARN", errors, remediation)


def run_checks(report_path: Path, report_text: str, report_read_note: Optional[str],
               artifacts_root: Optional[Path], artifacts_files: List[Path], artifacts_note: Optional[str]) -> List[CheckResult]:
    checks: List[CheckResult] = []

    # 1) Report exists/readable
    if not report_path.exists():
        checks.append(_fail(
            "report.exists",
            "DRAFT report is present",
            [f"Missing report file: {report_path}"],
            ["Ensure DRAFT_REPORT_v0.md exists at the specified path, or pass --report to point to it."],
        ))
        return checks  # remaining checks depend on report text
    if report_read_note and "Read error" in report_read_note:
        checks.append(_fail(
            "report.readable",
            "DRAFT report is readable",
            [f"Could not read report: {report_read_note}"],
            ["Fix filesystem permissions/encoding issues and re-run the QA gate."],
        ))
        return checks
    checks.append(_pass("report.readable", "DRAFT report is readable"))

    # 2) Non-empty
    if len(report_text.strip()) < 200:
        checks.append(_fail(
            "report.nonempty",
            "DRAFT report has sufficient content",
            [f"Report content is too short ({len(report_text.strip())} chars)."],
            ["Populate the report with the expected narrative, sections, and references; re-run QA."],
        ))
    else:
        checks.append(_pass("report.nonempty", "DRAFT report has sufficient content"))

    # 3) Has a top-level title
    first_nonempty = ""
    for line in report_text.splitlines():
        if line.strip():
            first_nonempty = line.strip()
            break
    if not first_nonempty.startswith("# "):
        checks.append(_warn(
            "report.title",
            "Report starts with a level-1 title",
            [f"First non-empty line is not a '# ' title: {first_nonempty[:80]!r}"],
            ["Add a top-level markdown title (e.g., '# Report Title') as the first non-empty line."],
        ))
    else:
        checks.append(_pass("report.title", "Report starts with a level-1 title"))

    # 4) Has multiple sections
    h2 = sum(1 for l in report_text.splitlines() if l.lstrip().startswith("## "))
    if h2 < 3:
        checks.append(_warn(
            "report.sections",
            "Report has multiple sections",
            [f"Found only {h2} level-2 sections (##)."],
            ["Add clear sections (## ...) for methods, results, limitations, and next steps."],
        ))
    else:
        checks.append(_pass("report.sections", "Report has multiple sections"))

    # 5) Artifacts discovery
    if artifacts_root is None:
        checks.append(_warn(
            "artifacts.provided",
            "Pilot artifacts are provided",
            ["No artifacts path provided."],
            ["Pass --artifacts <dir-or-file> so QA can validate presence and references to pilot artifacts."],
        ))
    else:
        if artifacts_note:
            checks.append(_warn(
                "artifacts.discovered",
                "Pilot artifacts are discoverable",
                [artifacts_note],
                ["Confirm the artifacts path; ensure it exists and contains the expected files."],
            ))
        if len(artifacts_files) == 0:
            checks.append(_fail(
                "artifacts.nonempty",
                "At least one artifact file is present",
                [f"No files found under artifacts root: {artifacts_root}"],
                ["Add pilot artifacts (data, logs, figures, notebooks) under the artifacts directory and re-run QA."],
            ))
        else:
            checks.append(_pass("artifacts.nonempty", "At least one artifact file is present"))

    # 6) Artifact references in report
    if artifacts_files:
        names = [p.name for p in artifacts_files]
        referenced = [n for n in names if n in report_text]
        if len(referenced) == 0:
            checks.append(_warn(
                "artifacts.referenced",
                "Report references pilot artifacts",
                ["No artifact filenames were found referenced in the report text."],
                ["Add explicit references/links to pilot artifacts (filenames or relative paths) in the report."],
            ))
        else:
            checks.append(_pass("artifacts.referenced", "Report references pilot artifacts"))

    # 7) Truncation note
    if report_read_note and "Truncated" in report_read_note:
        checks.append(_warn(
            "report.truncated",
            "Report read was not truncated",
            [report_read_note],
            ["QA read was truncated; consider reducing report size or adjust reader limits if needed."],
        ))

    return checks


def render_md(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# QA Report")
    lines.append("")
    lines.append(f"- Generated at: `{payload.get('generated_at','')}`")
    inputs = payload.get("inputs", {})
    lines.append(f"- Report: `{inputs.get('report_path','')}`")
    ar = inputs.get("artifacts_root")
    lines.append(f"- Artifacts: `{ar}`" if ar else "- Artifacts: (none)")
    lines.append("")
    summ = payload.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Overall: **{summ.get('overall_status','UNKNOWN')}**")
    lines.append(f"- PASS: {summ.get('pass',0)}  FAIL: {summ.get('fail',0)}  WARN: {summ.get('warn',0)}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| ID | Title | Status |")
    lines.append("|---|---|---|")
    for c in payload.get("checks", []):
        lines.append(f"| `{c.get('id','')}` | {c.get('title','')} | **{c.get('status','')}** |")
    lines.append("")
    lines.append("## Details & Remediation")
    lines.append("")
    for c in payload.get("checks", []):
        status = c.get("status", "")
        if status == "PASS":
            continue
        lines.append(f"### {c.get('id','')} — {c.get('title','')}")
        lines.append("")
        errs = c.get("errors") or []
        rem = c.get("remediation") or []
        if errs:
            lines.append("Errors / Notes:")
            for e in errs:
                lines.append(f"- {e}")
            lines.append("")
        if rem:
            lines.append("Remediation:")
            for r in rem:
                lines.append(f"- {r}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Run QA gate on DRAFT report and pilot artifacts; emit QA_REPORT.json and QA_REPORT.md.")
    ap.add_argument("--report", default="DRAFT_REPORT_v0.md", help="Path to DRAFT_REPORT_v0.md (default: ./DRAFT_REPORT_v0.md)")
    ap.add_argument("--artifacts", default=None, help="Path to pilot artifacts directory or a single file")
    ap.add_argument("--out-dir", default=".", help="Output directory for QA_REPORT.json and QA_REPORT.md (default: .)")
    args = ap.parse_args(argv)

    report_path = Path(args.report).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    report_text, report_note = _read_text(report_path)

    artifacts_root = Path(args.artifacts) if args.artifacts else None
    artifacts_root, artifacts_files, artifacts_note = _discover_artifacts(artifacts_root)
    rel_files: List[str] = []
    if artifacts_root and artifacts_files:
        for p in artifacts_files:
            try:
                rel_files.append(str(p.resolve().relative_to(artifacts_root.resolve())))
            except Exception:
                rel_files.append(str(p))

    checks = run_checks(report_path, report_text, report_note, artifacts_root, artifacts_files, artifacts_note)
    counts = {"PASS": 0, "FAIL": 0, "WARN": 0}
    for c in checks:
        counts[c.status] = counts.get(c.status, 0) + 1
    overall = "FAIL" if counts.get("FAIL", 0) else ("WARN" if counts.get("WARN", 0) else "PASS")

    payload: Dict[str, Any] = {
        "generated_at": _utc_now(),
        "inputs": {
            "report_path": str(report_path),
            "artifacts_root": str(artifacts_root) if artifacts_root else None,
            "artifact_files": rel_files,
        },
        "summary": {"overall_status": overall, "pass": counts.get("PASS", 0), "fail": counts.get("FAIL", 0), "warn": counts.get("WARN", 0)},
        "checks": [c.to_dict() for c in checks],
    }

    (out_dir / "QA_REPORT.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "QA_REPORT.md").write_text(render_md(payload), encoding="utf-8")

    print(f"QA: overall={overall} pass={counts.get('PASS',0)} fail={counts.get('FAIL',0)} warn={counts.get('WARN',0)}")
    return 2 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
