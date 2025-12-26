from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any, Dict, Iterable, Mapping, Optional, Union


Jsonable = Union[None, bool, int, float, str, list, dict]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_jsonable(obj: Any) -> Jsonable:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, Mapping):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    return repr(obj)


def _safe_slug(s: str) -> str:
    s = (s or "").strip().replace(" ", "_")
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("_", "-", "."):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "report"


def render_text_report(results: Mapping[str, Any]) -> str:
    r = _to_jsonable(results)
    assert isinstance(r, dict)
    status = str(r.get("status") or r.get("overall") or "UNKNOWN").upper()
    passed = bool(r.get("passed")) if "passed" in r else (status == "PASS")
    status_line = "PASS" if passed or status == "PASS" else ("FAIL" if status == "FAIL" else status)

    lines = []
    lines.append(f"QA Validation Report ({status_line})")
    lines.append(f"generated_utc: {_utc_now_iso()}")

    meta = r.get("meta") if isinstance(r.get("meta"), dict) else {}
    if meta:
        for k in ("project_root", "outputs_dir", "qa_dir", "generator_cmd", "duration_s"):
            if k in meta:
                lines.append(f"{k}: {meta.get(k)}")

    run = r.get("run") if isinstance(r.get("run"), dict) else {}
    if run:
        for k in ("returncode", "timeout_s"):
            if k in run:
                lines.append(f"run.{k}: {run.get(k)}")

    errors = r.get("errors") if isinstance(r.get("errors"), list) else []
    if errors:
        lines.append("")
        lines.append("Errors:")
        for e in errors:
            lines.append(f"- {e}")

    checks = r.get("checks") if isinstance(r.get("checks"), list) else []
    if checks:
        lines.append("")
        lines.append("Checks:")
        for c in checks:
            if not isinstance(c, dict):
                lines.append(f"- {c}")
                continue
            name = c.get("name") or c.get("id") or "check"
            ok = c.get("ok")
            st = "PASS" if ok is True else ("FAIL" if ok is False else "INFO")
            detail = c.get("detail") or c.get("message") or ""
            lines.append(f"- [{st}] {name}" + (f": {detail}" if detail else ""))
            miss = c.get("missing")
            if isinstance(miss, list) and miss:
                for m in miss:
                    lines.append(f"    missing: {m}")
            exp = c.get("expected")
            if isinstance(exp, list) and exp:
                for ex in exp:
                    lines.append(f"    expected: {ex}")

    artifacts = r.get("artifacts") if isinstance(r.get("artifacts"), dict) else {}
    if artifacts:
        lines.append("")
        lines.append("Artifacts:")
        for k in sorted(artifacts.keys()):
            lines.append(f"- {k}: {artifacts.get(k)}")

    stdout = run.get("stdout") if isinstance(run, dict) else None
    stderr = run.get("stderr") if isinstance(run, dict) else None
    if stdout:
        s = str(stdout).strip()
        if s:
            lines.append("")
            lines.append("generator_stdout (truncated):")
            lines.append(s[:4000])
    if stderr:
        s = str(stderr).strip()
        if s:
            lines.append("")
            lines.append("generator_stderr (truncated):")
            lines.append(s[:4000])

    return "\n".join(lines).rstrip() + "\n"


def write_reports(
    results: Mapping[str, Any],
    qa_dir: Union[str, Path],
    *,
    stem: str = "scaffold_validation",
    write_latest: bool = True,
) -> Dict[str, str]:
    qa_path = Path(qa_dir)
    qa_path.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = _safe_slug(stem)
    json_path = qa_path / f"{stem}_{ts}.json"
    txt_path = qa_path / f"{stem}_{ts}.md"

    payload = _to_jsonable(results)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(render_text_report(results), encoding="utf-8")

    out = {"json": str(json_path), "text": str(txt_path)}

    if write_latest:
        latest_json = qa_path / f"{stem}_latest.json"
        latest_txt = qa_path / f"{stem}_latest.md"
        latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
        latest_txt.write_text(txt_path.read_text(encoding="utf-8"), encoding="utf-8")
        out["json_latest"] = str(latest_json)
        out["text_latest"] = str(latest_txt)

    return out
