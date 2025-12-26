import csv
import importlib
from pathlib import Path

import pytest


def _import_first(*names: str):
    for name in names:
        try:
            return importlib.import_module(name)
        except ModuleNotFoundError:
            continue
    raise ModuleNotFoundError(f"Could not import any of: {names}")


def _run_cli(output_dir: Path):
    cli = _import_first("src.math_coverage_cli", "math_coverage_cli")
    output_dir.mkdir(parents=True, exist_ok=True)

    args = ["--output-dir", str(output_dir)]
    if hasattr(cli, "main") and callable(cli.main):
        cli.main(args)
    elif hasattr(cli, "cli_main") and callable(cli.cli_main):
        cli.cli_main(args)
    elif hasattr(cli, "run") and callable(cli.run):
        cli.run(args)
    else:
        raise AssertionError("CLI module must expose main(argv) (or cli_main/run) callable")


def _expected_row_count():
    tax = _import_first("src.math_taxonomy", "math_taxonomy")

    artifact_types = getattr(tax, "ARTIFACT_TYPES", None) or getattr(tax, "artifact_types", None)
    if artifact_types is None and hasattr(tax, "get_artifact_types"):
        artifact_types = tax.get_artifact_types()
    if not artifact_types:
        raise AssertionError("math_taxonomy must define ARTIFACT_TYPES (or get_artifact_types())")

    # Domains/subtopics structure is intentionally flexible; tests compute count from taxonomy.
    domains = None
    if hasattr(tax, "DOMAINS"):
        domains = tax.DOMAINS
    elif hasattr(tax, "TAXONOMY"):
        domains = tax.TAXONOMY
    elif hasattr(tax, "get_taxonomy"):
        domains = tax.get_taxonomy()
    if not domains:
        raise AssertionError("math_taxonomy must define DOMAINS/TAXONOMY (or get_taxonomy())")

    pairs = []
    if isinstance(domains, dict):
        # {domain: [subtopics] or {subtopic: ...}}
        for d, subs in domains.items():
            if isinstance(subs, dict):
                subs = list(subs.keys())
            for s in subs:
                pairs.append((str(d), str(s)))
    else:
        for item in domains:
            if isinstance(item, dict):
                d = item.get("domain") or item.get("name")
                subs = item.get("subtopics") or item.get("topics") or item.get("children")
                if isinstance(subs, dict):
                    subs = list(subs.keys())
            else:
                raise AssertionError("Unsupported taxonomy element type")
            if not d or not subs:
                raise AssertionError("Each taxonomy domain must have a name and non-empty subtopics")
            for s in subs:
                pairs.append((str(d), str(s)))

    return len(pairs) * len(list(artifact_types))


def _read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return reader.fieldnames, rows
def test_cli_generates_expected_outputs(tmp_path: Path):
    out = tmp_path / "outputs"
    _run_cli(out)

    cov = out / "coverage_matrix.csv"
    evl = out / "eval_loop.md"
    assert cov.exists(), "coverage_matrix.csv was not generated"
    assert evl.exists(), "eval_loop.md was not generated"
    assert cov.stat().st_size > 0
    assert evl.stat().st_size > 0
def test_coverage_matrix_headers_and_row_count(tmp_path: Path):
    out = tmp_path / "outputs"
    _run_cli(out)

    cov = out / "coverage_matrix.csv"
    fieldnames, rows = _read_csv(cov)

    required = {"domain", "subtopic", "artifact_type", "status", "cross_links"}
    assert fieldnames is not None
    assert required.issubset(set(fieldnames)), f"Missing required headers: {required - set(fieldnames)}"

    expected = _expected_row_count()
    assert len(rows) == expected, f"Expected {expected} rows from taxonomy, got {len(rows)}"

    # Ensure placeholders are present (not null-ish) to support downstream agents.
    for r in rows[: min(10, len(rows))]:
        assert (r.get("status") or "").strip() != ""
        assert r.get("cross_links") is not None
def test_deterministic_output_across_runs(tmp_path: Path):
    out1 = tmp_path / "o1"
    out2 = tmp_path / "o2"
    _run_cli(out1)
    _run_cli(out2)

    b1 = (out1 / "coverage_matrix.csv").read_bytes().replace(b"\r\n", b"\n")
    b2 = (out2 / "coverage_matrix.csv").read_bytes().replace(b"\r\n", b"\n")
    assert b1 == b2, "coverage_matrix.csv should be byte-stable across runs"

    m1 = (out1 / "eval_loop.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    m2 = (out2 / "eval_loop.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert m1 == m2, "eval_loop.md should be stable across runs"
    assert "5-cycle" in m1 or "5 cycle" in m1 or "Cycle 5" in m1
