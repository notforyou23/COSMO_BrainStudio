import os
import subprocess
import sys
from pathlib import Path

import pytest


def _run(cmd, cwd):
    p = subprocess.run(
        [sys.executable, "-m", "psyprim.cli", *cmd],
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    return p


def _run_any(candidates, cwd):
    last = None
    for cmd in candidates:
        p = _run(cmd, cwd)
        last = p
        if p.returncode == 0:
            return p
    msg = (
        "All candidate invocations failed. Last command: "
        + repr(candidates[-1])
        + "\nrc="
        + str(last.returncode)
        + "\nstdout=\n"
        + (last.stdout or "")
        + "\nstderr=\n"
        + (last.stderr or "")
    )
    raise AssertionError(msg)


def _any_project_artifact(root: Path):
    for pat in ("**/.psyprim/*", "**/*psyprim*.json", "**/*psyprim*.yml", "**/*psyprim*.yaml", "**/*psyprim*.toml"):
        if list(root.glob(pat)):
            return True
    return False


def test_cli_help_subcommands():
    for sub in ("init", "validate", "flag", "variant", "cite", "export-eval"):
        p = _run([sub, "--help"], Path.cwd())
        assert p.returncode == 0, (sub, p.stdout, p.stderr)


def test_cli_end_to_end_workflow(tmp_path):
    # init
    _run_any(
        [
            ["init"],
            ["init", "."],
            ["init", str(tmp_path)],
            ["init", "--path", "."],
            ["init", "--force"],
            ["init", ".", "--force"],
            ["init", "--path", ".", "--force"],
        ],
        tmp_path,
    )
    assert _any_project_artifact(tmp_path) or any(tmp_path.iterdir())

    # validate
    _run_any([["validate"], ["validate", "."], ["validate", "--path", "."]], tmp_path)

    # provenance flag (try several shapes)
    _run_any(
        [
            ["flag", "add", "uncertain_date"],
            ["flag", "--add", "uncertain_date"],
            ["flag", "set", "uncertain_date", "true"],
            ["flag", "uncertain_date"],
            ["flag"],
        ],
        tmp_path,
    )

    # variant numbering
    _run_any(
        [
            ["variant", "new"],
            ["variant", "add", "scan"],
            ["variant", "--new"],
            ["variant"],
        ],
        tmp_path,
    )

    # cite (allow stdout or file output)
    cite_out = tmp_path / "citations.bib"
    p_cite = _run_any(
        [
            ["cite", "--out", str(cite_out)],
            ["cite", str(cite_out)],
            ["cite", "--format", "bibtex"],
            ["cite"],
        ],
        tmp_path,
    )
    if cite_out.exists():
        assert cite_out.read_text(encoding="utf-8").strip()
    else:
        assert (p_cite.stdout or "").strip() or (p_cite.stderr or "").strip()

    # export evaluation data (allow stdout or file output)
    eval_out = tmp_path / "evaluation_export.json"
    p_eval = _run_any(
        [
            ["export-eval", "--out", str(eval_out)],
            ["export-eval", str(eval_out)],
            ["export-eval", "--format", "json", "--out", str(eval_out)],
            ["export-eval"],
        ],
        tmp_path,
    )
    if eval_out.exists():
        assert eval_out.read_text(encoding="utf-8").strip()
    else:
        assert (p_eval.stdout or "").strip() or (p_eval.stderr or "").strip()
