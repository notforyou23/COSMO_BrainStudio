#!/usr/bin/env python3
"""Canonical artifact verification script.

Runs lightweight validation against artifacts under runtime/_build/ and writes:
- runtime/_build/verify/raw/* (stdout/stderr per command)
- runtime/_build/verify/report.json + report.txt (summary)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _repo_root() -> Path:
    # scripts/verify_artifacts.py -> repo root is parent of scripts/
    return Path(__file__).resolve().parents[1]


def _build_dir(root: Path) -> Path:
    return root / "runtime" / "_build"


def _safe_name(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", s.strip())
    return s[:120] if s else "cmd"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_cmd(cmd: List[str], cwd: Path, env: Optional[Dict[str, str]], timeout: int) -> Dict[str, Any]:
    t0 = time.time()
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "cmd": cmd,
            "returncode": cp.returncode,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
            "duration_s": round(time.time() - t0, 3),
        }
    except subprocess.TimeoutExpired as e:
        return {
            "cmd": cmd,
            "returncode": 124,
            "stdout": (e.stdout or ""),
            "stderr": (e.stderr or "") + f"\nTIMEOUT after {timeout}s",
            "duration_s": round(time.time() - t0, 3),
        }
    except Exception as e:
        return {
            "cmd": cmd,
            "returncode": 125,
            "stdout": "",
            "stderr": f"EXCEPTION: {type(e).__name__}: {e}",
            "duration_s": round(time.time() - t0, 3),
        }


def _write_raw(raw_dir: Path, idx: int, result: Dict[str, Any]) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    name = _safe_name(" ".join(result.get("cmd", [])))
    stem = f"{idx:02d}_{name}"
    (raw_dir / f"{stem}.stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8", errors="replace")
    (raw_dir / f"{stem}.stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8", errors="replace")


def _inventory(build_dir: Path) -> Dict[str, Any]:
    inv: Dict[str, Any] = {"build_dir": str(build_dir), "files": [], "counts": {}}
    if not build_dir.exists():
        inv["missing"] = True
        return inv
    for p in sorted(build_dir.rglob("*")):
        if p.is_file():
            try:
                rel = str(p.relative_to(build_dir))
            except Exception:
                rel = str(p)
            inv["files"].append(
                {
                    "path": rel,
                    "size": p.stat().st_size,
                    "sha256": _sha256(p) if p.stat().st_size <= 50 * 1024 * 1024 else None,
                }
            )
            inv["counts"][p.suffix] = inv["counts"].get(p.suffix, 0) + 1
    inv["total_files"] = len(inv["files"])
    return inv


def _collect_candidates(build_dir: Path) -> Dict[str, List[Path]]:
    dist = build_dir / "dist"
    candidates = {
        "wheels": sorted(dist.glob("*.whl")) if dist.exists() else [],
        "sdists": sorted([*dist.glob("*.tar.gz"), *dist.glob("*.zip")]) if dist.exists() else [],
    }
    return candidates


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Verify artifacts under runtime/_build/ and write a verification report.")
    ap.add_argument("--build-dir", default=None, help="Override build dir (default: <repo>/runtime/_build).")
    ap.add_argument("--timeout", type=int, default=120, help="Per-command timeout seconds.")
    ap.add_argument("--strict", action="store_true", help="Fail if no artifacts found in runtime/_build/dist.")
    args = ap.parse_args(argv)

    root = _repo_root()
    build_dir = Path(args.build_dir).resolve() if args.build_dir else _build_dir(root)
    verify_dir = build_dir / "verify"
    raw_dir = verify_dir / "raw"
    verify_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "schema_version": 1,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo_root": str(root),
        "build_dir": str(build_dir),
        "python": {"executable": sys.executable, "version": sys.version},
        "platform": {"platform": sys.platform, "cwd": os.getcwd()},
        "inventory": _inventory(build_dir),
        "checks": [],
        "ok": True,
    }

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    checks: List[Tuple[str, List[str], Path]] = []

    # Basic sanity: build dir exists and is readable; compileall scripts as a quick smoke test.
    checks.append(("compileall_scripts", [sys.executable, "-m", "compileall", "-q", str(root / "scripts")], root))

    # Optional: if src/ exists, compile it too.
    if (root / "src").exists():
        checks.append(("compileall_src", [sys.executable, "-m", "compileall", "-q", str(root / "src")], root))

    # Artifact integrity checks
    cand = _collect_candidates(build_dir)
    for whl in cand["wheels"]:
        checks.append((f"wheel_zip_test:{whl.name}", [sys.executable, "-m", "zipfile", "-t", str(whl)], build_dir))
    for sdist in cand["sdists"]:
        if sdist.name.endswith(".tar.gz"):
            checks.append(
                (f"sdist_tar_list:{sdist.name}", [sys.executable, "-c", "import tarfile,sys; tarfile.open(sys.argv[1]).getmembers(); print('OK')", str(sdist)], build_dir)
            )
        elif sdist.name.endswith(".zip"):
            checks.append((f"sdist_zip_test:{sdist.name}", [sys.executable, "-m", "zipfile", "-t", str(sdist)], build_dir))

    # Strict mode: ensure dist contains something.
    dist_dir = build_dir / "dist"
    if args.strict and (not dist_dir.exists() or not any(dist_dir.iterdir())):
        report["ok"] = False
        report["checks"].append({"name": "dist_nonempty", "returncode": 2, "stdout": "", "stderr": "No artifacts found in runtime/_build/dist", "duration_s": 0.0})
    else:
        report["checks"].append({"name": "dist_nonempty", "returncode": 0, "stdout": "", "stderr": "", "duration_s": 0.0})

    # Execute checks
    idx = 0
    for name, cmd, cwd in checks:
        idx += 1
        res = _run_cmd(cmd, cwd=cwd, env=env, timeout=args.timeout)
        res["name"] = name
        report["checks"].append({k: res[k] for k in ("name", "cmd", "returncode", "duration_s")})
        _write_raw(raw_dir, idx, res)
        if res.get("returncode", 1) != 0:
            report["ok"] = False

    # Summarize
    failures = [c for c in report["checks"] if int(c.get("returncode", 0)) != 0]
    report["summary"] = {
        "ok": bool(report["ok"]),
        "total_checks": len(report["checks"]),
        "failed_checks": len(failures),
        "artifacts": {
            "wheels": [p.name for p in cand["wheels"]],
            "sdists": [p.name for p in cand["sdists"]],
        },
        "outputs": {
            "raw_dir": str(raw_dir),
            "report_json": str(verify_dir / "report.json"),
            "report_txt": str(verify_dir / "report.txt"),
        },
    }

    (verify_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = []
    lines.append(f"verify_artifacts: ok={report['ok']}")
    lines.append(f"build_dir: {build_dir}")
    lines.append(f"checks: {report['summary']['total_checks']} total, {report['summary']['failed_checks']} failed")
    if failures:
        lines.append("failed:")
        for c in failures:
            lines.append(f"  - {c.get('name')} (rc={c.get('returncode')})")
    (verify_dir / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
