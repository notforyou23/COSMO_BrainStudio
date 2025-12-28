from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


REQUIRED_SECTION_PATTERNS = [
    r"\bstakeholder\b.*\bengagement\b",
    r"\btechnical\b.*\brequirements\b",
    r"\bvalidation\b.*\bstudy\b",
    r"\bsurvey\b",
    r"\baudit\b",
    r"\bphased\b.*\brollout\b",
    r"\bmilestone\b",
    r"\badoption\b",
    r"\bevaluation\b",
    r"\bprovenance\b",
    r"\bedition\b",
    r"\btranslation\b",
    r"\bpagination\b|\bpage\b.*\bmarker\b|\bparagraph\b.*\bmarker\b",
    r"\bpublic\b[- ]domain\b.*\brepositor(y|ies)\b|\brepository\b.*\bcitation\b",
]


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _digest_tree(root: Path) -> dict[str, str]:
    files = [p for p in root.rglob("*") if p.is_file()]
    rels = sorted(str(p.relative_to(root)) for p in files)
    out: dict[str, str] = {}
    for rel in rels:
        p = root / rel
        out[rel] = _sha256_bytes(p.read_bytes())
    return out


def _run_cli_py(outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "protocol_planner.cli",
        "--output-dir",
        str(outdir),
        "--scope",
        "primary-source psychology scholarship",
        "--corpora",
        "public-domain books, journal articles",
        "--stakeholders",
        "scholars,librarians,editors,tool-developers,repositories",
        "--repositories",
        "Internet Archive,HathiTrust,Wikisource,Project Gutenberg",
        "--seed",
        "0",
    ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)


def _run_cli_import(outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    from protocol_planner import cli as cli_mod  # type: ignore

    argv = [
        "--output-dir",
        str(outdir),
        "--scope",
        "primary-source psychology scholarship",
        "--corpora",
        "public-domain books, journal articles",
        "--stakeholders",
        "scholars,librarians,editors,tool-developers,repositories",
        "--repositories",
        "Internet Archive,HathiTrust,Wikisource,Project Gutenberg",
        "--seed",
        "0",
    ]
    for fn_name in ("main", "cli_main", "run"):
        fn = getattr(cli_mod, fn_name, None)
        if callable(fn):
            ret = fn(argv)
            if isinstance(ret, int) and ret != 0:
                raise RuntimeError(f"CLI returned non-zero: {ret}")
            return
    raise AttributeError("protocol_planner.cli must expose a callable main/cli_main/run")


def run_cli(outdir: Path) -> None:
    try:
        _run_cli_py(outdir)
    except Exception:
        _run_cli_import(outdir)


def _find_plan_text(outdir: Path) -> str:
    md_files = [p for p in outdir.rglob("*.md") if p.is_file()]
    if not md_files:
        txt_files = [p for p in outdir.rglob("*.txt") if p.is_file()]
        if txt_files:
            return txt_files[0].read_text(encoding="utf-8", errors="replace")
        raise AssertionError("No .md plan file produced in output directory")
    md_files.sort(key=lambda p: (len(str(p)), str(p)))
    return md_files[0].read_text(encoding="utf-8", errors="replace")


def _assert_required_sections(plan_text: str) -> None:
    lowered = plan_text.lower()
    missing = [pat for pat in REQUIRED_SECTION_PATTERNS if not re.search(pat, lowered, flags=re.IGNORECASE | re.DOTALL)]
    assert not missing, f"Plan missing required section keywords/patterns: {missing}"
    assert re.search(r"\bM\d+\b|\bmonth\s*\d+\b|\bquarter\s*\d+\b|\byear\s*\d+\b", plan_text, flags=re.IGNORECASE), \
        "Plan should include time-bounded milestones (e.g., Month 1 / Q1 / Year 1 / M1)."
    assert re.search(r"\b\d+%|\bN\s*=\s*\d+|\b(n|sample)\b.*\b\d+\b", plan_text, flags=re.IGNORECASE), \
        "Plan should include measurable targets (e.g., percentages, sample sizes, N=...)."


def _load_json_files(outdir: Path) -> list[tuple[Path, object]]:
    json_files = [p for p in outdir.rglob("*.json") if p.is_file()]
    loaded = []
    for p in json_files:
        try:
            loaded.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return loaded


def _assert_has_valid_json_schema(outdir: Path) -> None:
    loaded = _load_json_files(outdir)
    assert loaded, "No JSON artifacts produced (expected at least one JSON Schema or metadata artifact)."

    schemas = []
    for p, obj in loaded:
        if isinstance(obj, dict) and ("$schema" in obj or ("type" in obj and "properties" in obj)):
            schemas.append((p, obj))
    assert schemas, "No JSON Schema-like artifact found (expected $schema/type/properties)."

    # Validate JSON Schema structure; prefer jsonschema library if available.
    try:
        import jsonschema  # type: ignore
        for p, schema in schemas:
            if hasattr(jsonschema, "Draft202012Validator"):
                jsonschema.Draft202012Validator.check_schema(schema)
            elif hasattr(jsonschema, "Draft7Validator"):
                jsonschema.Draft7Validator.check_schema(schema)
            else:
                jsonschema.validators.validator_for(schema).check_schema(schema)
    except Exception:
        # Minimal structural checks if jsonschema isn't available or check_schema fails unexpectedly.
        for p, schema in schemas:
            assert isinstance(schema, dict)
            assert schema.get("type", "object") in ("object",), f"{p.name} schema should be object-typed"
            assert "properties" in schema and isinstance(schema["properties"], dict) and schema["properties"], \
                f"{p.name} schema must define non-empty properties"


@pytest.mark.parametrize("runner", ["cli"])
def test_cli_produces_complete_plan_and_artifacts(tmp_path: Path, runner: str) -> None:
    outdir = tmp_path / "out"
    run_cli(outdir)

    plan_text = _find_plan_text(outdir)
    _assert_required_sections(plan_text)

    _assert_has_valid_json_schema(outdir)

    produced_files = [p for p in outdir.rglob("*") if p.is_file()]
    assert produced_files, "CLI produced no files"


def test_deterministic_outputs(tmp_path: Path) -> None:
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    run_cli(out1)
    run_cli(out2)

    d1 = _digest_tree(out1)
    d2 = _digest_tree(out2)

    assert d1 == d2, "CLI outputs should be deterministic given identical inputs/seed"


def test_plan_mentions_plugins_or_software_and_provenance_fields(tmp_path: Path) -> None:
    outdir = tmp_path / "out"
    run_cli(outdir)
    plan_text = _find_plan_text(outdir).lower()

    assert re.search(r"\b(plugin|extension|software|tooling|library|cli)\b", plan_text), \
        "Plan should describe lightweight software/plugins/tooling."
    assert re.search(r"\b(edition|translation)\b.*\b(provenance|source|variant)\b", plan_text, flags=re.DOTALL), \
        "Plan should cover edition/translation provenance and variants."
    assert re.search(r"\b(pagination|page|paragraph)\b.*\b(marker|offset|anchor)\b", plan_text, flags=re.DOTALL), \
        "Plan should cover pagination/paragraph markers and anchoring."
    assert re.search(r"\b(public[- ]domain|repository)\b.*\b(cite|citation|identifier|url|doi|handle)\b", plan_text, flags=re.DOTALL), \
        "Plan should cover public-domain repository citations/identifiers."
