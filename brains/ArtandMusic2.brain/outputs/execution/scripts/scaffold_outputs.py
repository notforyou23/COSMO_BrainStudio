#!/usr/bin/env python3
\"\"\"Scaffold and normalize the canonical outputs tree for deterministic CI runs.

Creates a stable directory layout under an outputs root and ensures required
placeholder files exist with deterministic contents.
\"\"\"

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import os
import time


@dataclass(frozen=True)
class ScaffoldSpec:
    outputs_root: Path
    dirs: tuple[str, ...] = (
        "artifacts",
        "logs",
        "reports",
        "tmp",
    )
    # Relative to outputs_root
    placeholder_files: tuple[str, ...] = (
        "QA_REPORT.json",
        "reports/.gitkeep",
        "artifacts/.gitkeep",
        "logs/.gitkeep",
        "tmp/.gitkeep",
        ".gitkeep",
        "README.txt",
    )


def _stable_now_utc() -> str:
    # Deterministic default: allow caller to set SOURCE_DATE_EPOCH.
    sde = os.environ.get("SOURCE_DATE_EPOCH")
    if sde and sde.isdigit():
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(sde)))
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(0))


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_text_if_missing(p: Path, text: str) -> None:
    if p.exists():
        return
    _ensure_dir(p.parent)
    p.write_text(text, encoding="utf-8")


def _write_json_if_missing(p: Path, obj: object) -> None:
    if p.exists():
        return
    _ensure_dir(p.parent)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scaffold_outputs(spec: ScaffoldSpec) -> dict:
    root = spec.outputs_root
    _ensure_dir(root)
    for d in spec.dirs:
        _ensure_dir(root / d)

    readme = (
        "This directory is managed by scripts/scaffold_outputs.py.\n"
        "It is safe to delete; CI/QA will recreate it deterministically.\n"
        "Only files under this tree should be written by the QA harness.\n"
    )
    _write_text_if_missing(root / "README.txt", readme)

    report_skeleton = {
        "schema_version": 1,
        "generated_at": _stable_now_utc(),
        "status": "NOT_RUN",
        "qa_command": None,
        "return_code": None,
        "policy": {"outputs_root": str(root.as_posix()), "writes_outside_outputs": None},
        "checks": [],
        "notes": [],
    }
    _write_json_if_missing(root / "QA_REPORT.json", report_skeleton)

    for rel in spec.placeholder_files:
        p = root / rel
        if p.suffix == ".json":
            continue
        _write_text_if_missing(p, "")

    # Normalize permissions minimally (avoid platform-specific churn).
    return {
        "outputs_root": str(root),
        "created_dirs": [str((root / d)) for d in spec.dirs],
        "ensured_files": [str((root / f)) for f in spec.placeholder_files],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Create/normalize the canonical outputs tree.")
    ap.add_argument(
        "--outputs-root",
        default="outputs",
        help="Path to outputs root (default: ./outputs)",
    )
    ap.add_argument("--quiet", action="store_true", help="Suppress non-essential output.")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.outputs_root).expanduser()
    info = scaffold_outputs(ScaffoldSpec(outputs_root=root))
    if not args.quiet:
        print(json.dumps(info, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
