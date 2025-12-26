"""Benchmarks CLI.

This CLI is used by developers and CI to generate deterministic benchmark
artifacts under the repository's ``outputs/`` directory.

Typical use:
  python -m benchmarks.cli example
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from . import compute as compute_mod
from . import schema as schema_mod
def _outputs_dir() -> Path:
    # outputs/src/benchmarks/cli.py -> outputs/
    return Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def make_example_input() -> Dict[str, Any]:
    """Return a deterministic example benchmark input artifact."""
    return {
        "schema_version": 1,
        "artifact": "benchmark_input",
        "benchmark": {
            "name": "example",
            "cases": [
                {"id": "case_a", "values": [1, 2, 3, 4]},
                {"id": "case_b", "values": [-2.5, 0, 2.5, 5]},
            ],
        },
    }


def run_end_to_end(
    *,
    outdir: Path,
    schema_path: Optional[Path] = None,
    overwrite: bool = False,
) -> Dict[str, Path]:
    """Generate example input+output JSON and validate them against schema."""
    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    schema_path = schema_path or schema_mod.default_schema_path()

    input_path = outdir / "example.input.json"
    output_path = outdir / "example.output.json"

    if not overwrite and (input_path.exists() or output_path.exists()):
        raise FileExistsError(f"refusing to overwrite existing artifacts in {outdir}")

    input_obj = make_example_input()
    schema_mod.validate_or_raise(input_obj, schema_path=schema_path)
    _write_json(input_path, input_obj)

    # Compute module also validates if schema exists; we validate explicitly for clear errors.
    output_obj = compute_mod.compute(input_obj)
    schema_mod.validate_or_raise(output_obj, schema_path=schema_path)
    _write_json(output_path, output_obj)

    return {"input": input_path, "output": output_path, "schema": schema_path}
def _cmd_example(args: argparse.Namespace) -> int:
    outdir = Path(args.outdir) if args.outdir else (_outputs_dir() / "benchmarks")
    paths = run_end_to_end(outdir=outdir, schema_path=Path(args.schema) if args.schema else None, overwrite=args.overwrite)
    print(str(paths["input"]))
    print(str(paths["output"]))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    schema_path = Path(args.schema) if args.schema else None
    compute_mod.run(Path(args.input), Path(args.output), schema_path=schema_path, validate_output=not args.no_validate_output)
    print(str(Path(args.output)))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    schema_path = Path(args.schema) if args.schema else schema_mod.default_schema_path()
    obj = _read_json(Path(args.path))
    schema_mod.validate_or_raise(obj, schema_path=schema_path)
    print("OK")
    return 0
def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="benchmarks", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("example", help="Generate deterministic example artifacts under outputs/")
    ex.add_argument("--outdir", default=None, help="Output directory (default: outputs/benchmarks)")
    ex.add_argument("--schema", default=None, help="Optional schema path (default: outputs/schemas/benchmark.schema.json)")
    ex.add_argument("--overwrite", action="store_true", help="Overwrite existing artifacts")
    ex.set_defaults(func=_cmd_example)

    run = sub.add_parser("run", help="Run benchmark from an input JSON to an output JSON")
    run.add_argument("input", help="Path to benchmark input JSON")
    run.add_argument("output", help="Path to write benchmark output JSON")
    run.add_argument("--schema", default=None, help="Optional schema path")
    run.add_argument("--no-validate-output", action="store_true", help="Skip output validation")
    run.set_defaults(func=_cmd_run)

    val = sub.add_parser("validate", help="Validate a JSON artifact against the benchmark schema")
    val.add_argument("path", help="Path to JSON file to validate")
    val.add_argument("--schema", default=None, help="Optional schema path")
    val.set_defaults(func=_cmd_validate)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
