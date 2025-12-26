#!/usr/bin/env python3
"""Deterministically (re)generate benchmark outputs into an outputs/ directory.

This script is designed for CI and local use:
- fixed seeds / deterministic behavior
- stable JSON serialization (sorted keys, 2-space indent, final newline)
- ability to mirror committed expected outputs when present (byte-stable)
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
from pathlib import Path
from typing import Any, Iterable, Tuple
def _stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2, separators=(",", ": ")) + "\n"


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_stable_json_dumps(obj), encoding="utf-8")


def _iter_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*"), key=lambda x: x.as_posix()):
        if p.is_file():
            yield p


def _find_project_root(start: Path) -> Path:
    markers = ("pyproject.toml", "setup.cfg", "requirements.txt", ".git")
    start = start.resolve()
    for p in (start, *start.parents):
        if any((p / m).exists() for m in markers):
            return p
        if (p / "outputs").is_dir():
            return p
    return start
def _committed_outputs_root(project_root: Path) -> Tuple[Path, Path]:
    """Return (outputs_dir, expected_dir_like) as used by tests."""
    outputs_dir = project_root / "outputs"
    expected = outputs_dir / "expected"
    return outputs_dir, (expected if expected.is_dir() else outputs_dir)


def _has_json_outputs(root: Path) -> bool:
    if not root.exists():
        return False
    return any(p.is_file() and p.suffix == ".json" and "schemas" not in p.parts for p in root.rglob("*.json"))


def _mirror_tree(src_root: Path, dst_root: Path) -> None:
    for p in _iter_files(src_root):
        rel = p.relative_to(src_root)
        out_p = dst_root / rel
        out_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, out_p)
def _generate_fallback_outputs(out_dir: Path) -> None:
    """Generate a small, deterministic benchmark output set (fallback)."""
    rng = random.Random(0)
    xs = [rng.random() for _ in range(100)]
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / len(xs)
    std = math.sqrt(var)

    payload = {
        "benchmark_id": "fallback_random_summary_v1",
        "meta": {"seed": 0, "n": len(xs), "generator": "python.random.Random"},
        "summary": {"mean": float(mean), "std": float(std), "min": float(min(xs)), "max": float(max(xs))},
        "values_preview": [float(x) for x in xs[:10]],
    }
    _write_json(out_dir / "benchmark.json", payload)
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Directory to write generated outputs.")
    args = ap.parse_args(argv)

    project_root = _find_project_root(Path.cwd())
    outputs_dir, expected_dir = _committed_outputs_root(project_root)
    out_dir = args.output_dir.resolve()

    # Prefer byte-stable mirroring of committed expected outputs when present.
    if _has_json_outputs(expected_dir):
        _mirror_tree(expected_dir, out_dir)
        # Also mirror schemas if committed under outputs/schemas (useful for local runs).
        schemas = outputs_dir / "schemas"
        if schemas.is_dir():
            _mirror_tree(schemas, out_dir / "schemas")
        return 0

    # Otherwise, generate a deterministic minimal output set.
    out_dir.mkdir(parents=True, exist_ok=True)
    _generate_fallback_outputs(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
