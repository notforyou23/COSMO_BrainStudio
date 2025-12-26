"""qa.paths

Canonical path resolution utilities for stable output directories and consistent
artifact locations across environments.

Design goals:
- Stable defaults (repo-root/.qa by default)
- Override via environment variables (QA_OUTPUT_DIR / QA_ROOT)
- Convenience helpers for common QA artifacts
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional


def _first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for p in paths:
        try:
            if p.exists():
                return p
        except OSError:
            continue
    return None


def cwd() -> Path:
    return Path.cwd().resolve()


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Best-effort repository root finder (walks upward).

    Heuristics:
    - .git directory
    - pyproject.toml
    - setup.cfg / setup.py
    - requirements.txt
    Falls back to `start` (or CWD) if nothing is found.
    """
    cur = (start or cwd()).resolve()
    for p in [cur, *cur.parents]:
        candidates = [
            p / '.git',
            p / 'pyproject.toml',
            p / 'setup.cfg',
            p / 'setup.py',
            p / 'requirements.txt',
        ]
        if _first_existing(candidates) is not None:
            return p
    return cur


def qa_root(start: Optional[Path] = None) -> Path:
    """Return the canonical QA root directory.

    Environment overrides:
    - QA_ROOT: explicit root directory for qa-managed state
    Default:
    - <repo_root>/.qa
    """
    env = os.environ.get('QA_ROOT')
    if env:
        return Path(env).expanduser().resolve()
    return find_repo_root(start) / '.qa'


def output_root(start: Optional[Path] = None) -> Path:
    """Return canonical output directory for runner-generated artifacts.

    Environment overrides:
    - QA_OUTPUT_DIR: explicit output directory
    Default:
    - <qa_root>/out
    """
    env = os.environ.get('QA_OUTPUT_DIR')
    if env:
        return Path(env).expanduser().resolve()
    return qa_root(start) / 'out'


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_dir(run_id: Optional[str] = None, start: Optional[Path] = None) -> Path:
    """Return directory for a specific run.

    If run_id is None, returns the shared output_root (non-run-scoped).
    """
    base = output_root(start)
    return base if not run_id else (base / 'runs' / str(run_id))


def artifacts_dir(run_id: Optional[str] = None, start: Optional[Path] = None) -> Path:
    """Directory for general artifacts."""
    return run_dir(run_id, start) / 'artifacts'


def logs_dir(run_id: Optional[str] = None, start: Optional[Path] = None) -> Path:
    return run_dir(run_id, start) / 'logs'


def reports_dir(run_id: Optional[str] = None, start: Optional[Path] = None) -> Path:
    return run_dir(run_id, start) / 'reports'


def junit_path(run_id: Optional[str] = None, start: Optional[Path] = None) -> Path:
    return reports_dir(run_id, start) / 'junit.xml'


def coverage_xml_path(run_id: Optional[str] = None, start: Optional[Path] = None) -> Path:
    return reports_dir(run_id, start) / 'coverage.xml'


def summary_json_path(run_id: Optional[str] = None, start: Optional[Path] = None) -> Path:
    return reports_dir(run_id, start) / 'summary.json'


def stable_paths(run_id: Optional[str] = None, start: Optional[Path] = None) -> dict:
    """Return a dict of key canonical paths (useful for logging/JSON output)."""
    rr = find_repo_root(start)
    qr = qa_root(start)
    out = output_root(start)
    rd = run_dir(run_id, start)
    return {
        'repo_root': str(rr),
        'qa_root': str(qr),
        'output_root': str(out),
        'run_dir': str(rd),
        'artifacts_dir': str(artifacts_dir(run_id, start)),
        'logs_dir': str(logs_dir(run_id, start)),
        'reports_dir': str(reports_dir(run_id, start)),
        'junit_xml': str(junit_path(run_id, start)),
        'coverage_xml': str(coverage_xml_path(run_id, start)),
        'summary_json': str(summary_json_path(run_id, start)),
    }


def ensure_run_layout(run_id: Optional[str] = None, start: Optional[Path] = None) -> dict:
    """Create the canonical directory layout and return stable_paths."""
    ensure_dir(output_root(start))
    ensure_dir(run_dir(run_id, start))
    ensure_dir(artifacts_dir(run_id, start))
    ensure_dir(logs_dir(run_id, start))
    ensure_dir(reports_dir(run_id, start))
    return stable_paths(run_id, start)
