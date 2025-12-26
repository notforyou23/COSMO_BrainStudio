#!/usr/bin/env python3
"""End-to-end pipeline orchestrator for CI.

Runs a sequence of stages, captures stdout/stderr and timing, writes structured
JSON logs/artifacts, and emits a failure summary for downstream CI automation.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
def _utc_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def _parse_stages(args) -> list[dict]:
    # Priority: CLI --stage, env E2E_STAGES_JSON, file e2e_stages.json, defaults.
    stages: list[dict] = []
    for s in args.stage or []:
        name, cmd = (s.split("::", 1) + [""])[:2]
        name, cmd = name.strip(), cmd.strip()
        if not name or not cmd:
            raise SystemExit(f"Invalid --stage {s!r}. Expected 'name::command'.")
        stages.append({"name": name, "cmd": cmd})

    if not stages and os.getenv("E2E_STAGES_JSON"):
        try:
            stages = json.loads(os.environ["E2E_STAGES_JSON"])
        except json.JSONDecodeError as e:
            raise SystemExit(f"Invalid E2E_STAGES_JSON: {e}") from e

    if not stages:
        cfg = Path("e2e_stages.json")
        if cfg.is_file():
            stages = json.loads(cfg.read_text(encoding="utf-8"))

    if not stages:
        stages = [
            {"name": "python_version", "cmd": f"{sys.executable} -V"},
            {"name": "compileall", "cmd": f"{sys.executable} -m compileall -q ."},
        ]
    # Normalize/validate.
    out = []
    for st in stages:
        if not isinstance(st, dict) or "name" not in st or "cmd" not in st:
            raise SystemExit("Stages must be objects with 'name' and 'cmd'.")
        out.append({"name": str(st["name"]), "cmd": str(st["cmd"])})
    return out
def _run_stage(stage: dict, out_dir: Path, idx: int) -> dict:
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in stage["name"])
    prefix = f"{idx:02d}_{safe}"
    log_dir = out_dir / "stages"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{prefix}.stdout.log"
    stderr_path = log_dir / f"{prefix}.stderr.log"

    t0 = time.time()
    start = _utc_now()
    p = subprocess.Popen(
        stage["cmd"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    stdout, stderr = p.communicate()
    end = _utc_now()
    dur_s = round(time.time() - t0, 3)

    stdout_path.write_text(stdout or "", encoding="utf-8")
    stderr_path.write_text(stderr or "", encoding="utf-8")

    return {
        "name": stage["name"],
        "cmd": stage["cmd"],
        "returncode": p.returncode,
        "started_at": start,
        "ended_at": end,
        "duration_s": dur_s,
        "stdout_path": str(stdout_path.relative_to(out_dir)),
        "stderr_path": str(stderr_path.relative_to(out_dir)),
    }
def _manifest(out_dir: Path) -> dict:
    files = []
    for p in sorted(out_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(out_dir).as_posix()
            files.append({"path": rel, "bytes": p.stat().st_size, "sha256": _sha256(p)})
    return {"generated_at": _utc_now(), "file_count": len(files), "files": files}
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True, help="Artifact output directory.")
    ap.add_argument(
        "--stage",
        action="append",
        help="Stage in form 'name::command' (repeatable). Overrides defaults.",
    )
    ap.add_argument("--continue-on-failure", action="store_true")
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_meta = {
        "started_at": _utc_now(),
        "cwd": str(Path.cwd()),
        "python": sys.version.split()[0],
        "argv": [sys.executable, *argv],
    }

    stages = _parse_stages(args)
    results, failures = [], []
    for i, st in enumerate(stages, 1):
        res = _run_stage(st, out_dir, i)
        results.append(res)
        if res["returncode"] != 0:
            failures.append(res)
            if not args.continue_on_failure:
                break

    run_meta["ended_at"] = _utc_now()
    run_meta["ok"] = len(failures) == 0
    summary = {"run": run_meta, "stages": results}
    _write_json(out_dir / "summary.json", summary)

    if failures:
        f = failures[0]
        repro = [
            "git clone <repo_url>",
            "cd <repo>",
            f"python3 scripts/e2e.py --out-dir /tmp/e2e --stage {shlex.quote(f['name'] + '::' + f['cmd'])}",
        ]
        failure_summary = {
            "failed": True,
            "failed_stage": f,
            "repro_steps": repro,
            "summary_path": str((out_dir / "summary.json").resolve()),
        }
        _write_json(out_dir / "failure_summary.json", failure_summary)
        # Print a short, CI-friendly summary.
        print(f"E2E_FAILED stage={f['name']} rc={f['returncode']} stdout={f['stdout_path']} stderr={f['stderr_path']}")
    else:
        print("E2E_OK")

    _write_json(out_dir / "manifest.json", _manifest(out_dir))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
