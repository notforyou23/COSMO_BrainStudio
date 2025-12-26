"""Schema conformance tests for benchmark JSON outputs.

Validates all benchmark JSON files (expected and/or generated) against
outputs/schemas/benchmark_schema.json with helpful diagnostics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pytest

try:
    import jsonschema
except Exception as e:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]
    _jsonschema_import_error = e
from .conftest import expected_outputs_dir, iter_json_files, read_json


def _iter_benchmark_json_files(outputs_dir: Path) -> list[Path]:
    """Collect candidate benchmark JSON files, excluding schemas."""
    files: list[Path] = []
    expected_dir = expected_outputs_dir(outputs_dir)
    for root in {outputs_dir, expected_dir}:
        if not root.exists():
            continue
        for p in iter_json_files(root):
            # Exclude schema files and anything under outputs/schemas/
            if "schemas" in p.parts:
                continue
            files.append(p)
    # Unique, stable ordering by relative path
    seen: set[str] = set()
    out: list[Path] = []
    for p in sorted(files, key=lambda x: x.as_posix()):
        k = p.resolve().as_posix()
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def _format_validation_errors(errors: Iterable["jsonschema.ValidationError"], *, file_path: Path) -> str:
    lines = [f"Schema validation failed for: {file_path.as_posix()}"]
    for i, err in enumerate(errors, start=1):
        inst_path = "/" + "/".join(str(p) for p in err.path) if err.path else "<root>"
        schema_path = "/" + "/".join(str(p) for p in err.schema_path) if err.schema_path else "<schema>"
        lines.append(f"  [{i}] instance path: {inst_path}")
        lines.append(f"      schema path:   {schema_path}")
        lines.append(f"      message:       {err.message}")
    return "\n".join(lines)
@pytest.mark.skipif(jsonschema is None, reason="jsonschema is required for schema validation")
def test_benchmark_schema_exists_and_is_valid_json(benchmark_schema_path: Path) -> None:
    assert benchmark_schema_path.exists(), (
        "Missing benchmark schema at outputs/schemas/benchmark_schema.json; "
        "generate or commit it to enable schema validation."
    )
    schema = read_json(benchmark_schema_path)
    # Ensure the schema itself is valid (raises on error).
    jsonschema.Draft202012Validator.check_schema(schema)
@pytest.mark.skipif(jsonschema is None, reason="jsonschema is required for schema validation")
def test_all_benchmark_json_conform_to_schema(outputs_dir: Path, benchmark_schema_path: Path) -> None:
    if not benchmark_schema_path.exists():
        pytest.skip("Benchmark schema not present; skipping schema conformance checks.")

    schema = read_json(benchmark_schema_path)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)

    files = _iter_benchmark_json_files(outputs_dir)
    if not files:
        pytest.skip("No benchmark JSON files found under outputs/ (or outputs/expected).")

    failures: list[str] = []
    for path in files:
        instance = read_json(path)
        errors = sorted(validator.iter_errors(instance), key=lambda e: (list(e.path), e.message))
        if errors:
            failures.append(_format_validation_errors(errors, file_path=path))

    assert not failures, "\n\n".join(failures)
