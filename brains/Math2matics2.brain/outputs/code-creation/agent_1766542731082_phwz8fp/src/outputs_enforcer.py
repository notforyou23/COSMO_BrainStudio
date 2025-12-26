"""outputs_enforcer.py

Core helpers for enforcing the project policy that every research cycle
adds or updates at least one file in an outputs directory.

This module is dependency-free (stdlib only) and portable: if a preferred
outputs directory is not writable, a fallback directory is selected/created.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Tuple
import os
import time
class OutputPolicyError(RuntimeError):
    """Raised when the per-cycle outputs policy is violated."""


@dataclass(frozen=True)
class OutputFileState:
    mtime_ns: int
    size: int


Snapshot = Dict[str, OutputFileState]
def _is_dir_writable(d: Path) -> bool:
    d.mkdir(parents=True, exist_ok=True)
    probe = d / (".write_probe_" + str(os.getpid()) + "_" + str(time.time_ns()))
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def detect_outputs_dir(
    preferred: Optional[Iterable[Path]] = None,
    fallback_root: Optional[Path] = None,
) -> Path:
    """Return the first writable outputs directory from preferred choices.

    If none are writable, create and return a fallback dir (default: ./outputs_fallback/outputs).
    """
    if preferred is None:
        preferred = [Path("outputs"), Path("/outputs")]
    for p in preferred:
        p = Path(p)
        if _is_dir_writable(p):
            return p

    fb = Path("outputs_fallback") if fallback_root is None else Path(fallback_root)
    fb = fb / "outputs"
    if not _is_dir_writable(fb):
        raise OutputPolicyError(f"No writable outputs directory (tried: {list(preferred)} and {fb})")
    return fb
def snapshot_outputs(outputs_dir: Path) -> Snapshot:
    """Snapshot current state of all files directly under outputs_dir."""
    outputs_dir = Path(outputs_dir)
    snap: Snapshot = {}
    if not outputs_dir.exists():
        return snap
    for p in outputs_dir.glob("*"):
        if p.is_file():
            st = p.stat()
            snap[p.name] = OutputFileState(mtime_ns=st.st_mtime_ns, size=st.st_size)
    return snap


def diff_snapshots(before: Mapping[str, OutputFileState], after: Mapping[str, OutputFileState]) -> Dict[str, str]:
    """Return {filename: change_type} where change_type in {'added','modified','deleted'}."""
    changes: Dict[str, str] = {}
    for k in after:
        if k not in before:
            changes[k] = "added"
        elif after[k] != before[k]:
            changes[k] = "modified"
    for k in before:
        if k not in after:
            changes[k] = "deleted"
    return changes


def enforce_cycle_change(before: Snapshot, after: Snapshot, *, min_changed: int = 1) -> Dict[str, str]:
    """Validate that at least min_changed files were added/modified (not only deleted)."""
    changes = diff_snapshots(before, after)
    positive = [k for k, v in changes.items() if v in ("added", "modified")]
    if len(positive) < min_changed:
        raise OutputPolicyError(
            f"Outputs policy violation: expected >= {min_changed} added/modified file(s); got {len(positive)}. "
            f"Changes={changes}"
        )
    return changes
_MIN_V1_README = """# Outputs (Minimum v1)

This directory is the canonical **artifact log** for this project.

## Policy
- Each research/pipeline cycle **must add or update at least one file** in this directory.
- The pipeline should snapshot the directory before and after a cycle and fail if no files changed.

## Core documents
- `README.md` (this file): index and policy.
- `core_findings.md`: consolidated findings/decisions; safe per-cycle update target.

## How to use
Typical cycle behavior:
1. Run the cycle.
2. Append a short dated note to `core_findings.md` describing what changed.
"""


_MIN_V1_CORE = """# Core findings

This document is intentionally lightweight: it accumulates the current consolidated
findings/decisions plus a small per-cycle changelog.

## Changelog
"""
def ensure_minimum_v1(outputs_dir: Path) -> Tuple[Path, Path]:
    """Ensure minimum v1 required docs exist; return (readme_path, core_findings_path)."""
    outputs_dir = Path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    readme = outputs_dir / "README.md"
    core = outputs_dir / "core_findings.md"

    if not readme.exists():
        readme.write_text(_MIN_V1_README.rstrip() + "\n", encoding="utf-8")
    if not core.exists():
        core.write_text(_MIN_V1_CORE.rstrip() + "\n", encoding="utf-8")

    return readme, core


def append_cycle_note(core_findings_path: Path, note: str, *, timestamp: Optional[str] = None) -> None:
    """Append a dated bullet to core_findings.md (creating parents if needed)."""
    p = Path(core_findings_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if timestamp is None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"- **{timestamp}**: {note.strip()}\n"
    if not p.exists():
        p.write_text(_MIN_V1_CORE.rstrip() + "\n" + line, encoding="utf-8")
    else:
        with p.open("a", encoding="utf-8") as f:
            f.write(line)
