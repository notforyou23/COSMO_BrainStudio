from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class LoggingPaths:
    root: Path
    build_dir: Path
    logs_dir: Path
    log_file: Path


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_logging_paths(project_root: Optional[Path] = None, run_name: Optional[str] = None) -> LoggingPaths:
    root = Path(project_root) if project_root is not None else Path.cwd()
    root = root.resolve()
    build_dir = root / "_build"
    logs_dir = build_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    safe_name = (run_name or "run").strip().replace(" ", "_")[:80] or "run"
    log_file = logs_dir / f"{safe_name}_{_utc_stamp()}.log"
    return LoggingPaths(root=root, build_dir=build_dir, logs_dir=logs_dir, log_file=log_file)


def setup_logging(
    name: str = "meta_analysis_demo",
    project_root: Optional[Path] = None,
    run_name: Optional[str] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> tuple[logging.Logger, Path]:
    paths = resolve_logging_paths(project_root=project_root, run_name=run_name)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if getattr(logger, "_meta_demo_configured", False):
        return logger, paths.log_file

    for h in list(logger.handlers):
        logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    detailed_fmt = "%(asctime)s.%(msecs)03dZ | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
    concise_fmt = "%(levelname)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"

    class _UTCFormatter(logging.Formatter):
        converter = datetime.utcfromtimestamp  # type: ignore[assignment]

    file_handler = logging.FileHandler(paths.log_file, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(_UTCFormatter(detailed_fmt, datefmt=datefmt))

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(console_level)
    stream_handler.setFormatter(logging.Formatter(concise_fmt))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger._meta_demo_configured = True  # type: ignore[attr-defined]
    logger.debug("Logging initialized (root=%s, log_file=%s)", paths.root, paths.log_file)
    logger.info("Log file: %s", paths.log_file)
    return logger, paths.log_file


def get_logger(name: str = "meta_analysis_demo") -> logging.Logger:
    return logging.getLogger(name)
