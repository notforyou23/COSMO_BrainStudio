#!/usr/bin/env python3
"""Run the project's artifact QA gate.

This entrypoint is designed for CI/local execution: it fails fast (non-zero exit)
when any gate fails (including ID integrity) and ensures logs are written to
outputs/logs/ via the artifact gate's logging utilities.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_import_path(root: Path) -> None:
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _default_outputs_dir(root: Path) -> Path:
    return root / "outputs"


def _parse_args(root: Path) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run artifact gate (fails non-zero on violations).")
    p.add_argument("--artifacts-dir", type=str, default=None, help="Optional path to artifacts directory.")
    p.add_argument("--outputs-dir", type=str, default=str(_default_outputs_dir(root)), help="Outputs dir (logs under outputs/logs).")
    p.add_argument("--strict", action="store_true", help="Treat warnings as failures if supported by gate.")
    p.add_argument("--quiet", action="store_true", help="Minimize stdout; logs still written by gate.")
    return p.parse_args()


def _coerce_result_to_exit_code(result) -> int:
    if result is None:
        return 0
    if isinstance(result, bool):
        return 0 if result else 1
    if isinstance(result, int):
        return 0 if result == 0 else int(result)
    if isinstance(result, dict):
        for k in ("passed", "ok", "success"):
            if k in result and isinstance(result[k], bool):
                return 0 if result[k] else 1
        for k in ("exit_code", "code", "status"):
            if k in result and isinstance(result[k], int):
                return 0 if result[k] == 0 else int(result[k])
    passed = getattr(result, "passed", None)
    if isinstance(passed, bool):
        return 0 if passed else 1
    exit_code = getattr(result, "exit_code", None)
    if isinstance(exit_code, int):
        return 0 if exit_code == 0 else int(exit_code)
    return 0


def _run_gate(artifacts_dir: Path | None, outputs_dir: Path, strict: bool, quiet: bool) -> int:
    try:
        from src.artifact_gate import run_artifact_gate  # type: ignore
    except Exception:
        run_artifact_gate = None

    if run_artifact_gate is not None:
        try:
            return _coerce_result_to_exit_code(
                run_artifact_gate(
                    artifacts_dir=artifacts_dir,
                    outputs_dir=outputs_dir,
                    strict=strict,
                    quiet=quiet,
                )
            )
        except TypeError:
            pass

    try:
        import src.artifact_gate as ag  # type: ignore
    except Exception as e:
        print(f"ERROR: Failed to import src.artifact_gate: {e}", file=sys.stderr)
        return 2

    for fn_name in ("main", "run", "run_gate", "artifact_gate_main"):
        fn = getattr(ag, fn_name, None)
        if callable(fn):
            try:
                return _coerce_result_to_exit_code(
                    fn(
                        artifacts_dir=artifacts_dir,
                        outputs_dir=outputs_dir,
                        strict=strict,
                        quiet=quiet,
                    )
                )
            except TypeError:
                try:
                    return _coerce_result_to_exit_code(fn())
                except Exception as e:
                    print(f"ERROR: Gate execution failed: {e}", file=sys.stderr)
                    return 2
            except Exception as e:
                print(f"ERROR: Gate execution failed: {e}", file=sys.stderr)
                return 2

    GateCls = getattr(ag, "ArtifactGate", None)
    if GateCls is not None:
        try:
            gate = GateCls(artifacts_dir=artifacts_dir, outputs_dir=outputs_dir, strict=strict, quiet=quiet)
        except TypeError:
            gate = GateCls()
        for method_name in ("run", "execute", "evaluate"):
            m = getattr(gate, method_name, None)
            if callable(m):
                try:
                    return _coerce_result_to_exit_code(m())
                except Exception as e:
                    print(f"ERROR: Gate execution failed: {e}", file=sys.stderr)
                    return 2

    print("ERROR: Could not find a runnable artifact gate entrypoint in src.artifact_gate.", file=sys.stderr)
    return 2


def main() -> int:
    root = _repo_root()
    _ensure_import_path(root)

    args = _parse_args(root)
    artifacts_dir = Path(args.artifacts_dir).resolve() if args.artifacts_dir else None
    outputs_dir = Path(args.outputs_dir).resolve()

    os.environ.setdefault("COSMO_OUTPUTS_DIR", str(outputs_dir))

    exit_code = _run_gate(artifacts_dir=artifacts_dir, outputs_dir=outputs_dir, strict=bool(args.strict), quiet=bool(args.quiet))
    if not args.quiet:
        print(json.dumps({"artifact_gate_exit_code": exit_code, "outputs_dir": str(outputs_dir)}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
