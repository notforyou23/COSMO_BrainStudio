#!/usr/bin/env python3
"""Record benchmark reproducibility metadata.

Writes a metadata JSON either as a sidecar file (default) or embedded into an
existing JSON benchmark output.

Captured fields: UTC timestamp, Python version/implementation, platform details,
selected (or all) installed package versions, and git commit/tag (best-effort).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

try:
    from importlib import metadata as importlib_metadata  # py3.8+
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore
def _run_git(args: Iterable[str], cwd: Optional[Path] = None) -> Optional[str]:
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        out = p.stdout.strip()
        return out or None
    except Exception:
        return None


def _git_info(cwd: Path) -> Dict[str, Optional[str]]:
    commit = _run_git(["rev-parse", "HEAD"], cwd=cwd)
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    # exact tag if on a tag; otherwise try a descriptive string
    tag = _run_git(["describe", "--tags", "--exact-match"], cwd=cwd)
    describe = _run_git(["describe", "--tags", "--dirty", "--always"], cwd=cwd)
    return {"commit": commit, "branch": branch, "tag": tag, "describe": describe}
def _python_info() -> Dict[str, Any]:
    return {
        "version": sys.version.replace("\n", " "),
        "version_info": list(sys.version_info[:]),
        "executable": sys.executable,
        "implementation": platform.python_implementation(),
    }


def _platform_info() -> Dict[str, Any]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
    }


def _timestamp_utc_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()
def _dist_version(name: str) -> Optional[str]:
    try:
        return importlib_metadata.version(name)
    except Exception:
        return None


def _all_packages() -> Dict[str, str]:
    pkgs: Dict[str, str] = {}
    try:
        for dist in importlib_metadata.distributions():
            meta_name = dist.metadata.get("Name") if hasattr(dist, "metadata") else None
            name = (meta_name or getattr(dist, "name", None) or "").strip()
            ver = getattr(dist, "version", None) or ""
            if name and ver:
                pkgs[name] = ver
    except Exception:
        pass
    return dict(sorted(pkgs.items(), key=lambda kv: kv[0].lower()))


def _selected_packages(names: Iterable[str]) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {}
    for n in names:
        n = n.strip()
        if n:
            out[n] = _dist_version(n)
    return out
def build_metadata(
    *,
    cwd: Optional[Path] = None,
    packages: Optional[Iterable[str]] = None,
    all_packages: bool = False,
) -> Dict[str, Any]:
    cwd = cwd or Path.cwd()
    meta: Dict[str, Any] = {
        "timestamp_utc": _timestamp_utc_iso(),
        "python": _python_info(),
        "platform": _platform_info(),
        "git": _git_info(cwd),
        "env": {
            "cwd": str(cwd),
            "ci": bool(os.environ.get("CI")),
        },
    }
    if all_packages:
        meta["packages"] = _all_packages()
    elif packages:
        meta["packages"] = _selected_packages(packages)
    else:
        # Minimal defaults without blowing up file sizes.
        meta["packages"] = _selected_packages(["pip", "setuptools", "wheel"])
    return meta
def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
def record(
    benchmark_json: Path,
    *,
    embed: bool,
    output: Optional[Path] = None,
    key: str = "benchmark_metadata",
    packages: Optional[Iterable[str]] = None,
    all_packages: bool = False,
) -> Path:
    meta = build_metadata(cwd=benchmark_json.parent, packages=packages, all_packages=all_packages)
    if embed:
        data = _read_json(benchmark_json)
        if not isinstance(data, dict):
            raise SystemExit(f"Cannot embed metadata: root JSON is {type(data).__name__}, expected object.")
        data[key] = meta
        _write_json(benchmark_json, data)
        return benchmark_json
    out = output or Path(str(benchmark_json) + ".meta.json")
    _write_json(out, meta)
    return out
def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("benchmark_json", type=Path, help="Path to benchmark JSON output.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--embed", action="store_true", help="Embed metadata into benchmark JSON.")
    g.add_argument("--sidecar", action="store_true", help="Write metadata as a sidecar (default).")
    p.add_argument("--output", type=Path, default=None, help="Sidecar output path (sidecar mode only).")
    p.add_argument("--key", default="benchmark_metadata", help="JSON key to use when embedding.")
    p.add_argument("--packages", nargs="*", default=None, help="Specific packages to record versions for.")
    p.add_argument("--all-packages", action="store_true", help="Record all installed packages (may be large).")
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    ns = parse_args(argv)
    if not ns.benchmark_json.exists():
        raise SystemExit(f"Benchmark JSON not found: {ns.benchmark_json}")
    embed = bool(ns.embed)
    out_path = record(
        ns.benchmark_json,
        embed=embed,
        output=None if embed else ns.output,
        key=ns.key,
        packages=ns.packages,
        all_packages=bool(ns.all_packages),
    )
    # Keep output short for CI logs.
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
