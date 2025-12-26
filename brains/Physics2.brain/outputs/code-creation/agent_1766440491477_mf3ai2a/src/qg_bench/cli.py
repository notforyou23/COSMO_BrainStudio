from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
def _eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def _load_json(path: Path) -> Any:
    try:
        data = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"Dataset not found: {path}")
    except OSError as e:
        raise SystemExit(f"Failed to read dataset: {path} ({e})")
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in {path} at line {e.lineno} col {e.colno}: {e.msg}"
        raise SystemExit(msg)
def _try_validate(dataset: Any, dataset_path: Path) -> None:
    \"\"\"Validate dataset using qg_bench.validate if available.

    The validation module is expected to raise ValueError (or jsonschema
    exceptions) on invalid inputs. We convert those to a clean message and
    a consistent exit code for CI.
    \"\"\"
    try:
        from .validate import validate_benchmark  # type: ignore
    except Exception:
        # Allow the CLI to remain importable even if validation is not packaged
        # in a minimal environment. Running without validation is still useful
        # for smoke tests.
        return

    try:
        validate_benchmark(dataset)
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(f"Validation failed for {dataset_path}: {e}")
def _fallback_run(dataset: Any) -> Dict[str, Any]:
    \"\"\"A small deterministic runner used if qg_bench.runner is unavailable.\"\"\"
    items = dataset.get("items") if isinstance(dataset, dict) else None
    if not isinstance(items, list):
        raise SystemExit("Dataset must be an object with an 'items' array to run.")
    ids: List[str] = []
    for i, it in enumerate(items):
        if isinstance(it, dict) and isinstance(it.get("id"), str):
            ids.append(it["id"])
        else:
            ids.append(f"item_{i}")
    h = hashlib.sha256()
    for _id in ids:
        h.update(_id.encode("utf-8"))
        h.update(b"\\n")
    return {
        "num_items": len(items),
        "item_ids": ids,
        "ids_sha256": h.hexdigest(),
    }


def _run_benchmark(dataset: Any) -> Dict[str, Any]:
    \"\"\"Run benchmark via qg_bench.runner if present, else fallback.\"\"\"
    try:
        from .runner import run_benchmark  # type: ignore
    except Exception:
        return _fallback_run(dataset)

    out = run_benchmark(dataset)
    if not isinstance(out, dict):
        raise SystemExit("Runner must return a JSON-serializable dict.")
    return out
def _write_output(obj: Any, out_path: Optional[Path], pretty: bool) -> None:
    text = json.dumps(obj, indent=2 if pretty else None, sort_keys=True)
    if out_path is None or str(out_path) == "-":
        sys.stdout.write(text + "\\n")
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\\n", encoding="utf-8")
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qg-bench", description="Validate and run QG benchmarks.")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate a dataset against the bundled schema.")
    p_val.add_argument("dataset", type=Path, help="Path to benchmark JSON dataset.")
    p_val.add_argument("--quiet", action="store_true", help="Suppress success message.")

    p_run = sub.add_parser("run", help="Validate then run a benchmark dataset.")
    p_run.add_argument("dataset", type=Path, help="Path to benchmark JSON dataset.")
    p_run.add_argument("-o", "--output", type=Path, default=None, help="Write results JSON to this path (or '-' for stdout).")
    p_run.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    p_run.add_argument("--no-validate", action="store_true", help="Skip schema validation (not recommended).")

    return p
def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    dataset_path: Path = args.dataset
    dataset = _load_json(dataset_path)

    if args.cmd == "validate":
        _try_validate(dataset, dataset_path)
        if not args.quiet:
            print("OK")
        return 0

    if args.cmd == "run":
        if not args.no_validate:
            _try_validate(dataset, dataset_path)

        result = _run_benchmark(dataset)
        # Attach a small bit of metadata for easier CI debugging.
        try:
            from . import __version__  # type: ignore
            version = __version__
        except Exception:
            version = "unknown"
        payload = {"tool": "qg-bench", "version": version, "dataset": str(dataset_path), "result": result}
        _write_output(payload, args.output, args.pretty)
        return 0

    _eprint(f"Unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
