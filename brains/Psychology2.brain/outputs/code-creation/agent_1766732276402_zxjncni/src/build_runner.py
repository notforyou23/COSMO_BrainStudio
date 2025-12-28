"""Single-command build runner.

Runs (in order): artifact gate -> taxonomy validation -> meta-analysis demo.
Standardizes outputs under runtime/_build/, fails fast, and writes a final summary.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

STEPS = (
    ("artifact_gate", "Artifact gate"),
    ("taxonomy_validation", "Taxonomy validation"),
    ("meta_analysis_demo", "Meta-analysis demo"),
)

DEFAULT_CMDS = {
    "artifact_gate": os.environ.get("BUILD_ARTIFACT_CMD", ""),
    "taxonomy_validation": os.environ.get("BUILD_TAXONOMY_CMD", ""),
    "meta_analysis_demo": os.environ.get("BUILD_META_CMD", ""),
}


def _project_root() -> Path:
    # .../src/build_runner.py -> project root is parent of src
    return Path(__file__).resolve().parents[1]


def _build_root(root: Path) -> Path:
    return root / "runtime" / "_build"


def _ts() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def _split_cmd(cmd: str) -> list[str]:
    if not cmd.strip():
        return []
    return shlex.split(cmd)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_step(step_key: str, label: str, cmd: str, out_dir: Path, env: dict[str, str] | None) -> dict:
    step_dir = out_dir / step_key
    step_dir.mkdir(parents=True, exist_ok=True)
    log_path = step_dir / "raw.log"
    summary_path = step_dir / "summary.json"

    argv = _split_cmd(cmd)
    if not argv:
        msg = (
            f"Missing command for step '{step_key}'. Provide via CLI (--{step_key.replace('_', '-')}-cmd) "
            f"or env var BUILD_{step_key.split('_')[0].upper()}_CMD / BUILD_{step_key.split('_')[1].upper()}_CMD, or set the appropriate BUILD_*_CMD."
        )
        result = {
            "step": step_key,
            "label": label,
            "command": cmd,
            "ok": False,
            "returncode": 2,
            "error": msg,
            "log_path": str(log_path),
            "started_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "ended_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "duration_s": 0.0,
        }
        _write_json(summary_path, result)
        raise RuntimeError(msg)

    started = time.time()
    started_at = _dt.datetime.now().isoformat(timespec="seconds")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"# step={step_key}\n# cmd={cmd}\n# started_at={started_at}\n\n")
        f.flush()
        proc = subprocess.Popen(argv, cwd=str(_project_root()), stdout=f, stderr=subprocess.STDOUT, env=env)
        rc = proc.wait()

    ended = time.time()
    ended_at = _dt.datetime.now().isoformat(timespec="seconds")
    ok = (rc == 0)
    result = {
        "step": step_key,
        "label": label,
        "command": cmd,
        "ok": ok,
        "returncode": rc,
        "log_path": str(log_path),
        "summary_path": str(summary_path),
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_s": round(ended - started, 6),
    }
    if not ok:
        result["error"] = f"Step '{step_key}' failed with exit code {rc}. See log: {log_path}"
    _write_json(summary_path, result)
    if not ok:
        raise RuntimeError(result["error"])
    return result


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="build_runner", description="Sequential build runner with standardized outputs.")
    p.add_argument("--out-dir", default="", help="Output directory (default: <repo>/runtime/_build).")
    p.add_argument("--run-id", default="", help="Run identifier subdir (default: timestamp).")
    p.add_argument("--keep-going", action="store_true", help="Do not fail fast (still returns nonzero if any failed).")
    p.add_argument("--artifact-gate-cmd", default=DEFAULT_CMDS["artifact_gate"], help="Command for artifact gate step.")
    p.add_argument("--taxonomy-validation-cmd", default=DEFAULT_CMDS["taxonomy_validation"], help="Command for taxonomy validation step.")
    p.add_argument("--meta-analysis-demo-cmd", default=DEFAULT_CMDS["meta_analysis_demo"], help="Command for meta-analysis demo step.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(sys.argv[1:] if argv is None else argv)
    root = _project_root()
    out_base = Path(ns.out_dir).expanduser().resolve() if ns.out_dir else _build_root(root)
    run_id = ns.run_id.strip() or _ts()
    out_dir = out_base / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["BUILD_OUT_DIR"] = str(out_dir)
    env["BUILD_RUN_ID"] = run_id

    cmd_map = {
        "artifact_gate": ns.artifact_gate_cmd,
        "taxonomy_validation": ns.taxonomy_validation_cmd,
        "meta_analysis_demo": ns.meta_analysis_demo_cmd,
    }

    results = []
    started_at = _dt.datetime.now().isoformat(timespec="seconds")
    overall_ok = True
    for step_key, label in STEPS:
        try:
            res = _run_step(step_key, label, cmd_map[step_key], out_dir, env)
            results.append(res)
            print(f"OK  {step_key} -> {res['duration_s']}s")
        except Exception as e:
            overall_ok = False
            err_msg = str(e)
            print(f"FAIL {step_key}: {err_msg}", file=sys.stderr)
            if not ns.keep_going:
                break
            results.append({
                "step": step_key,
                "label": label,
                "command": cmd_map.get(step_key, ""),
                "ok": False,
                "returncode": 1,
                "error": err_msg,
            })

    ended_at = _dt.datetime.now().isoformat(timespec="seconds")
    summary = {
        "ok": overall_ok and all(r.get("ok") for r in results) and len(results) == len(STEPS),
        "project_root": str(root),
        "out_dir": str(out_dir),
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "steps": results,
    }
    _write_json(out_dir / "final_summary.json", summary)
    (out_dir / ("SUCCESS" if summary["ok"] else "FAILED")).write_text("\n", encoding="utf-8")

    print(f"FINAL {'SUCCESS' if summary['ok'] else 'FAILED'} (out={out_dir})")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
