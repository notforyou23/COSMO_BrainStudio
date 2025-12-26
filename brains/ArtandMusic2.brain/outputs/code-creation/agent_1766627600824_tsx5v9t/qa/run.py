from __future__ import annotations
import argparse
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _run_git_sha(cwd: Path) -> Optional[str]:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        sha = (r.stdout or "").strip()
        return sha or None
    except Exception:
        return None

def _safe_rel(p: Path, base: Path) -> str:
    try:
        return str(p.resolve().relative_to(base.resolve()))
    except Exception:
        return str(p)
def _parse_kv(items: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for it in items:
        if "=" in it:
            k, v = it.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k:
                out[k] = v
        else:
            k = it.strip()
            if k:
                out[k] = True
    return out

def _default_required(base: Path) -> List[Path]:
    candidates = [
        base / "outputs",
        base / "outputs" / "qa",
    ]
    return candidates
def _maybe_run_artifacts(base: Path, outputs_root: Path, inputs: Dict[str, Any]) -> Dict[str, Any]:
    info: Dict[str, Any] = {"attempted": False, "module": None, "callable": None, "ok": True, "error": None}
    try:
        import importlib

        mod = importlib.import_module("qa.artifacts")
        info["attempted"] = True
        info["module"] = getattr(mod, "__name__", "qa.artifacts")
        for name in ("generate_and_collect", "generate_or_collect", "collect_artifacts", "run", "main"):
            fn = getattr(mod, name, None)
            if callable(fn):
                info["callable"] = name
                try:
                    res = fn(base_dir=base, outputs_root=outputs_root, inputs=inputs)  # type: ignore[arg-type]
                except TypeError:
                    try:
                        res = fn(base, outputs_root, inputs)  # type: ignore[misc]
                    except TypeError:
                        res = fn()  # type: ignore[misc]
                if isinstance(res, dict):
                    info["result"] = res
                return info
        info["ok"] = True
        info["callable"] = None
        return info
    except ModuleNotFoundError:
        return info
    except Exception as e:
        info["attempted"] = True
        info["ok"] = False
        info["error"] = f"{type(e).__name__}: {e}"
        return info
def _validate_required(required: List[Path], base: Path) -> Dict[str, Any]:
    try:
        import importlib

        mod = importlib.import_module("qa.validate")
        fn = getattr(mod, "validate_required_paths", None) or getattr(mod, "validate_outputs", None)
        if callable(fn):
            try:
                res = fn(required_paths=required, base_dir=base)  # type: ignore[arg-type]
            except TypeError:
                res = fn(required, base)  # type: ignore[misc]
            if isinstance(res, dict):
                return res
    except ModuleNotFoundError:
        pass
    except Exception as e:
        return {
            "ok": False,
            "missing": [],
            "present": [],
            "errors": [f"qa.validate error: {type(e).__name__}: {e}"],
        }

    present: List[str] = []
    missing: List[str] = []
    errors: List[str] = []
    for p in required:
        try:
            if p.exists():
                present.append(_safe_rel(p, base))
            else:
                missing.append(_safe_rel(p, base))
        except Exception as e:
            errors.append(f"{_safe_rel(p, base)}: {type(e).__name__}: {e}")
    return {"ok": (len(missing) == 0 and len(errors) == 0), "missing": missing, "present": present, "errors": errors}
def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def _write_md(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

def _md_escape(s: Any) -> str:
    txt = "" if s is None else str(s)
    return txt.replace("|", "\\|").replace("\n", "<br>")
def _build_md(summary: Dict[str, Any]) -> List[str]:
    v = summary.get("validation", {}) or {}
    missing = v.get("missing", []) or []
    errors = v.get("errors", []) or []
    ok = bool(summary.get("ok"))
    lines = [
        "# QA Summary",
        "",
        f"- Status: {'PASS' if ok else 'FAIL'}",
        f"- Run ID: {_md_escape(summary.get('run_id'))}",
        f"- Start (UTC): {_md_escape(summary.get('started_utc'))}",
        f"- End (UTC): {_md_escape(summary.get('ended_utc'))}",
        f"- Git SHA: {_md_escape(summary.get('git_sha'))}",
        f"- CWD: `{_md_escape(summary.get('cwd'))}`",
        "",
        "## Inputs",
        "",
    ]
    inputs = summary.get("inputs", {}) or {}
    if inputs:
        lines += ["| Key | Value |", "|---|---|"]
        for k in sorted(inputs.keys()):
            lines.append(f"| `{_md_escape(k)}` | `{_md_escape(inputs.get(k))}` |")
    else:
        lines.append("_No inputs provided._")
    lines += ["", "## Validation", ""]
    lines.append(f"- OK: `{ok}`")
    if missing:
        lines += ["", "### Missing paths", ""] + [f"- `{_md_escape(x)}`" for x in missing]
    if errors:
        lines += ["", "### Errors", ""] + [f"- {_md_escape(x)}" for x in errors]
    art = summary.get("artifacts", {}) or {}
    if art.get("attempted"):
        lines += ["", "## Artifacts", ""]
        lines.append(f"- Module: `{_md_escape(art.get('module'))}`")
        lines.append(f"- Callable: `{_md_escape(art.get('callable'))}`")
        lines.append(f"- OK: `{_md_escape(art.get('ok'))}`")
        if art.get("error"):
            lines.append(f"- Error: `{_md_escape(art.get('error'))}`")
    return lines
def main(argv: Optional[List[str]] = None) -> int:
    base_dir = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(prog="python -m qa.run", description="Run QA artifact collection and output validation.")
    p.add_argument("--outputs-root", default=str(base_dir / "outputs"), help="Root outputs directory (default: ./outputs).")
    p.add_argument("--required", action="append", default=[], help="Required output path (repeatable). Relative paths are resolved under base dir.")
    p.add_argument("--input", action="append", default=[], help="Input metadata as key=value (repeatable).")
    p.add_argument("--no-artifacts", action="store_true", help="Skip artifact generation/collection step.")
    args = p.parse_args(argv)

    started = _utc_now_iso()
    run_id = os.environ.get("QA_RUN_ID") or f"qa-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    outputs_root = Path(args.outputs_root)
    if not outputs_root.is_absolute():
        outputs_root = (base_dir / outputs_root).resolve()
    qa_dir = outputs_root / "qa"
    summary_json = qa_dir / "qa_summary.json"
    summary_md = qa_dir / "qa_summary.md"

    inputs = _parse_kv(list(args.input or []))
    required: List[Path] = []
    if args.required:
        for rp in args.required:
            rp_p = Path(rp)
            required.append((base_dir / rp_p).resolve() if not rp_p.is_absolute() else rp_p)
    else:
        required = _default_required(base_dir)

    artifacts_info: Dict[str, Any] = {"attempted": False, "ok": True}
    if not args.no_artifacts:
        artifacts_info = _maybe_run_artifacts(base_dir, outputs_root, inputs)

    validation = _validate_required(required, base_dir)
    ok = bool(validation.get("ok", False)) and bool(artifacts_info.get("ok", True))

    ended = _utc_now_iso()
    summary: Dict[str, Any] = {
        "ok": ok,
        "run_id": run_id,
        "started_utc": started,
        "ended_utc": ended,
        "git_sha": _run_git_sha(base_dir),
        "cwd": str(Path.cwd()),
        "base_dir": str(base_dir),
        "outputs_root": str(outputs_root),
        "required_paths": [_safe_rel(p, base_dir) for p in required],
        "inputs": inputs,
        "command": " ".join([sys.executable] + sys.argv),
        "platform": {"python": sys.version.split()[0], "os": platform.platform()},
        "artifacts": artifacts_info,
        "validation": validation,
        "summary_paths": {"json": str(summary_json), "md": str(summary_md)},
    }

    _write_json(summary_json, summary)
    _write_md(summary_md, _build_md(summary))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
