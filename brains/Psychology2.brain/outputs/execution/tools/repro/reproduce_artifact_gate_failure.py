#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, sys, stat, time, uuid, subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]

def _now_run_id() -> str:
    return time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]

def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def _chmod_no_perms(p: Path) -> None:
    try:
        p.chmod(0)
    except Exception:
        pass

def _restore_perms(p: Path) -> None:
    try:
        p.chmod(stat.S_IRWXU)
    except Exception:
        pass

def _write_file(p: Path, text: str) -> None:
    _ensure(p.parent)
    p.write_text(text, encoding="utf-8")

def _gate_cmd() -> list[str]:
    gate = BASE / "tools" / "artifact_gate.py"
    if gate.exists():
        return [sys.executable, str(gate)]
    return []

def _run_gate(run_id: str, cwd: Path, env: dict[str, str]) -> int:
    cmd = _gate_cmd()
    if not cmd:
        print("SKIP: tools/artifact_gate.py not found; preflight reproduction will be effective once gate exists.", file=sys.stderr)
        return 127
    e = os.environ.copy()
    e.update(env)
    e.setdefault("RUN_ID", run_id)
    e.setdefault("BUILD_DIR", str(BASE / "_build" / run_id))
    e.setdefault("LOG_DIR", str(BASE / "_build" / run_id / "logs"))
    return subprocess.run(cmd, cwd=str(cwd), env=e).returncode

def _project_sandbox(run_id: str) -> Path:
    root = BASE / "tools" / "repro" / "_sandbox" / run_id
    _ensure(root)
    _write_file(root / "README.txt", "sandbox for artifact gate reproduction\n")
    return root

def scenario_wrong_cwd(run_id: str) -> int:
    sb = _project_sandbox(run_id)
    good = BASE
    os.chdir(str(sb))
    env = {
        "EXPECTED_PROJECT_ROOT": str(good),
        "ARTIFACTS_GLOB": str(good / "_build" / run_id / "artifacts" / "*.json"),
        "EXPECTED_PATHS": str(good / "_build" / run_id),
    }
    return _run_gate(run_id, cwd=sb, env=env)

def scenario_missing_mount(run_id: str) -> int:
    sb = _project_sandbox(run_id)
    missing = Path("/nonexistent_mount_xyz") / run_id
    env = {
        "EXPECTED_PROJECT_ROOT": str(BASE),
        "EXPECTED_PATHS": str(missing),
        "ARTIFACTS_GLOB": str(missing / "**" / "*.json"),
    }
    return _run_gate(run_id, cwd=BASE, env=env)

def scenario_permission_denied(run_id: str) -> int:
    sb = _project_sandbox(run_id)
    blocked = sb / "blocked_dir"
    _ensure(blocked)
    _chmod_no_perms(blocked)
    try:
        env = {
            "EXPECTED_PROJECT_ROOT": str(BASE),
            "EXPECTED_PATHS": str(blocked),
            "ARTIFACTS_GLOB": str(blocked / "*.json"),
        }
        return _run_gate(run_id, cwd=BASE, env=env)
    finally:
        _restore_perms(blocked)

def scenario_empty_glob(run_id: str) -> int:
    sb = _project_sandbox(run_id)
    empty_dir = sb / "empty_artifacts"
    _ensure(empty_dir)
    env = {
        "EXPECTED_PROJECT_ROOT": str(BASE),
        "EXPECTED_PATHS": str(empty_dir),
        "ARTIFACTS_GLOB": str(empty_dir / "*.definitely_not_here"),
    }
    return _run_gate(run_id, cwd=BASE, env=env)

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Reproduce common artifact gate CI/container failure causes.")
    ap.add_argument("--mode", choices=["wrong-cwd", "missing-mount", "permission-denied", "empty-glob", "all"], default="all")
    ap.add_argument("--run-id", default=os.environ.get("RUN_ID") or _now_run_id())
    args = ap.parse_args(argv)

    run_id = args.run_id
    _ensure(BASE / "_build" / run_id / "logs")

    modes = [args.mode] if args.mode != "all" else ["wrong-cwd", "missing-mount", "permission-denied", "empty-glob"]
    rc = 0
    for m in modes:
        if m == "wrong-cwd":
            rc = scenario_wrong_cwd(run_id)
        elif m == "missing-mount":
            rc = scenario_missing_mount(run_id)
        elif m == "permission-denied":
            rc = scenario_permission_denied(run_id)
        elif m == "empty-glob":
            rc = scenario_empty_glob(run_id)
        if rc != 0:
            return rc
    return rc

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
