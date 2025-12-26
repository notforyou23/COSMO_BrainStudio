"""Deterministic benchmark computation.

This module reads a benchmark input JSON, validates it (optionally via JSON
Schema), computes deterministic summary statistics, and writes a normalized
output JSON.

The intention is to provide a stable end-to-end artifact for CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:  # Optional dependency; tests/CI are expected to install it.
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None  # type: ignore
Number = float


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _default_schema_path() -> Path:
    # outputs/src/benchmarks/compute.py -> outputs/schemas/benchmark.schema.json
    return Path(__file__).resolve().parents[2] / "schemas" / "benchmark.schema.json"


def _validate_with_schema(instance: Any, schema_path: Path) -> None:
    if jsonschema is None:
        raise RuntimeError("jsonschema is required for validation but is not installed.")
    schema = _read_json(schema_path)
    jsonschema.validate(instance=instance, schema=schema)
def _as_number_list(values: Any, case_id: str) -> List[Number]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"case {case_id!r} must have non-empty list 'values'")
    out: List[Number] = []
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"case {case_id!r} contains non-numeric value: {v!r}")
        out.append(float(v))
    return out


def _stats(values: Sequence[Number]) -> Dict[str, Any]:
    n = len(values)
    s = float(sum(values))
    mn = float(min(values))
    mx = float(max(values))
    mean = s / n
    # Deterministic "signature" so tests can detect any ordering changes.
    h = hashlib.sha256((",".join(f"{x:.12g}" for x in values)).encode("utf-8")).hexdigest()
    return {
        "count": n,
        "sum": s,
        "mean": mean,
        "min": mn,
        "max": mx,
        "sha256": h,
    }
def compute(input_obj: Mapping[str, Any]) -> Dict[str, Any]:
    """Compute a normalized output artifact from an input artifact."""
    if not isinstance(input_obj, Mapping):
        raise TypeError("benchmark input must be a JSON object")

    benchmark = input_obj.get("benchmark")
    if not isinstance(benchmark, Mapping):
        raise ValueError("input must contain object field 'benchmark'")
    name = benchmark.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("benchmark.name must be a non-empty string")
    cases = benchmark.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("benchmark.cases must be a non-empty list")

    out_cases: List[Dict[str, Any]] = []
    for i, c in enumerate(cases):
        if not isinstance(c, Mapping):
            raise ValueError(f"case at index {i} must be an object")
        cid = c.get("id", str(i))
        if not isinstance(cid, str) or not cid:
            raise ValueError(f"case at index {i} has invalid 'id'")
        values = _as_number_list(c.get("values"), cid)
        out_cases.append({"id": cid, "values": values, "stats": _stats(values)})

    # Normalize: stable ordering and canonical floats (via json dumps later).
    out_cases.sort(key=lambda x: x["id"])

    total_values = [v for c in out_cases for v in c["values"]]
    output: Dict[str, Any] = {
        "schema_version": input_obj.get("schema_version", 1),
        "artifact": "benchmark_output",
        "benchmark": {
            "name": name,
            "case_count": len(out_cases),
            "cases": out_cases,
            "overall": _stats(total_values),
        },
    }
    return output
def run(
    input_path: Path,
    output_path: Path,
    schema_path: Optional[Path] = None,
    validate_output: bool = True,
) -> Dict[str, Any]:
    input_obj = _read_json(input_path)
    schema_path = schema_path or _default_schema_path()
    if schema_path.exists():
        _validate_with_schema(input_obj, schema_path)
    output_obj = compute(input_obj)
    if validate_output and schema_path.exists():
        _validate_with_schema(output_obj, schema_path)
    _write_json(output_path, output_obj)
    return output_obj


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path, help="Path to benchmark input JSON")
    p.add_argument("output", type=Path, help="Path to write benchmark output JSON")
    p.add_argument("--schema", type=Path, default=None, help="Optional JSON Schema path")
    p.add_argument("--no-validate-output", action="store_true", help="Skip output validation")
    args = p.parse_args(argv)
    run(args.input, args.output, schema_path=args.schema, validate_output=not args.no_validate_output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
