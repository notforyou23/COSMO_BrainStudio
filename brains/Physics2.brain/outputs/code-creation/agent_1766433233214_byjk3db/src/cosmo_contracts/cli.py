# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
@dataclass
class ComplianceResult:
    benchmark_id: str
    implementation: str
    passed: bool
    diagnostics: Any = None

    @classmethod
    def from_json(cls, obj: Dict[str, Any], source: str) -> "ComplianceResult":
        missing = [k for k in ("benchmark_id", "implementation", "pass") if k not in obj]
        if missing:
            raise ValueError(f"{source}: missing required fields: {', '.join(missing)}")
        return cls(
            benchmark_id=str(obj["benchmark_id"]),
            implementation=str(obj["implementation"]),
            passed=bool(obj["pass"]),
            diagnostics=obj.get("diagnostics"),
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "implementation": self.implementation,
            "pass": self.passed,
            "diagnostics": self.diagnostics,
        }
def _try_import(path: str):
    try:
        return importlib.import_module(path)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            f"Failed to import '{path}'. Ensure cosmo_contracts is installed with its dependencies.\n"
            f"Underlying error: {type(e).__name__}: {e}"
        ) from e
def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in {path}: {e}") from e


def _load_report_files(paths: Iterable[Path]) -> List[ComplianceResult]:
    results: List[ComplianceResult] = []
    for p in paths:
        obj = _read_json(p)
        if isinstance(obj, dict):
            results.append(ComplianceResult.from_json(obj, str(p)))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if not isinstance(item, dict):
                    raise SystemExit(f"{p}[{i}]: expected object, got {type(item).__name__}")
                results.append(ComplianceResult.from_json(item, f"{p}[{i}]"))
        else:
            raise SystemExit(f"{p}: expected object or array, got {type(obj).__name__}")
    return results
def _aggregate(results: List[ComplianceResult]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    by_benchmark: Dict[str, Dict[str, Any]] = {}
    for r in results:
        b = by_benchmark.setdefault(r.benchmark_id, {"passed": 0, "failed": 0, "results": []})
        b["passed" if r.passed else "failed"] += 1
        b["results"].append(r.to_json())
    return {"summary": {"total": total, "passed": passed, "failed": failed}, "by_benchmark": by_benchmark}
def cmd_sync(args: argparse.Namespace) -> int:
    md_path = Path(args.benchmarks_md)
    out_path = Path(args.out) if args.out else md_path
    markdown = _try_import("cosmo_contracts.markdown")
    if not hasattr(markdown, "rewrite_with_contracts"):
        raise SystemExit("cosmo_contracts.markdown.rewrite_with_contracts is required for 'sync'.")
    new_text = markdown.rewrite_with_contracts(md_path.read_text(encoding="utf-8"))
    if args.check:
        if new_text != md_path.read_text(encoding="utf-8"):
            sys.stdout.write("contracts_out_of_date\n")
            return 2
        sys.stdout.write("contracts_up_to_date\n")
        return 0
    out_path.write_text(new_text, encoding="utf-8")
    sys.stdout.write(f"written:{out_path}\n")
    return 0
def cmd_validate(args: argparse.Namespace) -> int:
    # Two modes:
    # (A) Validate compliance-report JSON files (always supported).
    # (B) If cosmo_contracts has a validator API, run it and emit a report.
    if args.reports:
        results = _load_report_files([Path(p) for p in args.reports])
        report = _aggregate(results)
    else:
        validator = _try_import("cosmo_contracts")
        if not hasattr(validator, "validate_compliance"):
            raise SystemExit(
                "No reports provided and cosmo_contracts.validate_compliance not available. "
                "Provide --reports or install full cosmo_contracts package."
            )
        report = validator.validate_compliance(
            benchmarks_md=Path(args.benchmarks_md) if args.benchmarks_md else None,
            implementations=args.implementations or [],
        )

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")

    failed = int(report.get("summary", {}).get("failed", 0))
    return 1 if failed else 0
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cosmo-contracts", description="Contract section sync + compliance validation")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sync", help="Add/update standardized Contract sections in v0.1 benchmark markdown")
    s.add_argument("benchmarks_md", help="Path to benchmarks_v0_1.md (input; also output if --out not set)")
    s.add_argument("--out", help="Write updated markdown to this path (default: in-place)")
    s.add_argument("--check", action="store_true", help="Do not write; exit 0 if up-to-date else 2")
    s.set_defaults(func=cmd_sync)

    v = sub.add_parser("validate", help="Validate implementation contract compliance and emit a report")
    v.add_argument("--benchmarks-md", dest="benchmarks_md", help="Optional markdown path for API-driven validation")
    v.add_argument("--implementations", nargs="*", help="Optional implementation identifiers for API-driven validation")
    v.add_argument("--reports", nargs="*", help="Paths to JSON compliance reports emitted by implementations")
    v.add_argument("--out", help="Write JSON report to this file (default: stdout)")
    v.set_defaults(func=cmd_validate)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except SystemExit:
        raise
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"error:{type(e).__name__}:{e}\n")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
