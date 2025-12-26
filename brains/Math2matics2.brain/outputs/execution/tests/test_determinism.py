import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _find_entrypoint(repo_root: Path) -> Path:
    candidates = [
        repo_root / "src" / "entrypoint.py",
        repo_root / "entrypoint.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    pytest.skip("entrypoint.py not found (expected src/entrypoint.py or entrypoint.py)")


def _normalize_run_mapping(run_obj):
    if not isinstance(run_obj, dict):
        return {}
    for k in ("sha256", "checksums", "artifacts", "files"):
        v = run_obj.get(k)
        if isinstance(v, dict):
            return v
    return run_obj


def _get_runs(report: dict):
    if isinstance(report.get("runs"), list) and len(report["runs"]) >= 2:
        return report["runs"][:2]
    for a, b in (("run1", "run2"), ("run_1", "run_2"), ("first", "second")):
        if a in report and b in report:
            return [report[a], report[b]]
    if isinstance(report.get("determinism"), dict):
        d = report["determinism"]
        if isinstance(d.get("runs"), list) and len(d["runs"]) >= 2:
            return d["runs"][:2]
    raise AssertionError("Could not locate two runs in determinism_report.json")


def _pick_by_basename(mapping: dict, wanted: set[str]) -> dict[str, str]:
    out = {}
    for k, v in mapping.items():
        if not isinstance(v, str):
            continue
        name = Path(str(k)).name
        if name in wanted:
            out[str(k)] = v
    return out


def _pick_logs(mapping: dict) -> dict[str, str]:
    out = {}
    for k, v in mapping.items():
        if not isinstance(v, str):
            continue
        s = str(k).lower()
        name = Path(str(k)).name.lower()
        if "log" in name or "/logs" in s or s.endswith(".log") or name.endswith(".txt") and "log" in name:
            out[str(k)] = v
    return out


@pytest.mark.timeout(180)
def test_determinism_mode_produces_identical_checksums(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    entrypoint = _find_entrypoint(repo_root)

    outputs_dir = repo_root / "outputs"
    report_path = outputs_dir / "determinism_report.json"
    if report_path.exists():
        report_path.unlink()

    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")

    cmd = [sys.executable, str(entrypoint), "--determinism"]
    subprocess.run(cmd, cwd=str(repo_root), env=env, check=True, capture_output=True, text=True)

    assert report_path.exists(), "outputs/determinism_report.json was not created by --determinism mode"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    run_a, run_b = _get_runs(report)
    map_a = _normalize_run_mapping(run_a)
    map_b = _normalize_run_mapping(run_b)

    wanted_core = {"results.json", "run_stamp.json"}
    core_a = _pick_by_basename(map_a, wanted_core)
    core_b = _pick_by_basename(map_b, wanted_core)

    assert core_a and core_b, "Report did not include checksums for results.json and run_stamp.json"
    for base in wanted_core:
        keys_a = [k for k in core_a if Path(k).name == base]
        keys_b = [k for k in core_b if Path(k).name == base]
        assert keys_a and keys_b, f"Missing checksum for {base} in one or both runs"
        assert core_a[keys_a[0]] == core_b[keys_b[0]], f"Checksum mismatch for {base}: {core_a[keys_a[0]]} != {core_b[keys_b[0]]}"

    logs_a = _pick_logs(map_a)
    logs_b = _pick_logs(map_b)
    common_logs = sorted(set(logs_a) & set(logs_b))
    assert common_logs, "Report did not include any comparable log checksums across both runs"
    for k in common_logs:
        assert logs_a[k] == logs_b[k], f"Checksum mismatch for log {k}: {logs_a[k]} != {logs_b[k]}"
