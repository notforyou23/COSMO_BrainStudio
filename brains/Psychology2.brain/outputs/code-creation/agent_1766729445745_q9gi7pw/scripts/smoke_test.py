#!/usr/bin/env python3
"""Minimal, fast smoke test for preflight diagnostics.

Verifies:
- Python runtime basics (version, executable)
- Key imports (stdlib)
- Basic filesystem read/write
- Best-effort network sanity (DNS/TCP), optionally strict via env vars
"""

from __future__ import annotations

import os
import sys
import time
import json
import socket
import tempfile
import platform
from pathlib import Path


def _check(name, fn):
    t0 = time.time()
    try:
        detail = fn()
        return {"name": name, "ok": True, "ms": int((time.time() - t0) * 1000), "detail": detail}
    except Exception as e:
        return {"name": name, "ok": False, "ms": int((time.time() - t0) * 1000), "error": f"{type(e).__name__}: {e}"}


def _python_runtime():
    v = sys.version_info
    if v < (3, 8):
        raise RuntimeError(f"Python>=3.8 required, got {v.major}.{v.minor}.{v.micro}")
    return {"version": platform.python_version(), "executable": sys.executable, "platform": platform.platform()}


def _imports():
    import ssl  # noqa: F401
    import subprocess  # noqa: F401
    import urllib.request  # noqa: F401
    import hashlib  # noqa: F401
    import sqlite3  # noqa: F401
    return {"imports": ["ssl", "subprocess", "urllib.request", "hashlib", "sqlite3"]}


def _filesystem_rw():
    root = Path(os.environ.get("SMOKE_TEST_DIR", ""))
    base_dir = None
    if root and root.exists() and root.is_dir():
        base_dir = str(root)
    with tempfile.TemporaryDirectory(prefix="smoke_test_", dir=base_dir) as d:
        p = Path(d) / "probe.txt"
        payload = f"ok:{time.time()}"
        p.write_text(payload, encoding="utf-8")
        readback = p.read_text(encoding="utf-8")
        if readback != payload:
            raise RuntimeError("readback mismatch")
        if not os.access(d, os.W_OK):
            raise RuntimeError("temp dir not writable")
    return {"writable": True}


def _network_best_effort():
    # Defaults: attempt network check but do not fail the whole smoke test unless strict.
    strict = os.environ.get("SMOKE_TEST_STRICT_NETWORK", "0") == "1"
    enabled = os.environ.get("SMOKE_TEST_NETWORK", "1") != "0"
    if not enabled:
        return {"enabled": False, "strict": strict}

    timeout_s = float(os.environ.get("SMOKE_TEST_NET_TIMEOUT_S", "1.0"))
    socket.setdefaulttimeout(timeout_s)

    results = {"enabled": True, "strict": strict, "timeout_s": timeout_s, "dns": None, "tcp": None}
    errors = []

    try:
        infos = socket.getaddrinfo("example.com", 443, proto=socket.IPPROTO_TCP)
        results["dns"] = {"ok": True, "addrs": sorted({i[4][0] for i in infos})[:3]}
    except Exception as e:
        results["dns"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        errors.append("dns")

    # Try a TCP connect to example.com:443 (quick handshake only).
    try:
        with socket.create_connection(("example.com", 443), timeout=timeout_s) as s:
            s.settimeout(timeout_s)
            results["tcp"] = {"ok": True, "peer": s.getpeername()[0]}
    except Exception as e:
        results["tcp"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        errors.append("tcp")

    if strict and errors:
        raise RuntimeError("network checks failed: " + ",".join(errors))
    return results


def run():
    checks = [
        _check("python_runtime", _python_runtime),
        _check("imports", _imports),
        _check("filesystem_rw", _filesystem_rw),
        _check("network_best_effort", _network_best_effort),
    ]
    ok = all(c["ok"] for c in checks if c["name"] != "network_best_effort" or os.environ.get("SMOKE_TEST_STRICT_NETWORK", "0") == "1")
    return {"ok": ok, "checks": checks}


def main(argv=None):
    report = run()
    out = json.dumps(report, sort_keys=True)
    print(out)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
