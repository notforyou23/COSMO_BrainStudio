#!/usr/bin/env python3
"""Minimal reproducible pipeline entrypoint.

Always writes:
- ./outputs/run.log
- ./outputs/run_stamp.json
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _read_text_if_exists(p: Path, limit: int = 4096) -> str | None:
    try:
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return None
    return None


def _git_metadata(repo_root: Path) -> dict:
    meta: dict = {"is_git_repo": False}
    git_dir = repo_root / ".git"
    head = _read_text_if_exists(git_dir / "HEAD")
    if not head:
        return meta
    meta["is_git_repo"] = True
    head = head.strip()
    meta["head"] = head
    commit = None
    branch = None
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        branch = ref.split("/")[-1] if ref else None
        ref_path = git_dir / ref
        commit = _read_text_if_exists(ref_path)
        if commit:
            commit = commit.strip()
    else:
        commit = head
    meta["branch"] = branch
    meta["commit"] = commit
    return meta


def _configure_logging(log_path: Path) -> logging.Logger:
    _safe_mkdir(log_path.parent)
    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.propagate = False
    return logger


@dataclass
class RunStamp:
    schema_version: str
    run_id: str
    status: str
    started_at: str
    finished_at: str | None
    duration_seconds: float | None
    outputs_dir: str
    run_log_path: str
    run_stamp_path: str
    cwd: str
    argv: list[str]
    python_version: str
    platform: str
    hostname: str
    env: dict
    git: dict
    error: dict | None


def _write_json(path: Path, data: dict) -> None:
    _safe_mkdir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def run() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    outputs_dir = repo_root / "outputs"
    run_id = uuid.uuid4().hex
    run_log_path = outputs_dir / "run.log"
    run_stamp_path = outputs_dir / "run_stamp.json"
    logger = _configure_logging(run_log_path)

    started_at = _utc_now_iso()
    t0 = time.time()
    status = "unknown"
    err: dict | None = None

    logger.info("pipeline_start run_id=%s", run_id)
    logger.info("repo_root=%s", repo_root)
    logger.info("outputs_dir=%s", outputs_dir)

    try:
        # Minimal deterministic "pipeline" step: record basic environment and emit a log line.
        logger.info("step=hello message=%s", "minimal reproducible pipeline run")
        time.sleep(0.01)
        status = "success"
        return_code = 0
    except Exception as e:  # pragma: no cover
        status = "failed"
        return_code = 1
        err = {"type": type(e).__name__, "message": str(e)}
        logger.exception("pipeline_error")
    finally:
        finished_at = _utc_now_iso()
        duration = round(time.time() - t0, 6)
        stamp = RunStamp(
            schema_version="1.0",
            run_id=run_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration,
            outputs_dir=str(outputs_dir),
            run_log_path=str(run_log_path),
            run_stamp_path=str(run_stamp_path),
            cwd=os.getcwd(),
            argv=list(sys.argv),
            python_version=sys.version.replace("\n", " "),
            platform=platform.platform(),
            hostname=platform.node(),
            env={
                "ci": os.environ.get("CI"),
                "github_actions": os.environ.get("GITHUB_ACTIONS"),
            },
            git=_git_metadata(repo_root),
            error=err,
        )
        _write_json(run_stamp_path, asdict(stamp))
        logger.info("pipeline_end run_id=%s status=%s duration_seconds=%s", run_id, status, duration)

    return return_code


if __name__ == "__main__":
    raise SystemExit(run())
