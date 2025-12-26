"""Benchmark runner.

Loads each task contract, runs reference and candidate implementations, and
compares outputs using centralized utilities with CI-friendly failure output.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
import argparse
import json
import sys

from .compare import compare_outputs
from .contract import load_contract
def _load_callable(spec: str) -> Callable[..., Any]:
    """Load a callable from 'pkg.mod:attr' or 'pkg.mod.attr'."""
    if ":" in spec:
        mod, attr = spec.split(":", 1)
    else:
        mod, attr = spec.rsplit(".", 1)
    obj = getattr(import_module(mod), attr)
    if not callable(obj):
        raise TypeError(f"Loaded object is not callable: {spec}")
    return obj


def _iter_contract_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(str(path))
    exts = ("*.json", "*.yaml", "*.yml")
    out: list[Path] = []
    for pat in exts:
        out.extend(sorted(path.glob(pat)))
    return out
@dataclass
class RunResult:
    task_id: str
    passed: bool
    failures: list[str]  # already formatted for CI


def run_task(contract_path: Path, candidate: Callable[..., Any]) -> RunResult:
    contract = load_contract(contract_path)
    # contract is responsible for validating required metadata/tolerances
    task_id = getattr(contract, "task_id", None) or getattr(contract, "id", None) or contract_path.stem

    cases: Iterable[Any] = getattr(contract, "cases", None)
    if cases is None and hasattr(contract, "make_cases"):
        cases = contract.make_cases()
    if cases is None:
        raise ValueError(f"Contract {contract_path} provides no cases/make_cases")

    reference = getattr(contract, "reference", None)
    if reference is None and hasattr(contract, "get_reference_callable"):
        reference = contract.get_reference_callable()
    if not callable(reference):
        raise ValueError(f"Contract {contract_path} provides no callable reference implementation")

    # Tolerances and policies are contract-defined; compare_outputs owns semantics.
    tolerances = getattr(contract, "tolerances", None)
    nan_policy = getattr(contract, "nan_policy", None)
    inf_policy = getattr(contract, "inf_policy", None)

    failures: list[str] = []
    for i, case in enumerate(cases):
        # Support either raw input or dict-like {"input": ...}
        inp = case.get("input") if hasattr(case, "get") else case
        meta = case.get("meta", {}) if hasattr(case, "get") else {}
        try:
            ref_out = reference(inp)
            cand_out = candidate(inp)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{task_id} case={i} EXEC_ERROR: {e.__class__.__name__}: {e}")
            continue

        cmp_res = compare_outputs(
            expected=ref_out,
            actual=cand_out,
            tolerances=tolerances,
            nan_policy=nan_policy,
            inf_policy=inf_policy,
            context={"task": task_id, "case": i, **(meta or {})},
        )
        if not cmp_res.ok:
            # Keep output terse but actionable for CI logs.
            failures.append(cmp_res.format(max_mismatches=10))
    return RunResult(task_id=task_id, passed=not failures, failures=failures)
def run(contracts: Sequence[Path], candidate_spec: str) -> int:
    candidate = _load_callable(candidate_spec)
    all_failures: list[str] = []
    any_ran = False

    for root in contracts:
        for cpath in _iter_contract_paths(root):
            any_ran = True
            res = run_task(cpath, candidate)
            if not res.passed:
                all_failures.extend(res.failures)

    if not any_ran:
        print("No contracts found.", file=sys.stderr)
        return 2

    if all_failures:
        for line in all_failures:
            print(line, file=sys.stderr)
        print(f"FAILURES: {len(all_failures)}", file=sys.stderr)
        return 1

    print("OK")  # keep success output minimal for CI
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run benchmark contracts and compare candidate vs reference.")
    p.add_argument("contracts", nargs="+", help="Contract file(s) or directory(ies)")
    p.add_argument("--candidate", required=True, help="Callable spec: pkg.mod:func (or pkg.mod.func)")
    args = p.parse_args(list(argv) if argv is not None else None)
    paths = [Path(s) for s in args.contracts]
    return run(paths, args.candidate)


if __name__ == "__main__":
    raise SystemExit(main())
