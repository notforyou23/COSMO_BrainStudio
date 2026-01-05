from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _tool_version() -> str:
    try:
        from .version import __version__  # type: ignore
        return str(__version__)
    except Exception:
        try:
            from . import __version__  # type: ignore
            return str(__version__)
        except Exception:
            return "0.0.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_dir(outputs_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = outputs_dir / "logs" / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(s, encoding="utf-8")
    tmp.replace(p)


def _resolve_cmd(env_key: str, candidates: List[List[str]]) -> Optional[List[str]]:
    v = os.environ.get(env_key)
    if v:
        parts = shlex.split(v)
        if parts:
            return parts
    for cmd in candidates:
        exe = cmd[0]
        if shutil.which(exe):
            return cmd
    return None


def _run_one(name: str, cmd: List[str], cwd: Path, run_dir: Path, artifacts_dir: Path) -> Dict[str, Any]:
    start = time.time()
    started_at = _utc_now_iso()
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )
    ended_at = _utc_now_iso()
    dur_s = round(time.time() - start, 6)

    out_p = run_dir / f"{name}.stdout.txt"
    err_p = run_dir / f"{name}.stderr.txt"
    _write_text(out_p, p.stdout or "")
    _write_text(err_p, p.stderr or "")

    return {
        "name": name,
        "cmd": cmd,
        "cwd": str(cwd),
        "artifacts_dir": str(artifacts_dir),
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_s": dur_s,
        "returncode": int(p.returncode),
        "stdout_path": str(out_p),
        "stderr_path": str(err_p),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="json-cli-tool")
    parser.add_argument("--artifacts-dir", default=None, help="Path to outputs/artifacts (default: <project>/outputs/artifacts)")
    parser.add_argument("--outputs-dir", default=None, help="Path to outputs/ (default: <project>/outputs)")
    args = parser.parse_args(argv)

    root = _project_root()
    outputs_dir = Path(args.outputs_dir).expanduser().resolve() if args.outputs_dir else (root / "outputs")
    artifacts_dir = Path(args.artifacts_dir).expanduser().resolve() if args.artifacts_dir else (outputs_dir / "artifacts")

    run_dir = _run_dir(outputs_dir)
    console_path = run_dir / "console.txt"
    log_path = run_dir / "log.json"

    artifact_cmd = _resolve_cmd(
        "ARTIFACT_GATE_CMD",
        [
            ["artifact-gate", str(artifacts_dir)],
            ["artifact_gate", str(artifacts_dir)],
            [sys.executable, "-m", "artifact_gate", str(artifacts_dir)],
        ],
    )
    taxonomy_cmd = _resolve_cmd(
        "TAXONOMY_VALIDATOR_CMD",
        [
            ["taxonomy-validator", str(artifacts_dir)],
            ["taxonomy_validator", str(artifacts_dir)],
            [sys.executable, "-m", "taxonomy_validator", str(artifacts_dir)],
        ],
    )

    run_log: Dict[str, Any] = {
        "tool": {"name": "generated_cli_tool_1766726690727", "version": _tool_version()},
        "run": {"started_at": _utc_now_iso(), "run_dir": str(run_dir)},
        "inputs": {"outputs_dir": str(outputs_dir), "artifacts_dir": str(artifacts_dir)},
        "steps": [],
        "exit_code": 0,
    }

    console_chunks: List[str] = []
    overall = 0
    cwd = root

    for name, cmd in (("artifact_gate", artifact_cmd), ("taxonomy_validator", taxonomy_cmd)):
        if not cmd:
            msg = f"[{name}] command not found; set env {('ARTIFACT_GATE_CMD' if name=='artifact_gate' else 'TAXONOMY_VALIDATOR_CMD')}\n"
            console_chunks.append(msg)
            run_log["steps"].append({"name": name, "error": "command_not_found", "returncode": 127})
            overall = max(overall, 127)
            continue
        step = _run_one(name, cmd, cwd=cwd, run_dir=run_dir, artifacts_dir=artifacts_dir)
        run_log["steps"].append(step)
        overall = max(overall, int(step.get("returncode", 0)))
        try:
            console_chunks.append(f"=== {name} ===\n")
            console_chunks.append((Path(step["stdout_path"]).read_text(encoding="utf-8") or ""))
            stderr_txt = Path(step["stderr_path"]).read_text(encoding="utf-8") or ""
            if stderr_txt:
                console_chunks.append("\n--- stderr ---\n")
                console_chunks.append(stderr_txt)
            console_chunks.append("\n")
        except Exception as e:
            console_chunks.append(f"[{name}] failed to aggregate console output: {e}\n")
            overall = max(overall, 1)

    run_log["exit_code"] = int(overall)
    run_log["run"]["ended_at"] = _utc_now_iso()

    _write_text(console_path, "".join(console_chunks))
    _write_text(log_path, json.dumps(run_log, indent=2, sort_keys=True) + "\n")

    sys.stdout.write(f"run_dir={run_dir}\n")
    sys.stdout.write(f"log_json={log_path}\n")
    sys.stdout.write(f"console_txt={console_path}\n")
    return int(overall)


if __name__ == "__main__":
    raise SystemExit(main())
