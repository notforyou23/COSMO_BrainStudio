"""Benchmark runner for qg_bench.

This module provides a tiny, deterministic runner that:
- loads a JSON dataset,
- validates it against the bundled JSON Schema,
- computes a minimal exact-match score, and
- emits JSON results (stdout or a file).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import jsonschema
try:
    from importlib.resources import files as _files  # py3.9+
except Exception:  # pragma: no cover
    from importlib_resources import files as _files  # type: ignore


def _schema() -> Dict[str, Any]:
    schema_path = _files("qg_bench").joinpath("schemas/benchmark.schema.json")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_dataset(data: Dict[str, Any]) -> None:
    """Validate a benchmark dataset dict against the bundled schema."""
    schema = _schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if not errors:
        return
    e = errors[0]
    loc = "$" + "".join(f"[{p!r}]" if isinstance(p, str) else f"[{p}]" for p in e.absolute_path)
    msg = f"Dataset validation failed at {loc}: {e.message}"
    raise ValueError(msg)
def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


@dataclass(frozen=True)
class RunResult:
    dataset_path: str
    n_items: int
    accuracy: float
    scores: List[Dict[str, Any]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dataset_path": self.dataset_path,
            "n_items": self.n_items,
            "accuracy": self.accuracy,
            "scores": self.scores,
        }
def load_dataset(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Dataset JSON must be an object at the top level.")
    return data


def run_benchmark(dataset_path: Path) -> RunResult:
    """Run the minimal benchmark (exact match on prediction vs reference)."""
    dataset = load_dataset(dataset_path)
    validate_dataset(dataset)

    items = dataset.get("items") or []
    scores: List[Dict[str, Any]] = []
    total = 0.0
    for it in items:
        # Schema ensures these exist and are strings.
        iid = it.get("id")
        pred = it.get("prediction", "")
        ref = it.get("reference", "")
        score = 1.0 if _normalize(pred) == _normalize(ref) else 0.0
        scores.append({"id": iid, "score": score})
        total += score

    n = len(items)
    acc = (total / n) if n else 0.0
    return RunResult(dataset_path=str(dataset_path), n_items=n, accuracy=acc, scores=scores)
def _dump_json(obj: Any, fp) -> None:
    json.dump(obj, fp, ensure_ascii=False, sort_keys=True, indent=2)
    fp.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="qg-bench", description="Run qg_bench benchmark on a dataset JSON.")
    p.add_argument("dataset", type=Path, help="Path to benchmark dataset JSON.")
    p.add_argument("-o", "--output", type=Path, default=None, help="Write results JSON to this file.")
    args = p.parse_args(argv)

    result = run_benchmark(args.dataset).as_dict()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            _dump_json(result, f)
    else:
        _dump_json(result, sys.stdout)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
