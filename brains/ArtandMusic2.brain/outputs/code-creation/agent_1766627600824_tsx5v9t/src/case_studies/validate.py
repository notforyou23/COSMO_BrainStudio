"""case_studies.validate

CLI for validating case-study metadata JSON files against the v1 schema.
Intended for CI/hooks usage.

Usage:
  python -m case_studies.validate --all [--root PATH]
  python -m case_studies.validate PATH [PATH ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
def _import_validator():
    """Return (validate_func, schema_label). validate_func(metadata_dict)->List[str]."""
    try:
        from . import schema_v1  # type: ignore
    except Exception as e:  # pragma: no cover
        return None, f"schema_v1 import failed: {e}"

    for name in ("validate_metadata", "validate", "validate_dict"):
        fn = getattr(schema_v1, name, None)
        if callable(fn):
            def _wrap(d):
                out = fn(d)
                if out is None:
                    return []
                if isinstance(out, (list, tuple)):
                    return [str(x) for x in out]
                return [str(out)]
            return _wrap, "v1"

    schema = getattr(schema_v1, "SCHEMA_V1", None) or getattr(schema_v1, "SCHEMA", None)
    if isinstance(schema, dict):
        required = schema.get("required", []) or []
        enums = schema.get("enums", {}) or {}
        def _fallback(d):
            errs: List[str] = []
            for k in required:
                if k not in d:
                    errs.append(f"missing required field: {k}")
            for k, allowed in enums.items():
                if k in d and d[k] not in allowed:
                    errs.append(f"invalid enum for {k}: {d[k]!r} not in {sorted(list(allowed))}")
            return errs
        return _fallback, "v1(fallback)"

    return None, "no validator found in schema_v1"
def _read_json(path: Path) -> Tuple[Optional[dict], Optional[str]]:
    try:
        txt = path.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"read error: {e}"
    try:
        obj = json.loads(txt)
    except Exception as e:
        return None, f"json parse error: {e}"
    if not isinstance(obj, dict):
        return None, "top-level JSON must be an object"
    return obj, None


def _canonical_metadata_path(p: Path) -> Path:
    if p.is_dir():
        return p / "metadata.json"
    return p


def _iter_metadata_files(root: Path) -> Iterable[Path]:
    # Prefer canonical case-studies layout if available.
    try:
        from . import paths as cs_paths  # type: ignore
        get_root = getattr(cs_paths, "get_cases_root", None) or getattr(cs_paths, "find_cases_root", None)
        if callable(get_root):
            root = Path(get_root(root))
    except Exception:
        pass

    if not root.exists():
        return []
    # Search for metadata.json in the tree; skip obvious noise directories.
    skip = {".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build"}

    def _walk(d: Path) -> Iterable[Path]:
        try:
            entries = list(d.iterdir())
        except Exception:
            return []
        for e in entries:
            if e.is_dir():
                if e.name in skip or e.name.startswith("."):
                    continue
                yield from _walk(e)
            elif e.is_file() and e.name == "metadata.json":
                yield e

    return _walk(root)
def validate_paths(paths: List[Path]) -> int:
    validate_fn, schema_label = _import_validator()
    if validate_fn is None:
        print(f"ERROR: cannot validate without schema validator ({schema_label})", file=sys.stderr)
        return 2

    any_errors = False
    for p in paths:
        mp = _canonical_metadata_path(p)
        if not mp.exists():
            print(f"FAIL {mp}: file not found", file=sys.stderr)
            any_errors = True
            continue
        data, err = _read_json(mp)
        if err:
            print(f"FAIL {mp}: {err}", file=sys.stderr)
            any_errors = True
            continue
        errs = validate_fn(data)
        if errs:
            any_errors = True
            print(f"FAIL {mp}: {len(errs)} error(s)", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"OK   {mp} ({schema_label})")
    return 1 if any_errors else 0


def _parse_args(argv: List[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python -m case_studies.validate")
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--all", action="store_true", help="Validate all metadata.json under --root (default: cwd)")
    ap.add_argument("--root", default=".", help="Root to scan when using --all (default: .)")
    ap.add_argument("paths", nargs="*", help="Paths to case folders or metadata.json files")
    return ap.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    ns = _parse_args(sys.argv[1:] if argv is None else argv)
    if ns.all:
        root = Path(ns.root).resolve()
        files = list(_iter_metadata_files(root))
        if not files:
            print(f"ERROR: no metadata.json files found under {root}", file=sys.stderr)
            return 2
        return validate_paths(files)

    if not ns.paths:
        print("ERROR: provide PATH(s) or use --all", file=sys.stderr)
        return 2
    return validate_paths([Path(p).resolve() for p in ns.paths])


if __name__ == "__main__":
    raise SystemExit(main())
