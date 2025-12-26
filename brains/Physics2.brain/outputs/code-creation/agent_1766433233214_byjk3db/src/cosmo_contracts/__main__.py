"""cosmo_contracts package entry point.

Enables: python -m cosmo_contracts <command> ...

Commands focus on:
- injecting/updating standardized Contract sections into v0.1 benchmarks markdown
- validating contracts and reporting implementation compliance
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
def _json_dump(obj: Any) -> None:
    json.dump(obj, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
def _import(name: str):
    try:
        module = __import__(name, fromlist=["*"])
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            f"Failed to import {name!r}. The package installation may be incomplete.\n{e}"
        )
    return module
def cmd_inject(args: argparse.Namespace) -> int:
    md = _import("cosmo_contracts.markdown")
    in_path = Path(args.benchmarks).expanduser()
    out_path = Path(args.out).expanduser() if args.out else None
    res = md.inject_contract_sections(
        in_path=in_path,
        out_path=out_path,
        strict=args.strict,
    )
    if args.format == "json":
        _json_dump(res)
    else:
        sys.stdout.write(res.get("summary", "ok") + "\n")
    return 0
def cmd_validate(args: argparse.Namespace) -> int:
    schema = _import("cosmo_contracts.schema")
    contract_path = Path(args.contract).expanduser()
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    ok, diag = schema.validate_contract(data)
    out = {"ok": bool(ok), "diagnostics": diag}
    if args.format == "json":
        _json_dump(out)
    else:
        sys.stdout.write(("PASS" if ok else "FAIL") + "\n")
        if diag:
            sys.stdout.write(str(diag) + "\n")
    return 0 if ok else 2
def cmd_compliance(args: argparse.Namespace) -> int:
    api = _import("cosmo_contracts")
    if not hasattr(api, "check_compliance"):
        raise SystemExit(
            "cosmo_contracts.check_compliance is not available; update the package."
        )
    impl_path = Path(args.implementation).expanduser() if args.implementation else None
    contract_path = Path(args.contract).expanduser() if args.contract else None
    report = api.check_compliance(
        contract_path=contract_path,
        implementation_path=impl_path,
        implementation_id=args.implementation_id,
        run=args.run,
        timeout_s=args.timeout_s,
    )
    if args.format == "json":
        _json_dump(report)
    else:
        sys.stdout.write(report.get("summary", "ok") + "\n")
    return 0 if report.get("pass", False) else 2
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cosmo_contracts", add_help=True)
    p.add_argument("--format", choices=["json", "text"], default="json")
    sub = p.add_subparsers(dest="cmd", required=True)

    inj = sub.add_parser("inject", help="Inject/update Contract sections in benchmarks_v0_1.md")
    inj.add_argument("benchmarks", help="Path to benchmarks_v0_1.md")
    inj.add_argument("--out", help="Optional output path; default edits in-place")
    inj.add_argument("--strict", action="store_true", help="Fail if parsing is ambiguous")
    inj.set_defaults(func=cmd_inject)

    val = sub.add_parser("validate", help="Validate a contract JSON file against the schema")
    val.add_argument("contract", help="Path to a contract JSON file")
    val.set_defaults(func=cmd_validate)

    comp = sub.add_parser("compliance", help="Check implementation compliance with a contract")
    comp.add_argument("--contract", required=True, help="Contract JSON file")
    comp.add_argument("--implementation", help="Implementation file or module path")
    comp.add_argument("--implementation-id", help="Implementation identifier to report")
    comp.add_argument(
        "--run",
        action="store_true",
        help="Actually execute implementation (otherwise just structural checks if supported)",
    )
    comp.add_argument("--timeout-s", type=float, default=30.0)
    comp.set_defaults(func=cmd_compliance)

    return p
def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    return int(ns.func(ns))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
