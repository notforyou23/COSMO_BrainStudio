"""record_versions.py

Utility to capture Python/OS/package versions and inject them into JSON run logs.

Usage:
  python -m scripts.record_versions --log path/to/run.json
  python scripts/record_versions.py --log path/to/run.json
  python scripts/record_versions.py --print
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import sys
from pathlib import Path

try:
    from importlib import metadata as importlib_metadata  # py3.8+
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore


def _utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds")


def _safe_str(x) -> str:
    try:
        return str(x)
    except Exception:
        return repr(x)


def _collect_packages() -> list[dict]:
    pkgs = []
    try:
        for dist in importlib_metadata.distributions():
            name = dist.metadata.get("Name") or getattr(dist, "name", None) or "UNKNOWN"
            version = getattr(dist, "version", None) or dist.metadata.get("Version") or "UNKNOWN"
            pkgs.append({"name": _safe_str(name), "version": _safe_str(version)})
    except Exception:
        return []
    pkgs.sort(key=lambda d: (d.get("name") or "").lower())
    return pkgs


def collect_versions() -> dict:
    uname = platform.uname()
    info = {
        "capturedAtUtc": _utc_now_iso(),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "build": _safe_str(platform.python_build()),
            "executable": _safe_str(sys.executable),
            "argv0": _safe_str(sys.argv[0] if sys.argv else ""),
            "prefix": _safe_str(sys.prefix),
            "basePrefix": _safe_str(getattr(sys, "base_prefix", "")),
        },
        "os": {
            "platform": _safe_str(sys.platform),
            "name": _safe_str(os.name),
            "release": _safe_str(platform.release()),
            "version": _safe_str(platform.version()),
            "system": _safe_str(platform.system()),
            "machine": _safe_str(platform.machine()),
            "processor": _safe_str(platform.processor()),
            "uname": {
                "system": _safe_str(uname.system),
                "node": _safe_str(uname.node),
                "release": _safe_str(uname.release),
                "version": _safe_str(uname.version),
                "machine": _safe_str(uname.machine),
                "processor": _safe_str(uname.processor),
            },
        },
        "packages": _collect_packages(),
    }
    return info


def inject_into_run_log(log_path: Path, key: str = "environment") -> dict:
    log_path = Path(log_path)
    data = {}
    if log_path.exists():
        try:
            data = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {"_original": data}

    env = collect_versions()
    existing = data.get(key)
    if isinstance(existing, dict):
        # Preserve prior capture(s) but overwrite the latest snapshot deterministically.
        env["previous"] = existing
    data[key] = env

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Capture versions and inject into JSON run logs.")
    p.add_argument("--log", type=str, default="", help="Path to a JSON run log to update in-place.")
    p.add_argument("--key", type=str, default="environment", help="JSON key to write the version record under.")
    p.add_argument("--print", dest="do_print", action="store_true", help="Print version record JSON to stdout.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.do_print:
        print(json.dumps(collect_versions(), indent=2, sort_keys=True))
        return 0
    if not args.log:
        raise SystemExit("Expected --log PATH or --print")
    inject_into_run_log(Path(args.log), key=args.key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
