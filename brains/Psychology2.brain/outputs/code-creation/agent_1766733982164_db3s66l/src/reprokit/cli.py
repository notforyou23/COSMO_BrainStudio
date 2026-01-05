"""reprokit.cli

Small CLI entry point to generate a reproducibility run log on demand and to
standardize logging across scripts.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

try:
    from importlib import metadata as importlib_metadata  # py3.8+
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore
@dataclass(frozen=True)
class RunLog:
    created_utc: str
    cwd: str
    argv: Tuple[str, ...]
    python: str
    platform: Dict[str, str]
    packages: Dict[str, str]
    git: Dict[str, Optional[str]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "created_utc": self.created_utc,
            "cwd": self.cwd,
            "argv": list(self.argv),
            "python": self.python,
            "platform": self.platform,
            "packages": self.packages,
            "git": self.git,
        }
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_run(cmd: Iterable[str]) -> Optional[str]:
    try:
        out = subprocess.check_output(list(cmd), stderr=subprocess.DEVNULL, text=True)
        out = out.strip()
        return out if out else None
    except Exception:
        return None


def _git_info() -> Dict[str, Optional[str]]:
    return {
        "commit": _safe_run(["git", "rev-parse", "HEAD"]),
        "describe": _safe_run(["git", "describe", "--tags", "--always"]),
        "is_dirty": (lambda v: (None if v is None else ("yes" if v == "1" else "no")))(
            _safe_run(["git", "status", "--porcelain"])
            and "1"
        ),
    }


def _packages_map() -> Dict[str, str]:
    pkgs: Dict[str, str] = {}
    try:
        for dist in importlib_metadata.distributions():
            name = (dist.metadata.get("Name") or dist.metadata.get("Summary") or "").strip()
            if not name:
                continue
            pkgs[name] = dist.version
    except Exception:
        pass
    return dict(sorted(pkgs.items(), key=lambda kv: kv[0].lower()))
def build_run_log(argv: Optional[Tuple[str, ...]] = None) -> RunLog:
    argv = argv if argv is not None else tuple(sys.argv)
    py = f"{sys.version.split()[0]} ({sys.executable})"
    plat = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or "",
        "python_implementation": platform.python_implementation(),
    }
    return RunLog(
        created_utc=_utc_now_iso(),
        cwd=str(Path.cwd()),
        argv=tuple(argv),
        python=py,
        platform=plat,
        packages=_packages_map(),
        git=_git_info(),
    )


def write_run_log(path: os.PathLike[str] | str, *, argv: Optional[Tuple[str, ...]] = None) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    log = build_run_log(argv=argv)
    p.write_text(json.dumps(log.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def configure_logging(
    *,
    log_file: os.PathLike[str] | str | None = None,
    level: str = "INFO",
    fmt: str = "%(asctime)s %(levelname)s %(name)s: %(message)s",
) -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    for h in list(logger.handlers):
        logger.removeHandler(h)

    formatter = logging.Formatter(fmt)

    sh = logging.StreamHandler(stream=sys.stderr)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    if log_file:
        p = Path(log_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(p, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
def _default_runlog_path(out_dir: Optional[str]) -> Path:
    base = Path(out_dir) if out_dir else Path.cwd() / "outputs"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return base / "run_logs" / f"runlog_{ts}.json"


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="reprokit", description="Reproducibility utilities (run logs, standardized logging).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_log = sub.add_parser("runlog", help="Write a JSON run log with timestamp, git info, and package versions.")
    p_log.add_argument("--out", default=None, help="Output directory (default: ./outputs).")
    p_log.add_argument("--path", default=None, help="Explicit output file path (overrides --out).")
    p_log.add_argument("--print", action="store_true", help="Also print the JSON run log to stdout.")

    p_cfg = sub.add_parser("configure-logging", help="Configure root logging to stderr and optionally to a file.")
    p_cfg.add_argument("--log-file", default=None, help="Optional log file path.")
    p_cfg.add_argument("--level", default="INFO", help="Logging level (default: INFO).")

    ns = parser.parse_args(list(argv) if argv is not None else None)

    if ns.cmd == "runlog":
        out_path = Path(ns.path) if ns.path else _default_runlog_path(ns.out)
        p = write_run_log(out_path, argv=tuple(sys.argv))
        if ns.print:
            sys.stdout.write(p.read_text(encoding="utf-8"))
        sys.stderr.write(f"WROTE_RUNLOG:{p}\n")
        return 0

    if ns.cmd == "configure-logging":
        configure_logging(log_file=ns.log_file, level=ns.level)
        logging.getLogger(__name__).info("Logging configured.")
        return 0

    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
