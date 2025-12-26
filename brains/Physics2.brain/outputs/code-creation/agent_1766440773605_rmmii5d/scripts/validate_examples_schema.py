#!/usr/bin/env python3
"""Validate repository example files against a JSON Schema.

- Discovers example files (default: examples/**.json|yml|yaml).
- Validates each file against a JSON Schema (default: auto-discover schema*.json).
- Emits a diff-like, pointer-addressed report for any violations and exits non-zero.

Intended for CI usage; output is stable and human-readable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Tuple
def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _load_data(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        return json.loads(_load_text(path))
    if path.suffix.lower() in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"PyYAML is required to read {path.name}: {e}") from e
        return yaml.safe_load(_load_text(path))
    raise ValueError(f"Unsupported example file type: {path}")

def _json_pointer(parts: Iterable[Any]) -> str:
    segs = []
    for p in parts:
        s = str(p).replace("~", "~0").replace("/", "~1")
        segs.append(s)
    return "/" + "/".join(segs) if segs else "/"

def _fmt_value(v: Any, limit: int = 240) -> str:
    try:
        s = json.dumps(v, ensure_ascii=False, sort_keys=True)
    except Exception:
        s = repr(v)
    if len(s) > limit:
        s = s[: limit - 3] + "..."
    return s
def _discover_schema(repo_root: Path) -> Path:
    candidates = []
    for rel in ("schema.json", "schemas/schema.json", "json_schema.json"):
        p = repo_root / rel
        if p.is_file():
            candidates.append(p)
    candidates += sorted(repo_root.glob("**/schema*.json"))
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "No schema found; pass --schema PATH (looked for schema.json and **/schema*.json)."
    )

def _discover_examples(repo_root: Path, root: str, patterns: Tuple[str, ...]) -> list[Path]:
    ex_root = repo_root / root
    if not ex_root.exists():
        return []
    files: list[Path] = []
    for pat in patterns:
        files.extend(sorted(ex_root.rglob(pat)))
    return [p for p in files if p.is_file()]
def _build_validator(schema: dict) -> Any:
    try:
        import jsonschema  # type: ignore
        from jsonschema.validators import validator_for  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "jsonschema is required for validation; add it to your CI dependencies."
        ) from e
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)

def _format_error(err: Any, instance: Any) -> str:
    ptr = _json_pointer(err.absolute_path)
    # Best-effort lookup of offending value.
    cur = instance
    try:
        for part in err.absolute_path:
            cur = cur[part]
        val = _fmt_value(cur)
    except Exception:
        val = "<unavailable>"
    schema_ptr = _json_pointer(err.absolute_schema_path)
    msg = (err.message or str(err)).strip()
    return "\n".join(
        [
            f"@@ {ptr}",
            f"- value: {val}",
            f"+ error: {msg}",
            f"+ schema: {schema_ptr}",
        ]
    )
def validate_examples(schema_path: Path, example_paths: list[Path]) -> int:
    schema = json.loads(_load_text(schema_path))
    validator = _build_validator(schema)

    any_fail = False
    for ex in example_paths:
        try:
            data = _load_data(ex)
        except Exception as e:
            any_fail = True
            sys.stdout.write(f"--- {ex.as_posix()}\n+++ parse_error\n+ {e}\n")
            continue

        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if not errors:
            continue

        any_fail = True
        sys.stdout.write(f"--- {ex.as_posix()}\n+++ schema_validation\n")
        for err in errors:
            sys.stdout.write(_format_error(err, data) + "\n")

    return 1 if any_fail else 0
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=None, help="Repository root (default: auto).")
    ap.add_argument("--schema", default=None, help="Path to JSON Schema file.")
    ap.add_argument("--examples-root", default="examples", help="Examples directory root.")
    ap.add_argument(
        "--patterns",
        nargs="*",
        default=["*.json", "*.yml", "*.yaml"],
        help="Example file glob patterns (recursive).",
    )
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    schema_path = Path(args.schema).resolve() if args.schema else _discover_schema(repo_root)
    example_paths = _discover_examples(repo_root, args.examples_root, tuple(args.patterns))

    if not example_paths:
        sys.stderr.write(f"No example files found under {args.examples_root!r}; nothing to validate.\n")
        return 0

    try:
        return validate_examples(schema_path, example_paths)
    except Exception as e:
        sys.stderr.write(f"Schema validation failed to run: {e}\n")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
