#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except Exception as e:  # pragma: no cover
    raise SystemExit(f"ERROR: jsonschema is required (pip install jsonschema). Detail: {e}")
LEGACY_NAME_HINTS = {
    "results.json",
    "output.json",
    "metrics.json",
    "eval.json",
}
LEGACY_KEY_SETS = [
    {"config", "results"},
    {"metrics", "metadata"},
    {"scores", "details"},
]


def _discover_json_files(root: Path) -> list[Path]:
    candidates = []
    for p in root.rglob("*.json"):
        rp = p.as_posix()
        if "/.git/" in rp or "/.venv/" in rp or "/node_modules/" in rp:
            continue
        if rp.endswith("/outputs/schemas/benchmark_schema.json") or "/outputs/schemas/" in rp:
            continue
        if "/outputs/" in rp:
            candidates.append(p)
    return sorted(candidates)


def _fmt_path(path_parts) -> str:
    if not path_parts:
        return "$"
    out = "$"
    for part in path_parts:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += "." + str(part)
    return out


def _looks_legacy(path: Path, obj) -> bool:
    name = path.name.lower()
    if name in LEGACY_NAME_HINTS or any(name.endswith(suf) for suf in ("_results.json", "-results.json")):
        return True
    if isinstance(obj, dict):
        keys = set(obj.keys())
        if any(ks.issubset(keys) for ks in LEGACY_KEY_SETS):
            return True
        if "schema_version" in keys and "$schema" not in keys:
            return True
    return False
def _load_schema(schema_path: Path) -> dict:
    if not schema_path.exists():
        raise SystemExit(f"ERROR: Schema not found: {schema_path}")
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"ERROR: Failed to read schema JSON: {schema_path} ({e})")


def _validator(schema: dict, schema_path: Path):
    base_uri = schema_path.resolve().as_uri()
    resolver = jsonschema.RefResolver(base_uri=base_uri, referrer=schema)  # for local refs
    return jsonschema.Draft202012Validator(schema, resolver=resolver)


def _validate_file(p: Path, v, schema_name: str) -> list[str]:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"{p}: invalid JSON ({e})"]
    errors = sorted(v.iter_errors(data), key=lambda e: (len(list(e.absolute_path)), str(e.absolute_path)))
    msgs = []
    if errors:
        for e in errors[:50]:
            at = _fmt_path(e.absolute_path)
            msg = e.message
            if e.validator == "required" and isinstance(e.validator_value, list):
                missing = ", ".join(e.validator_value)
                msg = f"missing required field(s): {missing}"
            msgs.append(f"{p}:{at}: {msg}")
        extra = "" if len(errors) <= 50 else f" (showing first 50 of {len(errors)})"
        msgs.append(f"{p}: does not match {schema_name}{extra}")
    if _looks_legacy(p, data) and errors:
        msgs.append(
            f"{p}: appears to be a deprecated legacy/ad-hoc format. "
            "Migrate to the canonical benchmark output schema and rename away from generic "
            "names like results.json/output.json."
        )
    return msgs
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate benchmark output JSON files against outputs/schemas/benchmark_schema.json."
    )
    ap.add_argument("paths", nargs="*", help="Files or directories to scan (default: repo root).")
    ap.add_argument(
        "--schema",
        default="outputs/schemas/benchmark_schema.json",
        help="Path to JSON Schema (default: outputs/schemas/benchmark_schema.json).",
    )
    ap.add_argument("--fail-on-empty", action="store_true", help="Fail if no candidate JSON files are found.")
    args = ap.parse_args(argv)

    root = Path.cwd()
    schema_path = (root / args.schema).resolve()
    schema = _load_schema(schema_path)
    v = _validator(schema, schema_path)

    targets: list[Path] = []
    if args.paths:
        for s in args.paths:
            p = Path(s)
            if p.is_dir():
                targets.extend([q for q in p.rglob("*.json") if q.is_file()])
            elif p.is_file():
                targets.append(p)
    else:
        targets = _discover_json_files(root)

    targets = [t for t in sorted(set(t.resolve() for t in targets)) if t.suffix.lower() == ".json"]
    if not targets:
        if args.fail_on_empty:
            print("ERROR: No benchmark output JSON files discovered.", file=sys.stderr)
            return 2
        print("OK: No benchmark output JSON files discovered.")
        return 0

    schema_name = schema.get("$id") or schema_path.as_posix()
    all_msgs: list[str] = []
    for p in targets:
        if p.resolve() == schema_path:
            continue
        all_msgs.extend(_validate_file(p, v, schema_name))

    if all_msgs:
        print("VALIDATION_FAILED:")
        for m in all_msgs:
            print(" - " + m, file=sys.stderr)
        print(f"Checked {len(targets)} file(s): FAIL", file=sys.stderr)
        return 1
    print(f"Checked {len(targets)} file(s): OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
