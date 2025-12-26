import re
import pytest

try:
    from src.intake import validate_task as vt  # type: ignore
except Exception as e:  # pragma: no cover
    vt = None
    _IMPORT_ERR = e
else:
    _IMPORT_ERR = None


def _call_validate(task: dict):
    if vt is None:  # pragma: no cover
        pytest.skip(f"validate_task module not importable yet: {_IMPORT_ERR!r}")
    fn = None
    for name in ("validate_task", "normalize_then_validate", "normalize_and_validate", "run"):
        fn = getattr(vt, name, None)
        if callable(fn):
            break
    if fn is None:  # pragma: no cover
        pytest.fail("No callable validation entrypoint found in src.intake.validate_task")

    try:
        out = fn(task)
    except Exception as e:
        return False, None, [str(e)]

    # Common shapes: dict, (normalized, errors), {"ok":..., "errors":..., "normalized":...}
    if isinstance(out, dict) and ("ok" in out or "errors" in out or "normalized" in out):
        ok = bool(out.get("ok", not out.get("errors")))
        normalized = out.get("normalized") or out.get("task") or out.get("normalized_task")
        errors = out.get("errors") or []
        return ok, normalized, _stringify_errors(errors)

    if isinstance(out, tuple) and len(out) == 2:
        normalized, errors = out
        ok = not errors
        return ok, normalized, _stringify_errors(errors)

    if isinstance(out, dict):
        return True, out, []

    return True, out, []


def _stringify_errors(errors):
    if errors is None:
        return []
    if isinstance(errors, str):
        return [errors]
    out = []
    for e in errors:
        if isinstance(e, str):
            out.append(e)
        elif isinstance(e, dict):
            out.append(json.dumps(e, sort_keys=True))
        else:
            out.append(str(e))
    return out


def _base_task():
    return {
        "verbatim_claim": "Example claim: X causes Y.",
        "source_context": {
            "who": "Example Speaker",
            "when": "2024-01-02",
            "where": "Example Venue",
            "url": "https://example.com/source",
        },
        "provenance_anchor": {
            "type": "url",
            "value": "https://example.com/source#claim",
        },
        "query": {},
    }
@pytest.mark.parametrize(
    "field, expected_kw",
    [
        ("verbatim_claim", "verbatim"),
        ("source_context", "source"),
        ("provenance_anchor", "provenance"),
    ],
)
def test_rejects_missing_required_primary_inputs(field, expected_kw):
    task = _base_task()
    task.pop(field, None)
    ok, normalized, errors = _call_validate(task)
    assert ok is False
    msg = " ".join(errors).lower()
    assert expected_kw in msg or field in msg


def test_doi_missing_requires_query_keywords_and_authors():
    task = _base_task()
    task["query"] = {
        "doi": None,
        # intentionally missing keywords/authors
    }
    ok, normalized, errors = _call_validate(task)
    assert ok is False
    msg = " ".join(errors).lower()
    assert ("keyword" in msg) or ("author" in msg) or ("query" in msg)


def test_doi_missing_defaults_date_range_2019_2025_when_query_sufficient():
    task = _base_task()
    task["query"] = {
        "doi": None,
        "keywords": ["example topic"],
        "authors": ["Example Author"],
        # date range omitted; should default
    }
    ok, normalized, errors = _call_validate(task)
    assert ok is True, f"Expected validation success, got errors: {errors}"
    assert isinstance(normalized, dict)
    q = normalized.get("query") or {}
    # Accept a few plausible representations of a 2019–2025 default range.
    y = json.dumps(q).lower()
    assert "2019" in y and "2025" in y
