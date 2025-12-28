import os
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

try:
    from psyprim.cli import app  # Typer app
except Exception as e:  # pragma: no cover
    raise RuntimeError(f"Failed to import psyprim CLI app: {e!r}")


runner = CliRunner(mix_stderr=False)


def _invoke(argv, cwd: Path):
    env = os.environ.copy()
    return runner.invoke(app, argv, env=env, catch_exceptions=False, cwd=str(cwd))


def _try_invocations(invocations, cwd: Path):
    last = None
    for argv in invocations:
        last = _invoke(argv, cwd)
        if last.exit_code == 0:
            return last, argv
    return last, None


def _assert_any_file(tmp_path: Path, patterns):
    found = []
    for pat in patterns:
        found.extend(list(tmp_path.glob(pat)))
    assert found, f"Expected at least one file matching {patterns}, found none in {tmp_path}"
    return found


def _write_minimal_metadata(tmp_path: Path):
    # Create a minimal metadata file only if none exists; tolerate tool-specific schemas.
    for pat in ("*.json", "*.yaml", "*.yml", "*.toml"):
        if list(tmp_path.glob(pat)):
            return
    data = {
        "work": {
            "title": "Principles of Rigorous Primary-Source Scholarship",
            "author": "Doe, Jane",
            "year": 1900,
            "public_domain": True,
        },
        "edition": {
            "edition_statement": "1st ed.",
            "publisher": "Example Press",
            "place": "New York",
            "year": 1900,
        },
        "translation": {
            "is_translation": False,
            "translator": None,
            "source_language": "en",
            "target_language": "en",
        },
        "provenance": {
            "scan_or_source": "Local archive",
            "notes": "End-to-end test fixture",
        },
        "pagination": {"scheme": "original", "variant_pagination": []},
    }
    (tmp_path / "psyprim_metadata.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


@pytest.mark.parametrize(
    "init_invocations",
    [
        [["init"], ["init", "."], ["init", "--path", "."], ["project-init"], ["new"]],
        [["init", "--path", "."]],
    ],
)
def test_cli_end_to_end_workflow(tmp_path: Path, init_invocations):
    # 1) init
    res_init, used = _try_invocations(init_invocations, tmp_path)
    assert used is not None, f"Init failed. Last: code={res_init.exit_code}, out={res_init.stdout}, err={res_init.stderr}"

    # project scaffolds should create something (directory may already exist)
    _assert_any_file(tmp_path, ["*", ".*"])

    # 2) checklist generation (try common spellings / subcommands)
    checklist_invocations = [
        ["checklist"],
        ["checklist", "generate"],
        ["checklist", "gen"],
        ["generate-checklist"],
        ["gen-checklist"],
        ["checklist", "--path", "."],
        ["checklist", "generate", "--path", "."],
    ]
    res_chk, used_chk = _try_invocations(checklist_invocations, tmp_path)
    assert used_chk is not None, f"Checklist generation failed. Last: code={res_chk.exit_code}, out={res_chk.stdout}, err={res_chk.stderr}"
    assert (res_chk.stdout or res_chk.stderr).strip(), "Checklist command produced no output"

    # 3) metadata validation (create minimal metadata if init didn't)
    _write_minimal_metadata(tmp_path)
    validate_invocations = [
        ["validate"],
        ["validate", "."],
        ["validate", "--path", "."],
        ["metadata-validate"],
        ["check"],
        ["check", "--path", "."],
    ]
    res_val, used_val = _try_invocations(validate_invocations, tmp_path)
    assert used_val is not None, f"Validation failed. Last: code={res_val.exit_code}, out={res_val.stdout}, err={res_val.stderr}"
    assert (res_val.stdout + res_val.stderr).strip(), "Validate command produced no output"

    # 4) report / citation / provenance output
    report_invocations = [
        ["report"],
        ["report", "."],
        ["report", "--path", "."],
        ["provenance"],
        ["provenance", "--path", "."],
        ["citation"],
        ["citation", "--path", "."],
        ["cite"],
        ["cite", "--path", "."],
        ["report", "citation"],
        ["report", "provenance"],
    ]
    res_rep, used_rep = _try_invocations(report_invocations, tmp_path)
    assert used_rep is not None, f"Report/citation failed. Last: code={res_rep.exit_code}, out={res_rep.stdout}, err={res_rep.stderr}"
    out = (res_rep.stdout + res_rep.stderr).lower()
    # Keep assertions permissive: ensure mission-aligned keywords appear in at least one successful report.
    assert any(k in out for k in ["citation", "provenance", "edition", "translation", "pagination", "public domain", "public-domain"]), (
        "Report output missing expected mission-aligned terms; got: " + (res_rep.stdout + res_rep.stderr)[:500]
    )
