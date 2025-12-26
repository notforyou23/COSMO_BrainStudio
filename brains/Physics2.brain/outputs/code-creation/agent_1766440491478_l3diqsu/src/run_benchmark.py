"""CLI to run a benchmark contract, write outputs, and diff against golden.

This runner is intentionally dependency-free and relies on src.benchmark_contract.
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Tuple

from . import benchmark_contract as bc
def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]
def _load_inputs(path: Path | None) -> Mapping[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
def _load_callable(spec: str):
    """Load a callable from 'mod:attr' or 'mod.attr' strings."""
    mod_name, attr = None, None
    if ":" in spec:
        mod_name, attr = spec.split(":", 1)
    elif "." in spec:
        mod_name, attr = spec.rsplit(".", 1)
    if mod_name:
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, attr)
        if not callable(fn):
            raise TypeError(f"reference '{spec}' is not callable")
        return fn
    # Fallback built-ins.
    if spec == "echo":
        return lambda inputs: inputs
    raise ValueError(f"unrecognized reference algorithm spec: {spec!r}")
def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)
def _num_ok(a: float, b: float, tol: bc.Tolerance) -> bool:
    if math.isnan(a) or math.isnan(b):
        return tol.nan_equal and math.isnan(a) and math.isnan(b)
    return abs(a - b) <= tol.abs + tol.rel * abs(b)
def _diff(a: Any, b: Any, tol: bc.Tolerance, path: str = "$") -> Tuple[bool, str]:
    """Return (ok, message). Message is non-empty only on first failure."""
    if _is_number(a) and _is_number(b):
        ok = _num_ok(float(a), float(b), tol)
        if ok:
            return True, ""
        return False, f"numeric mismatch at {path}: got {a!r}, expected {b!r}"
    if isinstance(a, str) or isinstance(a, bool) or a is None:
        return (a == b), ("" if a == b else f"value mismatch at {path}: got {a!r}, expected {b!r}")
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False, f"length mismatch at {path}: got {len(a)}, expected {len(b)}"
        for i, (ai, bi) in enumerate(zip(a, b)):
            ok, msg = _diff(ai, bi, tol, f"{path}[{i}]")
            if not ok:
                return False, msg
        return True, ""
    if isinstance(a, dict) and isinstance(b, dict):
        ak, bk = set(a.keys()), set(b.keys())
        if ak != bk:
            missing = sorted(bk - ak)
            extra = sorted(ak - bk)
            return False, f"key mismatch at {path}: missing={missing}, extra={extra}"
        for k in sorted(ak):
            ok, msg = _diff(a[k], b[k], tol, f"{path}.{k}")
            if not ok:
                return False, msg
        return True, ""
    return (a == b), ("" if a == b else f"type/value mismatch at {path}: got {a!r}, expected {b!r}")
def run(contract_path: Path, run_dir: Path | None = None) -> int:
    root = _project_root()
    contract = bc.load_contract(contract_path)
    out_path, gold_path, in_path = bc.resolve_io_paths(contract, root, run_dir=run_dir)
    bc.validate_artifact_paths(out_path, gold_path, in_path)

    inputs = _load_inputs(in_path)
    algo_spec = str(contract["reference"]["algorithm"])
    algo = _load_callable(algo_spec)
    outputs = algo(inputs)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(outputs, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    golden = json.loads(gold_path.read_text(encoding="utf-8"))
    tol = bc.get_tolerance(contract)
    ok, msg = _diff(outputs, golden, tol)
    if ok:
        print(f"PASS diff within tolerance (abs={tol.abs}, rel={tol.rel})")
        print(f"wrote: {out_path.relative_to(root)}")
        return 0
    print("FAIL diff outside tolerance")
    print(msg)
    print(f"wrote: {out_path.relative_to(root)}")
    return 2
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run benchmark contract and diff outputs.")
    p.add_argument("--contract", default=str(bc.DEFAULT_CONTRACT_PATH), help="Path to contract JSON")
    p.add_argument("--run-dir", default=None, help="Override run dir (relative to repo root)")
    args = p.parse_args(argv)

    contract_path = (Path(args.contract) if Path(args.contract).is_absolute() else _project_root() / args.contract)
    run_dir = Path(args.run_dir) if args.run_dir else None
    return run(contract_path, run_dir=run_dir)


if __name__ == "__main__":
    raise SystemExit(main())
