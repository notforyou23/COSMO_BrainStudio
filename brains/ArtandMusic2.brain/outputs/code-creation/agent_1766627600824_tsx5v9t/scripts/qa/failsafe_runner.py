#!/usr/bin/env python3
"""No-container failsafe QA runner.

Runs a reduced, deterministic local test subset with strict timeouts and structured artifacts.
Designed to always produce logs + partial results even if full/container QA is unavailable.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional
def _now() -> float:
    return time.time()


def _iso(ts: Optional[float] = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts or _now()))


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + f"\n...<truncated {len(s) - limit} chars>\n"


def _repo_root(cwd: Path) -> Path:
    p = cwd
    for _ in range(6):
        if (p / ".git").exists() or (p / "pyproject.toml").exists() or (p / "setup.cfg").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return cwd
def _discover_test_files(root: Path, max_files: int) -> List[str]:
    candidates: List[Path] = []
    for base in [root / "tests", root]:
        if not base.exists():
            continue
        for pat in ("test_*.py", "*_test.py"):
            candidates.extend(base.rglob(pat))
    uniq = sorted({p.resolve() for p in candidates})
    out: List[str] = []
    for p in uniq:
        try:
            out.append(str(p.relative_to(root)))
        except Exception:
            out.append(str(p))
        if len(out) >= max_files:
            break
    return out


def _can_run_pytest(cwd: Path) -> bool:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return r.returncode == 0
    except Exception:
        return False
def _run_cmd(
    cmd: List[str],
    cwd: Path,
    env: Dict[str, str],
    timeout_s: int,
    output_limit: int,
) -> Dict[str, Any]:
    t0 = _now()
    rec: Dict[str, Any] = {
        "cmd": cmd,
        "cwd": str(cwd),
        "started_at": _iso(t0),
        "timeout_s": timeout_s,
    }
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        rec.update(
            {
                "returncode": p.returncode,
                "duration_s": round(_now() - t0, 3),
                "stdout": _truncate(p.stdout or "", output_limit),
                "stderr": _truncate(p.stderr or "", output_limit),
                "timed_out": False,
            }
        )
    except subprocess.TimeoutExpired as e:
        rec.update(
            {
                "returncode": 124,
                "duration_s": round(_now() - t0, 3),
                "stdout": _truncate(getattr(e, "stdout", "") or "", output_limit),
                "stderr": _truncate(getattr(e, "stderr", "") or "", output_limit),
                "timed_out": True,
            }
        )
    except Exception:
        rec.update(
            {
                "returncode": 125,
                "duration_s": round(_now() - t0, 3),
                "stdout": "",
                "stderr": _truncate(traceback.format_exc(), output_limit),
                "timed_out": False,
            }
        )
    rec["finished_at"] = _iso()
    return rec
def build_plan(repo: Path, max_tests: int) -> Dict[str, Any]:
    tests = _discover_test_files(repo, max_tests)
    plan: Dict[str, Any] = {
        "repo_root": str(repo),
        "selected_test_files": tests,
        "uses_pytest": False,
        "commands": [],
    }
    if tests and _can_run_pytest(repo):
        plan["uses_pytest"] = True
        plan["commands"] = [
            [sys.executable, "-m", "pytest", "-q", "--disable-warnings", "--maxfail=1", *tests],
        ]
        return plan

    plan["commands"] = [
        [sys.executable, "-m", "compileall", "-q", "."],
        [sys.executable, "-c", "import sys; print('python', sys.version.replace('\n',' '))"],
    ]
    return plan
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="No-container failsafe QA runner")
    ap.add_argument("--outputs-dir", default=os.environ.get("QA_OUTPUTS_DIR", "outputs/qa"))
    ap.add_argument("--timeout-s", type=int, default=int(os.environ.get("QA_FAILSAFE_TIMEOUT_S", "300")))
    ap.add_argument("--max-tests", type=int, default=int(os.environ.get("QA_FAILSAFE_MAX_TESTS", "10")))
    ap.add_argument("--output-limit", type=int, default=int(os.environ.get("QA_FAILSAFE_OUTPUT_LIMIT", "200000")))
    ap.add_argument("--cwd", default=os.environ.get("QA_CWD", ""))
    args = ap.parse_args(argv)

    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd().resolve()
    repo = _repo_root(cwd)
    out_dir = _ensure_dir((repo / args.outputs_dir).resolve())
    run_dir = _ensure_dir(out_dir / "failsafe")
    logs_dir = _ensure_dir(run_dir / "logs")

    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")

    meta = {
        "mode": "failsafe",
        "started_at": _iso(),
        "cwd": str(cwd),
        "repo_root": str(repo),
        "python": sys.executable,
        "argv": sys.argv,
        "timeout_s": args.timeout_s,
        "max_tests": args.max_tests,
        "output_limit": args.output_limit,
    }
    _write_json(run_dir / "run_metadata.json", meta)

    results: Dict[str, Any] = {"meta": meta, "plan": None, "steps": [], "ok": False}
    combined_out: List[str] = []
    combined_err: List[str] = []

    try:
        plan = build_plan(repo, args.max_tests)
        results["plan"] = plan
        _write_json(run_dir / "plan.json", plan)

        for i, cmd in enumerate(plan["commands"]):
            rec = _run_cmd(cmd, repo, env, args.timeout_s, args.output_limit)
            rec["step"] = i
            results["steps"].append(rec)

            combined_out.append(f"$ {' '.join(cmd)}\n{rec.get('stdout','')}")
            combined_err.append(f"$ {' '.join(cmd)}\n{rec.get('stderr','')}")

            _write_json(run_dir / "partial_results.json", results)
            _write_text(logs_dir / "stdout.log", "\n\n".join(combined_out).strip() + "\n")
            _write_text(logs_dir / "stderr.log", "\n\n".join(combined_err).strip() + "\n")

        results["ok"] = all(s.get("returncode", 1) == 0 for s in results["steps"])
        results["finished_at"] = _iso()
        _write_json(run_dir / "results.json", results)
        return 0 if results["ok"] else 1
    except Exception:
        err = {"finished_at": _iso(), "traceback": traceback.format_exc()}
        _write_json(run_dir / "error.json", err)
        results["finished_at"] = _iso()
        _write_json(run_dir / "results.json", results)
        _write_text(logs_dir / "stderr.log", (logs_dir / "stderr.log").read_text(encoding="utf-8", errors="replace") + "\n" + err["traceback"] + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
