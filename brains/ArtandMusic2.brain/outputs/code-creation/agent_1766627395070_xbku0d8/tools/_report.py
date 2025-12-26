"""Deterministic validation report writer (JSON + text) for CI/local workflows."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_str(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, (str, int, float, bool)):
        return str(x)
    try:
        return json.dumps(x, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(x)


def _stable_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _stable_json(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        norm = [_stable_json(v) for v in obj]
        if all(isinstance(v, dict) for v in norm):
            return sorted(norm, key=lambda d: json.dumps(d, ensure_ascii=False, sort_keys=True))
        return norm
    return obj
def _normalize_error(err: Any) -> Dict[str, Any]:
    if isinstance(err, str):
        return {"message": err}
    if isinstance(err, dict):
        out: Dict[str, Any] = {}
        for k in ("message", "path", "instance_path", "schema_path", "validator", "keyword", "code", "context"):
            if k in err:
                out[k] = err[k]
        if "loc" in err and "path" not in out:
            out["path"] = err["loc"]
        if "instancePath" in err and "instance_path" not in out:
            out["instance_path"] = err["instancePath"]
        if "schemaPath" in err and "schema_path" not in out:
            out["schema_path"] = err["schemaPath"]
        if "msg" in err and "message" not in out:
            out["message"] = err["msg"]
        if "error" in err and "message" not in out:
            out["message"] = err["error"]
        if "detail" in err and "context" not in out:
            out["context"] = err["detail"]
        if "message" not in out:
            out["message"] = _as_str(err)
        return out
    return {"message": _as_str(err)}


def _error_sort_key(e: Dict[str, Any]) -> Tuple[str, str, str]:
    p = _as_str(e.get("path") or e.get("instance_path"))
    v = _as_str(e.get("validator") or e.get("keyword") or e.get("code"))
    m = _as_str(e.get("message"))
    return (p, v, m)
def make_report(
    result: Any,
    *,
    source_path: Optional[str] = None,
    schema_path: Optional[str] = None,
    tool: str = "metadata_cli",
    tool_version: Optional[str] = None,
) -> Dict[str, Any]:
    payload = result
    meta: Dict[str, Any] = {}
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    if isinstance(payload, dict):
        for k in ("source_path", "schema_path", "tool", "tool_version"):
            if k in payload:
                meta[k] = payload[k]
        raw_errors = payload.get("errors")
        raw_warnings = payload.get("warnings")
        if raw_errors is None and raw_warnings is None and "valid" in payload:
            raw_errors = payload.get("problems") or payload.get("issues") or []
        if raw_errors is not None:
            errors = [_normalize_error(e) for e in (raw_errors or [])]
        if raw_warnings is not None:
            warnings = [_normalize_error(e) for e in (raw_warnings or [])]
        if "summary" in payload and isinstance(payload["summary"], dict):
            meta.setdefault("summary", payload["summary"])
    elif isinstance(payload, list):
        errors = [_normalize_error(e) for e in payload]
    else:
        errors = [{"message": _as_str(payload)}]

    if source_path is not None:
        meta["source_path"] = source_path
    if schema_path is not None:
        meta["schema_path"] = schema_path
    meta.setdefault("tool", tool)
    if tool_version is not None:
        meta["tool_version"] = tool_version

    errors = sorted(errors, key=_error_sort_key)
    warnings = sorted(warnings, key=_error_sort_key)

    ok = (len(errors) == 0)
    report: Dict[str, Any] = {
        "timestamp_utc": _utc_now_iso(),
        "ok": ok,
        "counts": {"errors": len(errors), "warnings": len(warnings)},
        "meta": _stable_json(meta),
        "errors": _stable_json(errors),
        "warnings": _stable_json(warnings),
    }
    return report
def render_text(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"ok: {report.get('ok')}")
    lines.append(f"timestamp_utc: {report.get('timestamp_utc')}")
    counts = report.get("counts") or {}
    lines.append(f"errors: {counts.get('errors', 0)}")
    lines.append(f"warnings: {counts.get('warnings', 0)}")

    meta = report.get("meta") or {}
    if meta:
        lines.append("")
        lines.append("meta:")
        for k in sorted(meta.keys()):
            v = meta[k]
            if isinstance(v, (dict, list)):
                v_str = json.dumps(v, ensure_ascii=False, sort_keys=True)
            else:
                v_str = _as_str(v)
            lines.append(f"  {k}: {v_str}")

    def _section(title: str, items: Iterable[Dict[str, Any]]) -> None:
        items = list(items)
        lines.append("")
        lines.append(f"{title}:")
        if not items:
            lines.append("  (none)")
            return
        for i, e in enumerate(items, 1):
            p = _as_str(e.get("path") or e.get("instance_path"))
            v = _as_str(e.get("validator") or e.get("keyword") or e.get("code"))
            m = _as_str(e.get("message"))
            prefix = f"  {i:03d}."
            parts = [m]
            if p:
                parts.append(f"path={p}")
            if v:
                parts.append(f"validator={v}")
            lines.append(prefix + " " + " | ".join(parts))

    _section("errors", report.get("errors") or [])
    _section("warnings", report.get("warnings") or [])
    return "\n".join(lines).rstrip() + "\n"
def write_reports(report: Dict[str, Any], out_dir: Union[str, Path], name: str = "validation_report") -> Tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = "".join(c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in name).strip("._") or "validation_report"
    json_path = out_dir / f"{safe}.json"
    txt_path = out_dir / f"{safe}.txt"

    report = _stable_json(report)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(render_text(report), encoding="utf-8")
    return json_path, txt_path
def _default_outdir() -> Path:
    # tools/_report.py -> repo_root/runtime/outputs/tools
    here = Path(__file__).resolve()
    repo_root = here.parent.parent
    return repo_root / "runtime" / "outputs" / "tools"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Write deterministic validation reports (JSON + text).")
    p.add_argument("--input", "-i", type=str, required=True, help="Path to a JSON payload (validator output or error list).")
    p.add_argument("--outdir", "-o", type=str, default=str(_default_outdir()), help="Output directory.")
    p.add_argument("--name", "-n", type=str, default="validation_report", help="Base name for report files.")
    p.add_argument("--source-path", type=str, default=None, help="Optional validated document path.")
    p.add_argument("--schema-path", type=str, default=None, help="Optional schema path.")
    p.add_argument("--tool", type=str, default="metadata_cli", help="Tool name for report meta.")
    p.add_argument("--tool-version", type=str, default=None, help="Optional tool version for report meta.")
    args = p.parse_args(argv)

    in_path = Path(args.input)
    payload = _load_json(in_path)
    report = make_report(
        payload,
        source_path=args.source_path,
        schema_path=args.schema_path,
        tool=args.tool,
        tool_version=args.tool_version,
    )
    write_reports(report, args.outdir, args.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
