from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _python() -> str:
    return sys.executable


def _run_id() -> str:
    # keep deterministic enough for assertions, unique per test execution
    return f"testrun_{os.getpid()}"


def _logs_dir(repo: Path, run_id: str) -> Path:
    return repo / "_build" / run_id / "logs"


def _read_all_logs_text(logs_dir: Path) -> str:
    if not logs_dir.exists():
        return ""
    parts = []
    for p in sorted(logs_dir.rglob("*")):
        if p.is_file():
            try:
                parts.append(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                parts.append(f"<<UNREADABLE:{p}>>")
    return "\n".join(parts)


def _assert_logs_created(logs_dir: Path) -> None:
    assert logs_dir.exists(), f"expected logs dir to exist: {logs_dir}"
    files = [p for p in logs_dir.rglob("*") if p.is_file()]
    assert files, f"expected at least one log file under: {logs_dir}"


def _call_artifact_gate(repo: Path, run_id: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["RUN_ID"] = run_id
    if extra_env:
        env.update(extra_env)

    # Try common entrypoints; tests should still be informative if script moves.
    candidates = [
        repo / "tools" / "artifact_gate.py",
        repo / "artifact_gate.py",
        repo / "tools" / "validators" / "artifacts_validator.py",
    ]
    script = next((p for p in candidates if p.exists()), None)
    assert script is not None, f"expected an entrypoint script at one of: {candidates}"

    return subprocess.run(
        [_python(), str(script)],
        cwd=str(repo),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@pytest.mark.parametrize(
    "missing_env_key,missing_path",
    [
        ("EXPECTED_PATH_MISSING", "this/does/not/exist"),
    ],
)
def test_preflight_logs_missing_paths(tmp_path: Path, missing_env_key: str, missing_path: str) -> None:
    repo = _repo_root()
    run_id = _run_id() + "_missing"
    logs_dir = _logs_dir(repo, run_id)
    if logs_dir.exists():
        for p in sorted(logs_dir.rglob("*"), reverse=True):
            try:
                p.unlink()
            except Exception:
                pass

    # Provide an explicit missing path hint to preflight/validators.
    # Implementations are expected to scan common env vars for expected paths.
    cp = _call_artifact_gate(repo, run_id, {missing_env_key: str(repo / missing_path)})

    _assert_logs_created(logs_dir)
    txt = _read_all_logs_text(logs_dir).lower()

    assert ("missing" in txt or "not found" in txt or "does not exist" in txt), (
        "expected missing-path diagnostics in logs"
    )
    assert missing_path.split("/")[0] in txt or missing_path in txt, "expected missing path to be referenced in logs"

    # Expect failure exit when required paths are missing
    assert cp.returncode != 0, f"expected non-zero exit code, got {cp.returncode} stdout={cp.stdout} stderr={cp.stderr}"


def test_preflight_logs_permission_issues(tmp_path: Path) -> None:
    repo = _repo_root()
    run_id = _run_id() + "_perm"
    logs_dir = _logs_dir(repo, run_id)
    if logs_dir.exists():
        for p in sorted(logs_dir.rglob("*"), reverse=True):
            try:
                p.unlink()
            except Exception:
                pass

    protected_dir = tmp_path / "protected"
    protected_dir.mkdir(parents=True, exist_ok=True)
    # remove all permissions
    protected_dir.chmod(0)

    try:
        cp = _call_artifact_gate(repo, run_id, {"EXPECTED_PATH_PROTECTED": str(protected_dir)})
        _assert_logs_created(logs_dir)
        txt = _read_all_logs_text(logs_dir).lower()

        assert ("permission" in txt or "eacces" in txt or "access denied" in txt), (
            "expected permission diagnostics in logs"
        )
        assert "protected" in txt, "expected protected path to be referenced in logs"
        assert cp.returncode != 0, f"expected non-zero exit code, got {cp.returncode} stdout={cp.stdout} stderr={cp.stderr}"
    finally:
        # restore permissions so tmp cleanup can proceed
        try:
            protected_dir.chmod(stat.S_IRWXU)
        except Exception:
            pass


def test_preflight_logs_glob_empty_conditions(tmp_path: Path) -> None:
    repo = _repo_root()
    run_id = _run_id() + "_glob"
    logs_dir = _logs_dir(repo, run_id)
    if logs_dir.exists():
        for p in sorted(logs_dir.rglob("*"), reverse=True):
            try:
                p.unlink()
            except Exception:
                pass

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(empty_dir / "*.no_such_ext")

    cp = _call_artifact_gate(repo, run_id, {"EXPECTED_GLOB": pattern})

    _assert_logs_created(logs_dir)
    txt = _read_all_logs_text(logs_dir).lower()

    # Expect explicit mention of glob expansion being empty or yielding zero matches.
    assert ("glob" in txt or "pattern" in txt), "expected glob-related diagnostics in logs"
    assert ("0 match" in txt or "no match" in txt or "empty" in txt), "expected empty-glob diagnostics in logs"
    assert ".no_such_ext" in txt or "no_such_ext" in txt, "expected glob pattern to be referenced in logs"

    # Empty expected glob should be treated as failure
    assert cp.returncode != 0, f"expected non-zero exit code, got {cp.returncode} stdout={cp.stdout} stderr={cp.stderr}"


def test_preflight_always_writes_logs_before_exit(tmp_path: Path) -> None:
    repo = _repo_root()
    run_id = _run_id() + "_always"
    logs_dir = _logs_dir(repo, run_id)
    if logs_dir.exists():
        for p in sorted(logs_dir.rglob("*"), reverse=True):
            try:
                p.unlink()
            except Exception:
                pass

    # Force an error scenario that should exit quickly.
    cp = _call_artifact_gate(repo, run_id, {"EXPECTED_PATH_MISSING": str(repo / "nope/nope")})

    _assert_logs_created(logs_dir)
    txt = _read_all_logs_text(logs_dir)

    # Expect some basic environment diagnostics
    low = txt.lower()
    assert ("cwd" in low or "working directory" in low or "pwd" in low), "expected cwd/pwd diagnostics in logs"
    assert ("run_id" in low or run_id.lower() in low), "expected run_id to appear in logs"

    assert cp.returncode != 0
