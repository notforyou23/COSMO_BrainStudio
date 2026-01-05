from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_validator(script: Path, argv_tail: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)] + argv_tail,
        cwd=str(_repo_root()),
        text=True,
        capture_output=True,
    )


def _try_cli_forms(script: Path, schema: Path, codebook: Path, annotations: Path) -> tuple[list[str], subprocess.CompletedProcess]:
    forms: list[list[str]] = [
        [str(annotations), "--schema", str(schema), "--codebook", str(codebook)],
        ["--schema", str(schema), "--codebook", str(codebook), str(annotations)],
        ["--schema", str(schema), str(annotations)],
        [str(annotations)],
        ["--inputs", str(annotations), "--schema", str(schema), "--codebook", str(codebook)],
        ["--annotations", str(annotations), "--schema", str(schema), "--codebook", str(codebook)],
        ["--input", str(annotations), "--schema", str(schema), "--codebook", str(codebook)],
    ]
    last = None
    for tail in forms:
        cp = _run_validator(script, tail)
        last = (tail, cp)
        if cp.returncode == 0:
            return tail, cp
    assert last is not None
    tail, cp = last
    out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    raise AssertionError(
        "Validator did not succeed with any supported CLI form. "
        f"Last tried: {tail}\n--- output ---\n{out.strip()}\n--- end ---"
    )


def test_validator_smoke_valid_and_invalid(tmp_path: Path) -> None:
    root = _repo_root()
    outputs = root / "outputs"
    schema = outputs / "annotation_schema_v0.1.json"
    codebook = outputs / "task_taxonomy_codebook_v0.1.json"
    examples = outputs / "example_annotations_v0.1.jsonl"
    script = root / "src" / "validate_annotations.py"

    missing = [p for p in [schema, codebook, examples, script] if not p.exists()]
    assert not missing, "Missing required project files: " + ", ".join(str(p) for p in missing)

    used_tail, cp_ok = _try_cli_forms(script, schema, codebook, examples)
    assert cp_ok.returncode == 0, (cp_ok.stdout or "") + "\n" + (cp_ok.stderr or "")

    bad = tmp_path / "bad_example.jsonl"
    # Construct a clearly invalid line (violates basic schema/required-field rules).
    bad.write_text('{"id":"bad-001"}\n', encoding="utf-8")

    # Reuse the exact CLI shape that worked for the valid file, swapping the path.
    used_tail_bad = [str(bad) if a == str(examples) else a for a in used_tail]
    cp_bad = _run_validator(script, used_tail_bad)

    # We accept either non-zero exit OR an explicit ERROR marker in output, but at least one must happen.
    combined = ((cp_bad.stdout or "") + "\n" + (cp_bad.stderr or "")).strip()
    assert cp_bad.returncode != 0 or "ERROR" in combined.upper() or "INVALID" in combined.upper(), combined
