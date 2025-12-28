#!/usr/bin/env python3
"""Generate v1 compliance/certification pathway artifact.

Writes: outputs/compliance_standards_map.md
Intended for CI/local one-command generation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _resolve_root() -> Path:
    # script located at <repo>/scripts/generate_compliance_artifact.py
    return Path(__file__).resolve().parents[1]


def _default_output_path(repo_root: Path) -> Path:
    return repo_root / "outputs" / "compliance_standards_map.md"


def _import_generator():
    try:
        # Preferred public API
        from compliance_pathway import generate_compliance_artifact  # type: ignore
        return generate_compliance_artifact
    except Exception:
        pass
    try:
        # Fallback to render layer if public API name differs
        from compliance_pathway.render import render_compliance_artifact  # type: ignore
        return render_compliance_artifact
    except Exception as e:
        raise ImportError(
            "Unable to import compliance pathway generator. "
            "Expected compliance_pathway.generate_compliance_artifact or "
            "compliance_pathway.render.render_compliance_artifact."
        ) from e


def main(argv: list[str] | None = None) -> int:
    repo_root = _resolve_root()
    parser = argparse.ArgumentParser(
        description="Generate compliance standards map markdown artifact."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_default_output_path(repo_root),
        help="Output markdown path (default: ./outputs/compliance_standards_map.md).",
    )
    parser.add_argument(
        "--format",
        default="markdown",
        help="Output format (kept for forward-compat; v1 uses markdown).",
    )
    args = parser.parse_args(argv)

    out_path: Path = args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    gen = _import_generator()

    # Support multiple plausible generator signatures.
    try:
        result = gen(output_path=out_path)
    except TypeError:
        try:
            result = gen(out_path)
        except TypeError:
            result = gen()

    # If generator returns markdown text, write it.
    if isinstance(result, str):
        out_path.write_text(result, encoding="utf-8")
    elif isinstance(result, Path):
        out_path = result

    if not out_path.exists():
        raise RuntimeError(f"Generator completed but output not found: {out_path}")

    print(str(out_path))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR:{exc}", file=sys.stderr)
        raise
