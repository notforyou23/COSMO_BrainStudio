from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RunLogPaths:
    run_id: str
    logs_dir: Path
    text_log: Path
    jsonl_log: Path
    summary_txt: Path


def _now_iso() -> str:
    # ISO-ish without timezone deps; stable for quick diagnostics.
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


def resolve_logs_dir(run_id: str, project_root: Optional[Path] = None) -> RunLogPaths:
    root = Path(project_root) if project_root else Path.cwd()
    logs_dir = root / "_build" / str(run_id) / "logs"
    return RunLogPaths(
        run_id=str(run_id),
        logs_dir=logs_dir,
        text_log=logs_dir / "artifact_gate.log",
        jsonl_log=logs_dir / "diagnostics.jsonl",
        summary_txt=logs_dir / "summary.txt",
    )


def ensure_logs_dir(paths: RunLogPaths) -> None:
    paths.logs_dir.mkdir(parents=True, exist_ok=True)


def init_file_logging(
    run_id: str,
    *,
    project_root: Optional[Path] = None,
    logger_name: str = "artifact_gate",
    level: int = logging.INFO,
) -> tuple[logging.Logger, RunLogPaths]:
    paths = resolve_logs_dir(run_id, project_root=project_root)
    ensure_logs_dir(paths)

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Avoid duplicate handlers on re-init.
    for h in list(logger.handlers):
        logger.removeHandler(h)

    fh = logging.FileHandler(paths.text_log, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(stream=sys.stderr)
    sh.setLevel(level)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger.info("logging initialized: run_id=%s logs_dir=%s", run_id, str(paths.logs_dir))
    write_jsonl(paths, {"ts": _now_iso(), "event": "logging_initialized", "run_id": str(run_id), "logs_dir": str(paths.logs_dir)})
    return logger, paths


def write_jsonl(paths: RunLogPaths, record: Dict[str, Any]) -> None:
    ensure_logs_dir(paths)
    rec = dict(record or {})
    rec.setdefault("ts", _now_iso())
    rec.setdefault("run_id", paths.run_id)
    line = json.dumps(rec, sort_keys=True, ensure_ascii=False)
    with open(paths.jsonl_log, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_summary(paths: RunLogPaths, title: str, lines: list[str]) -> None:
    ensure_logs_dir(paths)
    with open(paths.summary_txt, "a", encoding="utf-8") as f:
        f.write(f"[{_now_iso()}] {title}\n")
        for ln in lines:
            f.write(f"  {ln}\n")
        f.write("\n")


def capture_exception(paths: RunLogPaths, where: str, exc: BaseException) -> None:
    write_jsonl(
        paths,
        {
            "event": "exception",
            "where": where,
            "type": type(exc).__name__,
            "message": str(exc),
        },
    )


def safe_str(p: Any) -> str:
    try:
        return str(p)
    except Exception:
        return repr(p)


def env_snapshot(minimal: bool = True) -> Dict[str, Any]:
    keys = [
        "PWD",
        "HOME",
        "USER",
        "SHELL",
        "PATH",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "CI",
    ]
    env = dict(os.environ)
    if minimal:
        return {k: env.get(k) for k in keys if k in env or k in ("PWD", "HOME", "USER")}
    return env
