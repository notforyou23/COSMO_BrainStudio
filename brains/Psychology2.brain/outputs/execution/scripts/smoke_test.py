#!/usr/bin/env python3
"""Tiny smoke-test for runner environments.

- Verifies basic Python/runtime invariants
- Imports required/optional dependencies
- Writes an environment fingerprint JSON (for run logs)
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _parse_csv_env(name: str, default: str) -> List[str]:
    val = os.getenv(name, default).strip()
    if not val:
        return []
    return [x.strip() for x in val.split(",") if x.strip()]


def _import_module(modname: str) -> Tuple[bool, str]:
    try:
        __import__(modname)
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _safe_git_head(cwd: Path) -> Dict[str, Any]:
    try:
        head = cwd / ".git" / "HEAD"
        if not head.is_file():
            return {"present": False}
        txt = head.read_text(encoding="utf-8", errors="replace").strip()
        info: Dict[str, Any] = {"present": True, "HEAD": txt}
        if txt.startswith("ref:"):
            ref = txt.split(":", 1)[1].strip()
            ref_path = cwd / ".git" / ref
            if ref_path.is_file():
                info["ref"] = ref
                info["commit"] = ref_path.read_text(encoding="utf-8", errors="replace").strip()
        return info
    except Exception as e:
        return {"present": None, "error": f"{type(e).__name__}: {e}"}


def _installed_packages() -> Dict[str, str]:
    try:
        from importlib import metadata as im

        pkgs: Dict[str, str] = {}
        for d in im.distributions():
            name = (d.metadata.get("Name") or "").strip()
            if not name:
                continue
            ver = (d.version or "").strip()
            key = name.lower()
            if key not in pkgs:
                pkgs[key] = ver
        return dict(sorted(pkgs.items(), key=lambda kv: kv[0]))
    except Exception:
        return {}


def _fingerprint(required: List[str], optional: List[str], cwd: Path) -> Dict[str, Any]:
    imports: Dict[str, Any] = {"required": {}, "optional": {}}
    for mod in required:
        ok, err = _import_module(mod)
        imports["required"][mod] = {"ok": ok, "error": err or None}
    for mod in optional:
        ok, err = _import_module(mod)
        imports["optional"][mod] = {"ok": ok, "error": err or None}

    fp: Dict[str, Any] = {
        "schema": "smoke_test.fingerprint.v1",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cwd": str(cwd),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "version_info": list(sys.version_info),
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "platform": platform.platform(),
        },
        "env": {
            "PATH": os.getenv("PATH", ""),
            "PYTHONPATH": os.getenv("PYTHONPATH", ""),
            "VIRTUAL_ENV": os.getenv("VIRTUAL_ENV", ""),
        },
        "git": _safe_git_head(cwd),
        "imports": imports,
        "packages": _installed_packages(),
    }
    return fp


def main() -> int:
    ap = argparse.ArgumentParser(description="Environment smoke-test + fingerprint writer")
    ap.add_argument("--out", default=os.getenv("SMOKE_OUT", ""), help="Output JSON path")
    ap.add_argument("--print", dest="do_print", action="store_true", help="Also print fingerprint JSON to stdout")
    args = ap.parse_args()

    cwd = Path.cwd()
    required = _parse_csv_env("SMOKE_REQUIRED_IMPORTS", "jsonschema,requests,yaml")
    optional = _parse_csv_env("SMOKE_OPTIONAL_IMPORTS", "numpy,pandas,pydantic,orjson,rapidjson")

    fp = _fingerprint(required=required, optional=optional, cwd=cwd)

    missing = [m for m, r in fp["imports"]["required"].items() if not r.get("ok")]
    fp["status"] = {"ok": not missing, "missing_required": missing}

    out_path = Path(args.out) if args.out else cwd / "environment.fingerprint.json"
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(fp, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        fp["status"]["ok"] = False
        fp["status"]["write_error"] = traceback.format_exc()

    if args.do_print:
        print(json.dumps(fp, indent=2, sort_keys=True))

    if missing:
        print("SMOKE_FAIL: missing required imports: " + ", ".join(missing))
        print("FINGERPRINT_WRITTEN:" + str(out_path))
        return 1

    if not fp["status"].get("ok", False):
        print("SMOKE_FAIL: fingerprint write failed")
        print("FINGERPRINT_WRITTEN:" + str(out_path))
        return 2

    print("SMOKE_OK")
    print("FINGERPRINT_WRITTEN:" + str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
