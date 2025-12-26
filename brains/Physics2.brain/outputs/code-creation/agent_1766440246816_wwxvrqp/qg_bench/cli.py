"""qg_bench CLI.

This module intentionally keeps a small, dependency-light surface so the
benchmark pipeline can invoke it reliably in minimal environments.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple
EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_USAGE_ERROR = 2
EXIT_VALIDATION_ERROR = 3
def _eprint(*parts: object) -> None:
    print(*parts, file=sys.stderr)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ValueError(f"input file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON in {path}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("benchmark payload must be a JSON object")
    return data


def _schema_path() -> Path:
    # Expected layout: <repo_root>/schemas/benchmark.schema.json
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        cand = parent / "schemas" / "benchmark.schema.json"
        if cand.is_file():
            return cand
    return Path("schemas") / "benchmark.schema.json"


def _validate_payload(payload: Dict[str, Any], schema_file: Optional[Path] = None) -> Tuple[bool, str]:
    # Lightweight validation that works with or without jsonschema installed.
    schema_file = schema_file or _schema_path()
    schema: Optional[Dict[str, Any]] = None
    if schema_file.is_file():
        try:
            schema = json.loads(schema_file.read_text(encoding="utf-8"))
        except Exception:
            schema = None

    try:
        import jsonschema  # type: ignore
    except Exception:
        jsonschema = None  # type: ignore

    if schema and jsonschema:
        try:
            jsonschema.validate(instance=payload, schema=schema)
        except Exception as e:
            return False, str(e)

    # Minimal required keys for pipeline smoke-runs.
    if "case_id" not in payload or not isinstance(payload["case_id"], str) or not payload["case_id"].strip():
        return False, "missing or invalid required field: case_id"
    if "experiment" not in payload or not isinstance(payload["experiment"], dict):
        return False, "missing or invalid required field: experiment"
    if "name" not in payload["experiment"] or not isinstance(payload["experiment"]["name"], str):
        return False, "missing or invalid required field: experiment.name"
    return True, ""
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qg-bench", description="Minimal benchmark CLI.")
    p.add_argument("--version", action="version", version="qg-bench 0.1")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="Validate a benchmark JSON payload.")
    pv.add_argument("input", type=Path, help="Path to benchmark JSON file.")
    pv.add_argument("--schema", type=Path, default=None, help="Optional path to schema JSON file.")

    pr = sub.add_parser("run", help="Run a benchmark case (smoke-run).")
    pr.add_argument("input", type=Path, help="Path to benchmark JSON file.")
    pr.add_argument("--schema", type=Path, default=None, help="Optional path to schema JSON file.")
    pr.add_argument("-o", "--output", type=Path, default=None, help="Optional output JSON file.")
    pr.add_argument("--dry-run", action="store_true", help="Validate and echo resolved run plan only.")
    return p
def _run_case(payload: Dict[str, Any]) -> Dict[str, Any]:
    # This CLI does not execute heavy experiments; it standardizes an execution plan
    # so the rest of the pipeline can take over.
    exp = payload.get("experiment", {}) if isinstance(payload.get("experiment"), dict) else {}
    return {
        "case_id": payload.get("case_id"),
        "experiment": {"name": exp.get("name"), "params": exp.get("params", {})},
        "status": "planned",
    }


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        payload = _load_json(args.input)
    except ValueError as e:
        _eprint(f"ERROR: {e}")
        return EXIT_VALIDATION_ERROR

    ok, msg = _validate_payload(payload, schema_file=getattr(args, "schema", None))
    if not ok:
        _eprint(f"VALIDATION_ERROR: {msg}")
        return EXIT_VALIDATION_ERROR

    if args.cmd == "validate":
        return EXIT_OK

    if args.cmd == "run":
        result = _run_case(payload)
        if args.dry_run or args.output is None:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return EXIT_OK

    parser.error(f"unknown command: {args.cmd}")
    return EXIT_USAGE_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
