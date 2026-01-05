import json
import importlib
from pathlib import Path

import pytest


def _write_demo_dataset(root: Path):
    root.mkdir(parents=True, exist_ok=True)

    # Intentionally inconsistent dataset:
    # - CSV: duplicate EffectID (same StudyID/EffectID repeated)
    # - JSONL: mismatched StudyID for same EffectID
    # - prereg template: missing EffectID field
    csv_path = root / "effects.csv"
    csv_path.write_text(
        "StudyID,EffectID,Estimate\n"
        "S0001,E0001,0.10\n"
        "S0001,E0001,0.20\n",
        encoding="utf-8",
    )

    jsonl_path = root / "effects.jsonl"
    jsonl_path.write_text(
        json.dumps({"StudyID": "S0002", "EffectID": "E0001", "Estimate": 0.30}) + "\n",
        encoding="utf-8",
    )

    prereg_path = root / "prereg_template.md"
    prereg_path.write_text(
        "# Preregistration\n\n"
        "StudyID: S0001\n"
        "EffectID: \n",
        encoding="utf-8",
    )

    return csv_path, jsonl_path, prereg_path


def _find_checker_callable(mod):
    for name in (
        "check_ids",
        "check",
        "run",
        "run_check",
        "check_files",
        "check_paths",
        "main_check",
    ):
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    raise AssertionError("No checker entrypoint found in src.ids.checker")


def _run_checker(csv_path: Path, jsonl_path: Path, prereg_path: Path):
    mod = importlib.import_module("src.ids.checker")
    fn = _find_checker_callable(mod)

    # Try common signatures; fall back to kwargs.
    try:
        return fn(csv_path, jsonl_path, prereg_path)
    except TypeError:
        pass
    try:
        return fn([csv_path, jsonl_path, prereg_path])
    except TypeError:
        pass
    try:
        return fn(csv=csv_path, jsonl=jsonl_path, prereg=prereg_path)
    except TypeError:
        pass
    try:
        return fn(
            csv_paths=[csv_path],
            jsonl_paths=[jsonl_path],
            prereg_paths=[prereg_path],
        )
    except TypeError as e:
        raise AssertionError(f"Checker callable signature not supported: {e}") from e


def _iter_issue_like(obj):
    if obj is None:
        return []
    if isinstance(obj, dict):
        if "issues" in obj and isinstance(obj["issues"], list):
            return obj["issues"]
        if "errors" in obj and isinstance(obj["errors"], list):
            return obj["errors"]
        return [obj]
    if isinstance(obj, list):
        return obj
    for attr in ("issues", "errors", "problem_list", "problems"):
        v = getattr(obj, attr, None)
        if isinstance(v, list):
            return v
    return []


def _issue_texts(result):
    texts = []
    for issue in _iter_issue_like(result):
        if isinstance(issue, str):
            texts.append(issue)
        elif isinstance(issue, dict):
            texts.append(
                " ".join(
                    str(issue.get(k, ""))
                    for k in ("type", "code", "message", "detail", "path")
                ).strip()
            )
        else:
            texts.append(str(issue))
    if not texts:
        for attr in ("text", "summary", "report", "message"):
            v = getattr(result, attr, None)
            if isinstance(v, str) and v.strip():
                texts.append(v.strip())
    return [t for t in texts if t]


def _has_any(texts, *needles):
    s = " ".join(texts).lower()
    return all(n.lower() in s for n in needles)


def test_id_checker_demo_detects_missing_duplicate_mismatch(tmp_path: Path):
    csv_path, jsonl_path, prereg_path = _write_demo_dataset(tmp_path / "demo_ids")
    result = _run_checker(csv_path, jsonl_path, prereg_path)

    texts = _issue_texts(result)
    assert texts, "Expected checker to report issues for the intentionally-bad demo dataset"

    # Expected failure behavior (intentionally triggered by demo dataset):
    assert _has_any(texts, "duplicate"), f"Expected duplicate ID error, got: {texts}"
    assert _has_any(texts, "missing"), f"Expected missing ID error, got: {texts}"
    assert _has_any(texts, "mismatch") or _has_any(texts, "mismatched"), (
        f"Expected mismatched ID error, got: {texts}"
    )
