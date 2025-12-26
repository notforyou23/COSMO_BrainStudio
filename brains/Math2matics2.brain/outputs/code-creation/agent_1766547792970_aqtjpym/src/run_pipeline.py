"""Main pipeline entrypoint.

This module resolves all output artifacts through the shared OUTPUT_DIR utility
and ensures required directories exist (no hard-coded /outputs paths).
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Tuple


def _load_output_utils():
    """Import shared output utilities; fall back to a safe local implementation."""
    try:
        from .utils.output_paths import OUTPUT_DIR as _OUTPUT_DIR  # type: ignore
        from .utils import output_paths as _op  # type: ignore
        return _OUTPUT_DIR, _op
    except Exception:
        class _Fallback:
            OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs")).resolve()

            @staticmethod
            def ensure_dir(p: Path) -> Path:
                p = Path(p)
                p.mkdir(parents=True, exist_ok=True)
                return p

            @staticmethod
            def subdir(*parts: str) -> Path:
                return _Fallback.ensure_dir(_Fallback.OUTPUT_DIR.joinpath(*parts))

            @staticmethod
            def path(*parts: str) -> Path:
                p = _Fallback.OUTPUT_DIR.joinpath(*parts)
                _Fallback.ensure_dir(p.parent)
                return p

        return _Fallback.OUTPUT_DIR, _Fallback


OUTPUT_DIR, _op = _load_output_utils()


def _ensure_dir(p: Path) -> Path:
    fn = getattr(_op, "ensure_dir", None)
    if callable(fn):
        return fn(Path(p))
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _subdir(*parts: str) -> Path:
    for name in ("subdir", "get_output_subdir", "output_subdir", "resolve_subdir"):
        fn = getattr(_op, name, None)
        if callable(fn):
            return Path(fn(*parts))
    return _ensure_dir(Path(OUTPUT_DIR).joinpath(*parts))


def _out_path(*parts: str) -> Path:
    for name in ("path", "output_path", "resolve_output_path", "resolve_path"):
        fn = getattr(_op, name, None)
        if callable(fn):
            return Path(fn(*parts))
    p = Path(OUTPUT_DIR).joinpath(*parts)
    _ensure_dir(p.parent)
    return p


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: Path
    output_root: Path


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: Any) -> None:
    _ensure_dir(Path(path).parent)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_pipeline_entrypoint() -> Tuple[Optional[Callable[..., Any]], str]:
    candidates = [
        (".pipeline", ("run_pipeline", "run", "main")),
        (".main_pipeline", ("run_pipeline", "run", "main")),
        (".pipeline_runner", ("run_pipeline", "run", "main")),
        (".core.pipeline", ("run_pipeline", "run", "main")),
    ]
    pkg = __package__ or "src"
    for mod_name, fn_names in candidates:
        try:
            mod = importlib.import_module(mod_name, package=pkg)
        except Exception:
            continue
        for fn_name in fn_names:
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                return fn, f"{mod.__name__}.{fn_name}"
    return None, ""


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run the project pipeline.")
    p.add_argument("--run-id", default=None, help="Optional run id (defaults to UTC timestamp).")
    p.add_argument(
        "--output-subdir",
        default="runs",
        help="Subdirectory under OUTPUT_DIR for run artifacts (default: runs).",
    )
    p.add_argument(
        "--config",
        default=None,
        help="Optional path to a config file (passed through to the pipeline if supported).",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    _ensure_dir(Path(OUTPUT_DIR))

    run_id = args.run_id or _utc_run_id()
    run_dir = _ensure_dir(_subdir(args.output_subdir).joinpath(run_id))
    ctx = RunContext(run_id=run_id, run_dir=run_dir, output_root=Path(OUTPUT_DIR))

    meta = {
        "run_id": ctx.run_id,
        "output_root": str(ctx.output_root),
        "run_dir": str(ctx.run_dir),
        "argv": sys.argv,
        "env_OUTPUT_DIR": os.getenv("OUTPUT_DIR"),
        "utc_started_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(ctx.run_dir / "run_metadata.json", meta)

    fn, fn_ref = _resolve_pipeline_entrypoint()
    if fn is None:
        _write_json(ctx.run_dir / "status.json", {"status": "no_pipeline_entrypoint_found"})
        return 0

    try:
        kwargs = {
            "output_dir": ctx.run_dir,
            "output_root": ctx.output_root,
            "run_dir": ctx.run_dir,
            "run_id": ctx.run_id,
            "config_path": args.config,
            "config": args.config,
        }
        try:
            result = fn(**kwargs)
        except TypeError:
            result = fn(ctx)  # type: ignore[misc]
        _write_json(ctx.run_dir / "status.json", {"status": "ok", "entrypoint": fn_ref, "result": str(result)})
        return 0
    except SystemExit as e:
        code = int(getattr(e, "code", 1) or 0)
        _write_json(ctx.run_dir / "status.json", {"status": "system_exit", "entrypoint": fn_ref, "code": code})
        return code
    except Exception as e:
        _write_json(ctx.run_dir / "status.json", {"status": "error", "entrypoint": fn_ref, "error": repr(e)})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
