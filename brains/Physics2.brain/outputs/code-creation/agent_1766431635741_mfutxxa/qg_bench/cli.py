\"\"\"Command line interface for qg_bench.

Implements a minimal, deterministic benchmark runner that:
1) loads schema.json,
2) ingests a JSONL dataset,
3) computes a couple of observables,
4) writes standardized results JSON with a reproducible hash/metadata block.
\"\"\"

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
def _pkg_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent.joinpath(*parts)


def _canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            rec = json.loads(s)
            if not isinstance(rec, dict):
                raise ValueError("Each JSONL line must be an object/dict.")
            records.append(rec)
    return records


def _sha256_hex(parts: Iterable[bytes]) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.hexdigest()
def _compute_observables(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    \"\"\"Compute 1–2 observables from ingested records.

    Expected record shape (example):
      {"id": "...", "y_true": 0/1, "y_pred": 0/1, "latency_ms": float}
    \"\"\"
    try:
        from .observables import accuracy, mean_latency_ms  # type: ignore
    except Exception:
        accuracy = None
        mean_latency_ms = None

    out: Dict[str, Any] = {}
    if accuracy is not None:
        out["accuracy"] = float(accuracy(records))
    else:
        correct = total = 0
        for r in records:
            if "y_true" in r and "y_pred" in r:
                total += 1
                correct += int(r["y_true"] == r["y_pred"])
        out["accuracy"] = (correct / total) if total else None

    if mean_latency_ms is not None:
        out["mean_latency_ms"] = float(mean_latency_ms(records))
    else:
        vals = [float(r["latency_ms"]) for r in records if "latency_ms" in r]
        out["mean_latency_ms"] = (sum(vals) / len(vals)) if vals else None
    return out
def run_benchmark(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    \"\"\"Run the benchmark and write results JSON; returns the results dict.\"\"\"
    p = argparse.ArgumentParser(prog="run_benchmark", description="Run qg_bench on a dataset.")
    p.add_argument("--schema", type=str, default=str(_pkg_path("schema.json")))
    p.add_argument("--data", type=str, default=str(_pkg_path("data", "example_dataset.jsonl")))
    p.add_argument("--output", type=str, default="results.json")
    args = p.parse_args(argv)

    schema_path, data_path, out_path = Path(args.schema), Path(args.data), Path(args.output)
    schema = _load_json(schema_path)
    records = _load_jsonl(data_path)
    observables = _compute_observables(records)

    try:
        from . import __version__ as pkg_version  # type: ignore
    except Exception:
        pkg_version = "0.0.0"

    inputs_fingerprint = _sha256_hex([
        schema_path.read_bytes(),
        b"\n",
        data_path.read_bytes(),
        b"\n",
        _canonical_dumps({"schema": str(schema_path), "data": str(data_path)}).encode("utf-8"),
    ])

    results: Dict[str, Any] = {
        "schema_id": schema.get("$id") or schema.get("title") or "qg_bench_results",
        "schema_version": schema.get("version") or schema.get("$schema"),
        "metadata": {
            "tool": "qg_bench",
            "tool_version": pkg_version,
            "inputs": {"schema_path": str(schema_path), "data_path": str(data_path)},
            "record_count": len(records),
            "inputs_sha256": inputs_fingerprint,
        },
        "observables": observables,
    }

    results_hash = _sha256_hex([_canonical_dumps(results).encode("utf-8")])
    results["metadata"]["results_sha256"] = results_hash

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_canonical_dumps(results) + "\n", encoding="utf-8")
    return results


def main() -> None:
    run_benchmark(None)


if __name__ == "__main__":
    main()
