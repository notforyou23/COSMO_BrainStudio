"""gate.path_probe

Lightweight path probing helpers for gate/validator scripts.

Goals:
- Resolve symlinks and return canonical paths consistently.
- Validate expected project directories/files exist and are readable.
- Detect suspicious mount/path issues (missing, empty, non-writable).
- Provide concise, parseable diagnostics for logs/reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sys
import json
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class PathProbeResult:
    key: str
    provided: str
    expanded: str
    resolved: str
    exists: bool
    is_dir: bool
    is_file: bool
    readable: bool
    writable_dir: bool
    size_bytes: Optional[int]
    note: str = ""


def _expand(p: Path) -> Path:
    try:
        s = os.path.expandvars(os.path.expanduser(str(p)))
        return Path(s)
    except Exception:
        return p


def canonical_path(p: Path, strict: bool = False) -> Path:
    p2 = _expand(p)
    try:
        return p2.resolve(strict=strict)
    except Exception:
        try:
            return Path(os.path.realpath(str(p2)))
        except Exception:
            return p2


def _rw_flags(path: Path) -> Tuple[bool, bool]:
    readable = False
    writable_dir = False
    try:
        readable = os.access(str(path), os.R_OK)
    except Exception:
        readable = False
    try:
        parent = path if path.is_dir() else path.parent
        writable_dir = os.access(str(parent), os.W_OK)
    except Exception:
        writable_dir = False
    return readable, writable_dir


def probe_path(key: str, path: Path) -> PathProbeResult:
    provided = str(path)
    expanded = str(_expand(path))
    resolved_p = canonical_path(path, strict=False)
    exists = resolved_p.exists()
    is_dir = resolved_p.is_dir() if exists else False
    is_file = resolved_p.is_file() if exists else False
    readable, writable_dir = _rw_flags(resolved_p if exists else resolved_p.parent)
    size_bytes: Optional[int] = None
    note = ""
    if exists and is_file:
        try:
            size_bytes = resolved_p.stat().st_size
        except Exception:
            size_bytes = None
    if not exists:
        note = "missing"
    elif is_dir:
        try:
            it = resolved_p.iterdir()
            next(it, None)
        except Exception:
            note = "unlistable_dir"
    elif is_file and size_bytes == 0:
        note = "empty_file"
    return PathProbeResult(
        key=key,
        provided=provided,
        expanded=expanded,
        resolved=str(resolved_p),
        exists=exists,
        is_dir=is_dir,
        is_file=is_file,
        readable=readable,
        writable_dir=writable_dir,
        size_bytes=size_bytes,
        note=note,
    )


def detect_missing_mount(root: Path) -> Tuple[bool, str]:
    """Heuristic detection for 'missing mount' situations.

    Returns (suspect, reason). A suspect mount includes:
    - path missing, or
    - path exists but is not readable, or
    - directory exists but cannot be listed, or
    - directory exists but is empty while expected to contain project files.
    """
    rp = canonical_path(root, strict=False)
    if not rp.exists():
        return True, "root_missing"
    if not os.access(str(rp), os.R_OK):
        return True, "root_not_readable"
    if not rp.is_dir():
        return True, "root_not_dir"
    try:
        entries = [e.name for e in rp.iterdir()]
    except Exception:
        return True, "root_unlistable"
    if len(entries) == 0:
        return True, "root_empty"
    return False, "ok"


def expected_project_paths(project_root: Path) -> Dict[str, Path]:
    """Common paths validators typically reference. Non-fatal if absent."""
    pr = canonical_path(project_root, strict=False)
    return {
        "project_root": pr,
        "gate_dir": pr / "gate",
        "runtime_dir": pr / "runtime",
        "reports_dir": pr / "runtime" / "_build" / "reports",
        "pyproject_toml": pr / "pyproject.toml",
        "setup_cfg": pr / "setup.cfg",
        "requirements_txt": pr / "requirements.txt",
    }


def probe_expected(project_root: Path, extra: Optional[Dict[str, Path]] = None) -> List[PathProbeResult]:
    paths = expected_project_paths(project_root)
    if extra:
        paths.update(extra)
    results = [probe_path(k, v) for k, v in paths.items()]
    return sorted(results, key=lambda r: r.key)


def as_dict(results: Iterable[PathProbeResult]) -> Dict[str, dict]:
    return {r.key: r.__dict__ for r in results}


def format_human(results: Iterable[PathProbeResult]) -> str:
    lines: List[str] = []
    for r in results:
        flags = []
        if r.exists:
            flags.append("exists")
        if r.is_dir:
            flags.append("dir")
        if r.is_file:
            flags.append("file")
        if r.readable:
            flags.append("r")
        if r.writable_dir:
            flags.append("wdir")
        if r.size_bytes is not None:
            flags.append(f"{r.size_bytes}B")
        note = f" [{r.note}]" if r.note else ""
        lines.append(f"{r.key}: {r.resolved} ({','.join(flags)}){note}")
        if r.provided != r.resolved:
            lines.append(f"  provided={r.provided} expanded={r.expanded}")
    return "\n".join(lines)


def print_probe(project_root: Optional[Path] = None, *, json_output: bool = False, extra: Optional[Dict[str, Path]] = None) -> int:
    """Print canonical paths + mount suspicion checks. Returns process-style code."""
    root = project_root or Path.cwd()
    suspect, reason = detect_missing_mount(root)
    results = probe_expected(root, extra=extra)
    payload = {
        "root": str(canonical_path(root, strict=False)),
        "suspect_mount": suspect,
        "suspect_reason": reason,
        "python": sys.executable,
        "cwd": str(Path.cwd()),
        "results": as_dict(results),
    }
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"PATH_PROBE root={payload['root']} suspect_mount={suspect} reason={reason}")
        print(format_human(results))
    return 2 if suspect else 0
