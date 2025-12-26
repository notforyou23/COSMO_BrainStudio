#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _draft_validator(schema: dict):
    try:
        import jsonschema  # type: ignore
    except Exception as e:
        return None, f"jsonschema import failed: {e}"

    draft = str(schema.get("$schema", "")).lower()
    Validator = None
    if "2020-12" in draft:
        Validator = getattr(jsonschema, "Draft202012Validator", None)
    elif "2019-09" in draft:
        Validator = getattr(jsonschema, "Draft201909Validator", None)
    elif "draft-07" in draft or "draft7" in draft:
        Validator = getattr(jsonschema, "Draft7Validator", None)
    elif "draft-06" in draft or "draft6" in draft:
        Validator = getattr(jsonschema, "Draft6Validator", None)
    elif "draft-04" in draft or "draft4" in draft:
        Validator = getattr(jsonschema, "Draft4Validator", None)
    if Validator is None:
        Validator = getattr(jsonschema, "Draft202012Validator", None) or getattr(jsonschema, "Draft7Validator", None)
    if Validator is None:
        return None, "No supported jsonschema Draft validator available."
    try:
        Validator.check_schema(schema)
    except Exception as e:
        return None, f"Schema is invalid: {e}"
    return Validator(schema), None


def _format_error(err) -> dict:
    path = "/" + "/".join(str(p) for p in err.absolute_path) if list(err.absolute_path) else ""
    spath = "/" + "/".join(str(p) for p in err.absolute_schema_path) if list(err.absolute_schema_path) else ""
    msg = getattr(err, "message", str(err))
    return {"path": path, "schema_path": spath, "message": msg}


def _write_md(out_md: Path, report: dict) -> None:
    lines = []
    lines.append("# Case Study Schema Validation")
    lines.append("")
    lines.append(f"- Timestamp (UTC): {report.get('timestamp_utc','')}")
    lines.append(f"- Schema: `{report.get('schema_path','')}`")
    lines.append(f"- Input glob: `{report.get('input_glob','')}`")
    lines.append(f"- Files checked: {report.get('files_checked',0)}")
    lines.append(f"- Passed: {report.get('files_passed',0)}")
    lines.append(f"- Failed: {report.get('files_failed',0)}")
    lines.append(f"- Overall: **{'PASS' if report.get('overall_pass') else 'FAIL'}**")
    lines.append("")
    if report.get("fatal_error"):
        lines.append("## Fatal error")
        lines.append("")
        lines.append(report["fatal_error"])
        lines.append("")
    lines.append("## Per-file results")
    lines.append("")
    results = report.get("results", [])
    if not results:
        lines.append("_No files found._")
    for r in results:
        status = "PASS" if r.get("pass") else "FAIL"
        lines.append(f"### {status}: `{r.get('file','')}`")
        if r.get("pass"):
            lines.append("")
            continue
        errs = r.get("errors", [])
        lines.append(f"- Errors: {len(errs)}")
        for e in errs[:200]:
            p = e.get("path", "")
            sp = e.get("schema_path", "")
            m = e.get("message", "")
            lines.append(f"  - `{p}` ({sp}): {m}")
        if len(errs) > 200:
            lines.append(f"  - ... {len(errs)-200} more")
        lines.append("")
    out_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "runtime/outputs/METADATA_SCHEMA.json"
    in_dir = root / "runtime/outputs/case_studies"
    qa_dir = root / "runtime/outputs/qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    out_json = qa_dir / "schema_validation.json"
    out_md = qa_dir / "schema_validation.md"

    report = {
        "timestamp_utc": _now_iso(),
        "schema_path": str(schema_path),
        "input_glob": str(in_dir / "*.json"),
        "overall_pass": False,
        "files_checked": 0,
        "files_passed": 0,
        "files_failed": 0,
        "fatal_error": None,
        "results": [],
    }

    try:
        schema = _load_json(schema_path)
    except Exception as e:
        report["fatal_error"] = f"Failed to load schema: {e}"
        out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _write_md(out_md, report)
        print("SCHEMA_VALIDATION:FAIL")
        return 2

    validator, v_err = _draft_validator(schema)
    if validator is None:
        report["fatal_error"] = v_err or "Validator unavailable."
        out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _write_md(out_md, report)
        print("SCHEMA_VALIDATION:FAIL")
        return 2

    files = sorted(in_dir.glob("*.json"))
    for fp in files:
        rec = {"file": str(fp), "pass": False, "errors": []}
        try:
            inst = _load_json(fp)
            errs = list(validator.iter_errors(inst))
            errs.sort(key=lambda e: (list(e.absolute_path), getattr(e, "message", "")))
            rec["errors"] = [_format_error(e) for e in errs]
            rec["pass"] = len(rec["errors"]) == 0
        except Exception as e:
            rec["errors"] = [{"path": "", "schema_path": "", "message": f"Failed to load/validate JSON: {e}"}]
            rec["pass"] = False
        report["results"].append(rec)

    report["files_checked"] = len(report["results"])
    report["files_passed"] = sum(1 for r in report["results"] if r.get("pass"))
    report["files_failed"] = report["files_checked"] - report["files_passed"]
    report["overall_pass"] = report["files_failed"] == 0 and report["fatal_error"] is None

    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_md(out_md, report)
    print("SCHEMA_VALIDATION:" + ("PASS" if report["overall_pass"] else "FAIL"))
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
