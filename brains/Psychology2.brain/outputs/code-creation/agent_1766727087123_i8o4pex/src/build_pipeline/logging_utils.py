from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Dict, Any, Tuple
import datetime as _dt
import getpass
import hashlib
import json
import logging
import os
import platform
import socket
import subprocess
import sys
DEFAULT_LOGS_SUBDIR = Path("outputs") / "build_logs"


def utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds")


def utc_stamp_for_filename() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y%m%d_%H%M%SZ")
def ensure_build_logs_dir(base_dir: Optional[Path] = None) -> Path:
    base = Path.cwd() if base_dir is None else Path(base_dir)
    out = (base / DEFAULT_LOGS_SUBDIR).resolve()
    out.mkdir(parents=True, exist_ok=True)
    return out


def _run_git(args: list[str], cwd: Optional[Path] = None) -> Optional[str]:
    try:
        cp = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        s = (cp.stdout or "").strip()
        return s if s else None
    except Exception:
        return None


def environment_metadata(base_dir: Optional[Path] = None) -> Dict[str, Any]:
    base = Path.cwd() if base_dir is None else Path(base_dir)
    meta: Dict[str, Any] = {
        "timestamp_utc": utc_now_iso(),
        "user": getpass.getuser(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": sys.version.replace("\n", " "),
        "python_executable": sys.executable,
        "cwd": str(Path.cwd()),
        "base_dir": str(base.resolve()),
        "argv": list(sys.argv),
        "env": {k: os.environ.get(k) for k in ("CI", "GITHUB_SHA", "GITHUB_REF", "GITHUB_RUN_ID", "GITHUB_WORKFLOW")},
    }

    git_root = _run_git(["rev-parse", "--show-toplevel"], cwd=base)
    if git_root:
        git_root_p = Path(git_root)
        meta["git"] = {
            "root": str(git_root_p),
            "commit": _run_git(["rev-parse", "--short", "HEAD"], cwd=git_root_p),
            "branch": _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=git_root_p),
            "is_dirty": bool(_run_git(["status", "--porcelain"], cwd=git_root_p)),
        }
    return meta
@dataclass(frozen=True)
class BuildLogPaths:
    logs_dir: Path
    log_file: Path
    manifest_file: Path
    build_id: str


def make_build_log_paths(base_dir: Optional[Path] = None, prefix: str = "build") -> BuildLogPaths:
    logs_dir = ensure_build_logs_dir(base_dir)
    stamp = utc_stamp_for_filename()
    pid = os.getpid()
    build_id = f"{stamp}_{pid}"
    log_file = logs_dir / f"{prefix}_{build_id}.log"
    manifest_file = logs_dir / f"{prefix}_{build_id}.manifest.json"
    return BuildLogPaths(logs_dir=logs_dir, log_file=log_file, manifest_file=manifest_file, build_id=build_id)
def configure_logger(
    name: str = "build_pipeline",
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    fmt = logging.Formatter(
        fmt="%(asctime)sZ | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    if not any(isinstance(h, logging.StreamHandler) and getattr(h, "_bp_stream", False) for h in logger.handlers):
        sh = logging.StreamHandler(stream=sys.stdout)
        sh.setLevel(level)
        sh.setFormatter(fmt)
        sh._bp_stream = True  # type: ignore[attr-defined]
        logger.addHandler(sh)

    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        key = str(log_file.resolve())
        if not any(isinstance(h, logging.FileHandler) and getattr(h, "_bp_file", None) == key for h in logger.handlers):
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(level)
            fh.setFormatter(fmt)
            fh._bp_file = key  # type: ignore[attr-defined]
            logger.addHandler(fh)

    return logger
def log_metadata(logger: logging.Logger, metadata: Dict[str, Any], title: str = "ENVIRONMENT") -> None:
    logger.info("%s BEGIN", title)
    try:
        payload = json.dumps(metadata, sort_keys=True, ensure_ascii=False)
    except Exception:
        payload = str(metadata)
    for line in payload.splitlines():
        logger.info("%s", line)
    logger.info("%s END", title)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksum_manifest(
    manifest_path: Path,
    files: Iterable[Path],
    base_dir: Optional[Path] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base = Path.cwd() if base_dir is None else Path(base_dir)
    manifest: Dict[str, Any] = {
        "created_utc": utc_now_iso(),
        "base_dir": str(base.resolve()),
        "files": [],
    }
    if extra:
        manifest["meta"] = extra

    for p in files:
        pp = Path(p)
        if not pp.exists() or not pp.is_file():
            continue
        rel = str(pp.resolve().relative_to(base.resolve())) if pp.resolve().is_relative_to(base.resolve()) else str(pp.resolve())
        manifest["files"].append(
            {
                "path": rel,
                "bytes": pp.stat().st_size,
                "sha256": sha256_file(pp),
                "mtime_utc": _dt.datetime.fromtimestamp(pp.stat().st_mtime, tz=_dt.timezone.utc).isoformat(timespec="seconds"),
            }
        )

    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest
def init_build_logging(
    base_dir: Optional[Path] = None,
    prefix: str = "build",
    logger_name: str = "build_pipeline",
    level: int = logging.INFO,
) -> Tuple[logging.Logger, BuildLogPaths, Dict[str, Any]]:
    paths = make_build_log_paths(base_dir=base_dir, prefix=prefix)
    logger = configure_logger(name=logger_name, log_file=paths.log_file, level=level)
    meta = environment_metadata(base_dir=base_dir)
    meta["build_id"] = paths.build_id
    meta["log_file"] = str(paths.log_file)
    meta["manifest_file"] = str(paths.manifest_file)
    logger.info("BUILD START | build_id=%s", paths.build_id)
    log_metadata(logger, meta)
    return logger, paths, meta
