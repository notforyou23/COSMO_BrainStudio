#!/usr/bin/env python3
from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REQUIRED_FILES = [
    "REPORT_OUTLINE.md",
    "CASE_STUDY_TEMPLATE.md",
    "METADATA_SCHEMA.json",
    "WORKLOG.md",
]

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent

def _run_scaffold(root: Path) -> dict:
    run_scaffold = root / "scripts" / "run_scaffold.py"
    if not run_scaffold.exists():
        return {
            "ran": False,
            "ok": False,
            "cmd": None,
            "returncode": None,
            "stdout": "",
            "stderr": f"Missing scaffold generator: {run_scaffold}",
        }
    cmd = [sys.executable, str(run_scaffold)]
    p = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    return {
        "ran": True,
        "ok": p.returncode == 0,
        "cmd": " ".join(cmd),
        "returncode": p.returncode,
        "stdout": (p.stdout or "").strip(),
        "stderr": (p.stderr or "").strip(),
    }

def _validate(root: Path) -> dict:
    results = []
    for name in REQUIRED_FILES:
        path = root / name
        results.append({"file": name, "present": path.is_file(), "path": str(path)})
    return {
        "all_present": all(r["present"] for r in results),
        "results": results,
    }

def _write_summary(root: Path, scaffold: dict, validation: dict) -> Path:
    log_dir = root / "outputs" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    out_path = log_dir / "validation.txt"

    lines = []
    lines.append("Validation Summary")
    lines.append(f"Timestamp (UTC): {_utc_now()}")
    lines.append(f"Repository root: {root}")
    lines.append("")
    lines.append("1) Scaffold generator execution")
    if scaffold["ran"]:
        lines.append(f"- Command: {scaffold['cmd']}")
        lines.append(f"- Return code: {scaffold['returncode']}")
        lines.append(f"- Status: {'OK' if scaffold['ok'] else 'FAIL'}")
    else:
        lines.append("- Command: (not run)")
        lines.append("- Status: FAIL")
    if scaffold.get("stdout"):
        lines.append("")
        lines.append("STDOUT:")
        lines.append(scaffold["stdout"])
    if scaffold.get("stderr"):
        lines.append("")
        lines.append("STDERR:")
        lines.append(scaffold["stderr"])

    lines.append("")
    lines.append("2) Required output files")
    for r in validation["results"]:
        lines.append(f"- {'OK' if r['present'] else 'MISSING'}: {r['file']}  ({r['path']})")

    overall_ok = bool(scaffold["ok"]) and bool(validation["all_present"])
    lines.append("")
    lines.append(f"OVERALL: {'PASS' if overall_ok else 'FAIL'}")

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path

def main() -> int:
    root = _repo_root()
    scaffold = _run_scaffold(root)
    validation = _validate(root)
    out_path = _write_summary(root, scaffold, validation)

    overall_ok = bool(scaffold["ok"]) and bool(validation["all_present"])
    print(str(out_path))
    return 0 if overall_ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
