#!/usr/bin/env python3
"""Validate claim-card workflow on the pilot case study (CI-friendly wrapper).

This script discovers pilot case study markdown files (or accepts explicit paths),
then invokes the project claim-card validator if available.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple


def _repo_root() -> Path:
    # scripts/validate_pilot_case_study.py -> repo root is parent of scripts/
    return Path(__file__).resolve().parents[1]


def _discover_pilot_paths(root: Path) -> List[Path]:
    # Prefer obvious locations; fall back to a light-weight search.
    candidates = [
        root / "case_studies" / "pilot",
        root / "case-studies" / "pilot",
        root / "case_study" / "pilot",
        root / "docs" / "case_studies" / "pilot",
        root / "data" / "pilot_case_study",
        root / "pilot_case_study",
    ]
    out: List[Path] = []
    for d in candidates:
        if d.is_dir():
            out.extend(sorted(p for p in d.rglob("*.md") if p.is_file()))
    if out:
        return out

    # Fallback: find any markdown that mentions "pilot" in path within common top-level dirs.
    tops = [root / "case_studies", root / "case-studies", root / "docs", root / "data"]
    for t in tops:
        if t.is_dir():
            for p in t.rglob("*.md"):
                if p.is_file() and "pilot" in str(p).lower():
                    out.append(p)
    return sorted(set(out))


def _load_validator() -> Tuple[Optional[Callable[..., object]], str]:
    # Try a small set of likely entrypoints; the repo may evolve.
    entrypoints = [
        ("src.claim_cards.validator", "validate_paths"),
        ("src.claim_cards.validate", "validate_paths"),
        ("claim_cards.validator", "validate_paths"),
        ("claim_cards.validate", "validate_paths"),
        ("src.claim_cards.cli", "main"),
        ("claim_cards.cli", "main"),
    ]
    for mod_name, func_name in entrypoints:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, func_name, None)
            if callable(fn):
                return fn, f"{mod_name}:{func_name}"
        except Exception:
            continue
    return None, ""


def _coerce_paths(paths: Iterable[str], root: Path) -> List[Path]:
    out: List[Path] = []
    for s in paths:
        p = Path(s)
        if not p.is_absolute():
            p = root / p
        out.append(p)
    return out


def _print_result(obj: object) -> int:
    # Normalize various validator return shapes to an exit code.
    if obj is None:
        return 0
    if isinstance(obj, bool):
        return 0 if obj else 1
    if isinstance(obj, int):
        return 0 if obj == 0 else 1
    # Common patterns: dict with ok/success/errors, or list of errors.
    if isinstance(obj, dict):
        for k in ("ok", "success", "valid"):
            if k in obj and isinstance(obj[k], bool):
                return 0 if obj[k] else 1
        if "errors" in obj and isinstance(obj["errors"], list):
            return 0 if len(obj["errors"]) == 0 else 1
    if isinstance(obj, list):
        return 0 if len(obj) == 0 else 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    root = _repo_root()
    sys.path.insert(0, str(root))  # allow "src.*" imports when running from repo root

    ap = argparse.ArgumentParser(description="Run claim-card validator on the pilot case study.")
    ap.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Optional explicit case study markdown paths (relative to repo root or absolute).",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="If supported by validator, request JSON output (best-effort).",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output; still returns non-zero on validation failures.",
    )
    ns = ap.parse_args(argv)

    paths = _coerce_paths(ns.paths, root) if ns.paths else _discover_pilot_paths(root)
    if not paths:
        sys.stderr.write("No pilot case study markdown files found. Provide --paths or add pilot case study files.\n")
        return 2

    validator, label = _load_validator()
    if validator is None:
        sys.stderr.write(
            "Claim-card validator not found (tried src/claim_cards and claim_cards modules).\n"
            "Ensure claim card tooling exists and is importable, then rerun.\n"
        )
        return 2

    # Best-effort call signature support.
    kwargs = {}
    if ns.json:
        kwargs["json"] = True
        kwargs["output_format"] = "json"
        kwargs["format"] = "json"

    try:
        try:
            result = validator(paths, **kwargs)
        except TypeError:
            # Some validators may want strings instead of Paths.
            result = validator([str(p) for p in paths], **kwargs)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 1
    except Exception as e:
        sys.stderr.write(f"Validator execution error ({label}): {e.__class__.__name__}: {e}\n")
        return 2

    if not ns.quiet:
        sys.stdout.write(f"Validated {len(paths)} file(s) using {label}.\n")
    return _print_result(result)


if __name__ == "__main__":
    raise SystemExit(main())
