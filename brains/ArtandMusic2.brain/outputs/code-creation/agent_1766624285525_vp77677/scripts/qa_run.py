#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs" / "qa"


def _utc_run_id(prefix: str = "qa") -> str:
    ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{ts}_{os.getpid()}_{secrets.token_hex(4)}"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_index(run_dir: Path, meta: dict) -> Path:
    files = []
    for p in sorted(run_dir.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(run_dir).as_posix()
        try:
            st = p.stat()
            files.append(
                {
                    "path": rel,
                    "bytes": st.st_size,
                    "sha256": _sha256(p),
                }
            )
        except FileNotFoundError:
            continue
    index = {
        "schema": "outputs.qa.index.v1",
        "run_dir": str(run_dir),
        "created_utc": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "meta": meta,
        "files": files,
    }
    out = run_dir / "index.json"
    out.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _run_subprocess(cmd: list[str], cwd: Path, env: dict, check: bool = False) -> int:
    p = subprocess.run(cmd, cwd=str(cwd), env=env)
    if check and p.returncode != 0:
        raise SystemExit(p.returncode)
    return p.returncode


def _default_workflow_cmd() -> list[str]:
    env_cmd = os.environ.get("QA_WORKFLOW_CMD", "").strip()
    if env_cmd:
        import shlex
        return shlex.split(env_cmd)
    candidate = REPO_ROOT / "scripts" / "qa_workflow.py"
    if candidate.is_file():
        return [sys.executable, str(candidate)]
    return [sys.executable, "-c", "print('No QA workflow configured; set QA_WORKFLOW_CMD or add scripts/qa_workflow.py')"]


def _find_validate_outputs() -> Path | None:
    p = REPO_ROOT / "scripts" / "validate_outputs.py"
    return p if p.is_file() else None


def _run_validate_outputs(validate_py: Path, run_dir: Path) -> int:
    candidates = [
        [sys.executable, str(validate_py), str(run_dir)],
        [sys.executable, str(validate_py), "--input", str(run_dir)],
        [sys.executable, str(validate_py), "--path", str(run_dir)],
        [sys.executable, str(validate_py), "--root", str(run_dir)],
        [sys.executable, str(validate_py), "--qa-dir", str(run_dir)],
    ]
    last_rc = 2
    for cmd in candidates:
        try:
            r = subprocess.run(cmd, cwd=str(REPO_ROOT))
            last_rc = r.returncode
            if last_rc in (0, 1):
                return last_rc
        except Exception:
            continue
    return last_rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="qa_run", description="Canonical single-command QA runner.")
    ap.add_argument("--run-id", default=None, help="Optional run id; default auto-generated.")
    ap.add_argument("--outputs-root", default=str(OUTPUTS_ROOT), help="Root outputs/qa directory.")
    ap.add_argument("--keep-existing", action="store_true", help="Do not error if run dir exists.")
    ap.add_argument("--validate-only", action="store_true", help="Skip workflow execution; only validate.")
    ap.add_argument("--", dest="dashdash", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="Workflow command after '--' (optional).")
    args = ap.parse_args(argv)

    run_id = args.run_id or _utc_run_id()
    outputs_root = Path(args.outputs_root).resolve()
    run_dir = outputs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=args.keep_existing)

    env = os.environ.copy()
    env["QA_RUN_ID"] = run_id
    env["QA_OUTPUT_DIR"] = str(run_dir)
    env["OUTPUT_DIR"] = str(run_dir)
    env["OUTPUTS_DIR"] = str(run_dir)

    meta = {
        "run_id": run_id,
        "repo_root": str(REPO_ROOT),
        "workflow_cmd": None,
        "python": sys.executable,
    }

    workflow_rc = 0
    if not args.validate_only:
        cmd = [c for c in args.cmd if c != "--"]
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            cmd = _default_workflow_cmd()
        meta["workflow_cmd"] = cmd
        workflow_rc = _run_subprocess(cmd, cwd=run_dir, env=env, check=False)

    _write_index(run_dir, meta)

    validate_py = _find_validate_outputs()
    validate_rc = 0
    if validate_py is not None:
        validate_rc = _run_validate_outputs(validate_py, run_dir)
    else:
        (run_dir / "validation_skipped.txt").write_text(
            "validate_outputs.py not found; validation skipped.\n", encoding="utf-8"
        )

    (run_dir / "run_status.json").write_text(
        json.dumps(
            {
                "schema": "outputs.qa.status.v1",
                "run_id": run_id,
                "workflow_returncode": workflow_rc,
                "validate_returncode": validate_rc,
                "ok": (workflow_rc == 0 and validate_rc == 0),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if workflow_rc != 0:
        return workflow_rc
    return validate_rc


if __name__ == "__main__":
    raise SystemExit(main())
