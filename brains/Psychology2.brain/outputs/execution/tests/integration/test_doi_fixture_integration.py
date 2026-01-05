from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
@dataclass(frozen=True)
class Fixture:
    doi: str
    expect_success: bool
    note: str = ""


def _repo_root() -> Path:
    # tests/integration/<file> -> root
    return Path(__file__).resolve().parents[3]


def _fixture_path() -> Path:
    return _repo_root() / "tests" / "fixtures" / "doi_fixture_list.json"


def _artifact_dir() -> Path:
    root = _repo_root()
    preferred = root / "outputs" / "tools"
    fallback = root / "runtime" / "_build"
    out = preferred if preferred.exists() else fallback
    out.mkdir(parents=True, exist_ok=True)
    return out


def _load_fixtures() -> List[Fixture]:
    fp = _fixture_path()
    if not fp.exists():
        pytest.skip(f"Missing fixture list: {fp}")
    data = json.loads(fp.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("fixtures") or data.get("items") or []
    if not isinstance(data, list) or not data:
        pytest.skip(f"Empty/invalid fixture list: {fp}")
    out: List[Fixture] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        doi = (item.get("doi") or item.get("DOI") or "").strip()
        if not doi:
            continue
        exp = item.get("expected_success")
        if exp is None:
            exp = item.get("expect_success")
        if exp is None:
            exp = item.get("expected") in ("success", "ok", True)
        note = (item.get("note") or item.get("notes") or "").strip()
        out.append(Fixture(doi=doi, expect_success=bool(exp), note=note))
    if not out:
        pytest.skip(f"No usable fixtures in: {fp}")
    return out
def _find_api_server() -> Optional[Path]:
    root = _repo_root()
    candidates = [
        root / "api_server.py",
        root / "src" / "api_server.py",
        root / "app" / "api_server.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _run_help(script: Path) -> str:
    try:
        cp = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        return (cp.stdout or "") + "
" + (cp.stderr or "")
    except Exception:
        return ""


def _build_command(script: Path, doi: str) -> Tuple[List[str], Optional[str]]:
    help_text = _run_help(script)
    py = sys.executable

    # Prefer explicit DOI flag if present in help output.
    if "--doi" in help_text:
        cmd = [py, str(script), "--doi", doi]
        if "--format" in help_text:
            cmd += ["--format", "json"]
        elif "--json" in help_text:
            cmd += ["--json"]
        return cmd, None

    # Subcommand pattern: resolve <doi>
    if " resolve " in help_text or "\nresolve " in help_text:
        cmd = [py, str(script), "resolve", doi]
        if "--json" in help_text:
            cmd += ["--json"]
        return cmd, None

    # Last resort: feed DOI via stdin (single line)
    return [py, str(script)], doi + "\n"


def _try_parse_json(text: str) -> Optional[Any]:
    t = (text or "").strip()
    if not t:
        return None
    # Some CLIs may print logs; try last JSON-looking line first.
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    for cand in (lines[-1:], lines[-5:], lines):
        for ln in reversed(cand):
            if ln.startswith("{") or ln.startswith("["):
                try:
                    return json.loads(ln)
                except Exception:
                    pass
    try:
        return json.loads(t)
    except Exception:
        return None


def _looks_success(payload: Any) -> bool:
    if payload is None:
        return False
    if isinstance(payload, dict):
        if payload.get("error") or payload.get("errors") or payload.get("detail") == "Not Found":
            return False
        if payload.get("ok") is False or payload.get("success") is False:
            return False
    return True
def test_doi_fixture_integration(tmp_path: Path) -> None:
    fixtures = _load_fixtures()
    script = _find_api_server()
    if script is None:
        pytest.skip("api_server.py not found (expected at repo root or src/)")

    artifact_base = _artifact_dir() / "doi_fixture_integration"
    artifact_base.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    any_unexpected = False

    for fx in fixtures:
        cmd, stdin = _build_command(script, fx.doi)
        cp = subprocess.run(
            cmd,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        payload = _try_parse_json(cp.stdout)
        success_signal = (cp.returncode == 0) and _looks_success(payload)
        ok = success_signal if fx.expect_success else (not success_signal)

        if not ok:
            any_unexpected = True

        results.append(
            {
                "doi": fx.doi,
                "expected_success": fx.expect_success,
                "note": fx.note,
                "cmd": " ".join(cmd),
                "returncode": cp.returncode,
                "ok": ok,
                "stdout": (cp.stdout or "").strip(),
                "stderr": (cp.stderr or "").strip(),
                "parsed_json": payload,
            }
        )

    json_path = artifact_base / "results.json"
    csv_path = artifact_base / "results.csv"
    json_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["doi", "expected_success", "ok", "returncode", "note", "cmd"],
        )
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in w.fieldnames})

    if any_unexpected:
        bad = [r for r in results if not r["ok"]]
        lines = [
            "Unexpected DOI fixture outcomes:",
            *(f"- {b['doi']} expected_success={b['expected_success']} rc={b['returncode']}" for b in bad[:10]),
            f"Artifacts: {artifact_base}",
        ]
        pytest.fail("\n".join(lines))
