from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import json


@dataclass
class ValidationItem:
    path: str
    required: bool = True
    kind: str = "file"  # "file" or "dir"
    min_bytes: int = 1
    min_files: int = 1
    must_parse_json: bool = False

    @staticmethod
    def from_spec(spec: Union[str, Dict[str, Any]]) -> "ValidationItem":
        if isinstance(spec, str):
            return ValidationItem(path=spec)
        p = spec.get("path")
        if not p or not isinstance(p, str):
            raise ValueError("Validation spec missing string 'path'")
        kind = spec.get("kind", "file")
        must_parse = bool(spec.get("must_parse_json", False))
        if spec.get("json", False) or spec.get("parse_json", False):
            must_parse = True
        return ValidationItem(
            path=p,
            required=bool(spec.get("required", True)),
            kind=kind if kind in ("file", "dir") else "file",
            min_bytes=int(spec.get("min_bytes", 1)),
            min_files=int(spec.get("min_files", 1)),
            must_parse_json=must_parse,
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_rel(path: Path, base: Optional[Path]) -> str:
    if base:
        try:
            return str(path.resolve().relative_to(base.resolve()))
        except Exception:
            return str(path)
    return str(path)


def _file_sha256(path: Path, max_bytes: int = 50_000_000) -> Tuple[Optional[str], Optional[str]]:
    try:
        h = sha256()
        n = 0
        with path.open("rb") as f:
            while True:
                b = f.read(1024 * 1024)
                if not b:
                    break
                n += len(b)
                if n > max_bytes:
                    return None, f"sha256 skipped (file too large > {max_bytes} bytes)"
                h.update(b)
        return h.hexdigest(), None
    except Exception as e:
        return None, f"sha256 error: {e!r}"


def _maybe_parse_json(path: Path) -> Tuple[Optional[bool], Optional[str]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            json.load(f)
        return True, None
    except Exception as e:
        return False, f"json parse error: {e!r}"


def validate_outputs(
    required: Iterable[Union[str, Dict[str, Any]]],
    base_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Validate required output paths, file presence, and basic integrity.

    Args:
      required: Iterable of path strings or dict specs:
        {"path": "...", "kind": "file|dir", "required": bool, "min_bytes": int,
         "min_files": int, "must_parse_json": bool}
      base_dir: Optional base directory to resolve relative paths.

    Returns:
      Structured dict suitable for QA summaries.
    """
    base = Path(base_dir).resolve() if base_dir else None
    items = [ValidationItem.from_spec(s) for s in required]
    results: List[Dict[str, Any]] = []
    ok_required = True
    missing_required: List[str] = []

    for it in items:
        p = (base / it.path) if (base and not Path(it.path).is_absolute()) else Path(it.path)
        pr = p.resolve() if p.exists() else p
        entry: Dict[str, Any] = {
            "path": str(it.path),
            "resolved": str(pr),
            "rel_to_base": _safe_rel(pr, base),
            "kind": it.kind,
            "required": it.required,
            "exists": p.exists(),
        }

        if not p.exists():
            entry["status"] = "missing"
            if it.required:
                ok_required = False
                missing_required.append(str(it.path))
            results.append(entry)
            continue

        try:
            st = p.stat()
            entry["mtime_utc"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
        except Exception as e:
            entry["stat_error"] = repr(e)

        if it.kind == "dir":
            entry["is_dir"] = p.is_dir()
            if not p.is_dir():
                entry["status"] = "wrong_type"
                if it.required:
                    ok_required = False
                results.append(entry)
                continue
            try:
                files = [q for q in p.rglob("*") if q.is_file()]
                entry["file_count"] = len(files)
                entry["status"] = "ok" if len(files) >= it.min_files else "too_few_files"
                if entry["status"] != "ok" and it.required:
                    ok_required = False
            except Exception as e:
                entry["status"] = "error"
                entry["error"] = repr(e)
                if it.required:
                    ok_required = False
            results.append(entry)
            continue

        entry["is_file"] = p.is_file()
        if not p.is_file():
            entry["status"] = "wrong_type"
            if it.required:
                ok_required = False
            results.append(entry)
            continue

        size = None
        try:
            size = p.stat().st_size
            entry["bytes"] = int(size)
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = f"size error: {e!r}"
            if it.required:
                ok_required = False
            results.append(entry)
            continue

        if size is not None and size < it.min_bytes:
            entry["status"] = "too_small"
            if it.required:
                ok_required = False
        else:
            entry["status"] = "ok"

        digest, digest_note = _file_sha256(p)
        if digest:
            entry["sha256"] = digest
        if digest_note:
            entry["sha256_note"] = digest_note

        ext = p.suffix.lower()
        should_parse = it.must_parse_json or ext == ".json"
        if should_parse:
            j_ok, j_err = _maybe_parse_json(p)
            entry["json_ok"] = bool(j_ok)
            if j_err:
                entry["json_error"] = j_err
                if it.required:
                    ok_required = False
                entry["status"] = "invalid_json"

        results.append(entry)

    summary = {
        "checked_at_utc": _utc_now_iso(),
        "base_dir": str(base) if base else None,
        "ok": bool(ok_required),
        "required_missing": missing_required,
        "counts": {
            "total": len(results),
            "missing": sum(1 for r in results if r.get("status") == "missing"),
            "invalid": sum(1 for r in results if r.get("status") not in ("ok",)),
        },
        "items": results,
    }
    return summary


def require_ok(report: Dict[str, Any]) -> None:
    """Raise RuntimeError if validation report is not OK."""
    if not report.get("ok", False):
        missing = report.get("required_missing") or []
        raise RuntimeError(f"Output validation failed; missing/invalid required outputs: {missing}")
