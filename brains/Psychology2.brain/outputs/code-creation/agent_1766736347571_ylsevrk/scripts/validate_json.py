#!/usr/bin/env python3
"""Schema validation tool for run specs and run logs.

Validates one or more JSON instances against a JSON Schema before execution/persistence.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _read_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        loc = f"{path}:{e.lineno}:{e.colno}"
        raise ValueError(f"Invalid JSON at {loc}: {e.msg}") from e


def _iter_instance_paths(paths: List[str]) -> List[Path]:
    out: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if any(ch in raw for ch in ["*", "?", "["]) and not p.exists():
            out.extend(sorted(Path().glob(raw)))
        else:
            out.append(p)
    # de-dup while preserving order
    seen = set()
    uniq: List[Path] = []
    for p in out:
        rp = str(p)
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq
def _load_schema(schema_path: Path) -> Dict[str, Any]:
    schema = _read_json(schema_path)
    if not isinstance(schema, dict):
        raise ValueError(f"Schema must be a JSON object: {schema_path}")
    return schema


def _format_error(err: Any) -> str:
    # jsonschema.ValidationError compatible
    path = ""
    try:
        if getattr(err, "path", None):
            path = "/" + "/".join(str(x) for x in list(err.path))
    except Exception:
        path = ""
    msg = getattr(err, "message", None) or str(err)
    if path:
        return f"{path}: {msg}"
    return msg


def _validate_with_jsonschema(instance: Any, schema: Dict[str, Any], schema_path: Path) -> List[str]:
    try:
        import jsonschema  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Dependency missing: jsonschema. Install it (pinned) to enable schema validation."
        ) from e

    base_uri = schema_path.resolve().as_uri()
    try:
        resolver = jsonschema.RefResolver(base_uri=base_uri, referrer=schema)  # type: ignore[attr-defined]
        Validator = jsonschema.validators.validator_for(schema)  # type: ignore[attr-defined]
        Validator.check_schema(schema)
        validator = Validator(schema, resolver=resolver)
    except Exception:
        # Fallback for newer jsonschema without RefResolver, using $ref base via handlers
        Validator = jsonschema.validators.validator_for(schema)  # type: ignore[attr-defined]
        Validator.check_schema(schema)
        validator = Validator(schema)

    errors = sorted(validator.iter_errors(instance), key=lambda e: list(getattr(e, "path", [])))
    return [_format_error(e) for e in errors]


def validate_file(instance_path: Path, schema_path: Path) -> Tuple[bool, List[str]]:
    instance = _read_json(instance_path)
    schema = _load_schema(schema_path)
    errors = _validate_with_jsonschema(instance, schema, schema_path)
    return (len(errors) == 0, errors)
def _default_schema_for(instance_path: Path) -> Optional[Path]:
    name = instance_path.name.lower()
    if "spec" in name:
        cand = Path("schemas/run_spec.schema.json")
        if cand.exists():
            return cand
    if "log" in name:
        cand = Path("schemas/run_log.schema.json")
        if cand.exists():
            return cand
    return None


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="validate_json.py", add_help=True)
    ap.add_argument(
        "--instance",
        "-i",
        action="append",
        required=True,
        help="Path(s) or glob(s) to JSON instance file(s) to validate.",
    )
    ap.add_argument(
        "--schema",
        "-s",
        help="Path to JSON Schema. If omitted, attempts to infer from filename and ./schemas/* if present.",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Only emit errors; suppress per-file OK lines.",
    )
    args = ap.parse_args(argv)

    instance_paths = _iter_instance_paths(args.instance)
    if not instance_paths:
        _eprint("No instance files matched.")
        return 2

    schema_path: Optional[Path] = Path(args.schema) if args.schema else None
    failures = 0

    for ip in instance_paths:
        sp = schema_path or _default_schema_for(ip)
        if sp is None:
            _eprint(f"{ip}: No schema provided and no default schema found.")
            failures += 1
            continue
        try:
            ok, errors = validate_file(ip, sp)
        except Exception as e:
            _eprint(f"{ip}: VALIDATION_ERROR: {e}")
            failures += 1
            continue

        if ok:
            if not args.quiet:
                print(f"{ip}: OK")
        else:
            failures += 1
            _eprint(f"{ip}: FAIL ({len(errors)} issue(s))")
            for msg in errors[:200]:
                _eprint(f"  - {msg}")
            if len(errors) > 200:
                _eprint(f"  ... ({len(errors) - 200} more)")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
