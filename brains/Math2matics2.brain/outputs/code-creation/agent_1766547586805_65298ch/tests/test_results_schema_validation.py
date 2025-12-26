import copy
import pytest


def _import_results_schema():
    try:
        from src import results_schema as rs
    except Exception as e:  # pragma: no cover
        pytest.fail(f"Failed to import src.results_schema: {e}")
    return rs


def _call_validate(rs, payload):
    if hasattr(rs, "validate_results_payload"):
        return rs.validate_results_payload(payload)
    if hasattr(rs, "validate_results"):
        return rs.validate_results(payload)
    pytest.fail("results_schema must expose validate_results_payload(...) or validate_results(...)")


def _call_build(rs, **kwargs):
    if hasattr(rs, "build_results_payload"):
        return rs.build_results_payload(**kwargs)
    if hasattr(rs, "build_results_json"):
        return rs.build_results_json(**kwargs)
    pytest.fail("results_schema must expose build_results_payload(...) or build_results_json(...)")


def _schema_version_constant(rs):
    for name in ("RESULTS_SCHEMA_VERSION", "SCHEMA_VERSION", "RESULTS_VERSION"):
        if hasattr(rs, name):
            return getattr(rs, name)
    pytest.fail("results_schema must define RESULTS_SCHEMA_VERSION (or SCHEMA_VERSION/RESULTS_VERSION)")


def test_build_payload_emits_v1_schema_version_and_validates():
    rs = _import_results_schema()
    v = _schema_version_constant(rs)
    assert v == 1, f"Expected v1 schema version constant to be 1, got {v!r}"

    payload = _call_build(
        rs,
        metrics={"example_metric": 1.0},
        artifacts=[],
        figures=[],
        run_metadata={"seed": 123, "notes": "test"},
    )
    assert isinstance(payload, dict)
    assert payload.get("schema_version") == 1

    out = _call_validate(rs, payload)
    if out is not None:
        assert isinstance(out, dict)
        assert out.get("schema_version") == 1


def test_validation_rejects_missing_schema_version():
    rs = _import_results_schema()
    payload = _call_build(
        rs,
        metrics={"m": 1.0},
        artifacts=[],
        figures=[],
        run_metadata={"seed": 0},
    )
    bad = copy.deepcopy(payload)
    bad.pop("schema_version", None)
    with pytest.raises(Exception):
        _call_validate(rs, bad)


def test_validation_rejects_incorrect_schema_version_value():
    rs = _import_results_schema()
    payload = _call_build(
        rs,
        metrics={"m": 1.0},
        artifacts=[],
        figures=[],
        run_metadata={"seed": 0},
    )
    bad = copy.deepcopy(payload)
    bad["schema_version"] = 2
    with pytest.raises(Exception):
        _call_validate(rs, bad)


def test_validation_rejects_incorrect_field_types_for_known_top_level_fields():
    rs = _import_results_schema()
    payload = _call_build(
        rs,
        metrics={"m": 1.0},
        artifacts=[],
        figures=[],
        run_metadata={"seed": 0},
    )

    # metrics should be a dict
    if "metrics" in payload:
        bad = copy.deepcopy(payload)
        bad["metrics"] = ["not", "a", "dict"]
        with pytest.raises(Exception):
            _call_validate(rs, bad)

    # artifacts should be a list
    if "artifacts" in payload:
        bad = copy.deepcopy(payload)
        bad["artifacts"] = {"not": "a list"}
        with pytest.raises(Exception):
            _call_validate(rs, bad)

    # figures should be a list
    if "figures" in payload:
        bad = copy.deepcopy(payload)
        bad["figures"] = {"not": "a list"}
        with pytest.raises(Exception):
            _call_validate(rs, bad)


def test_schema_available_and_declares_schema_version_required_for_v1():
    rs = _import_results_schema()
    schema = None
    for name in ("RESULTS_SCHEMA_V1", "SCHEMA_V1", "RESULTS_JSON_SCHEMA_V1"):
        if hasattr(rs, name):
            schema = getattr(rs, name)
            break
    if schema is None and hasattr(rs, "get_results_schema"):
        schema = rs.get_results_schema(1)
    if schema is None and hasattr(rs, "get_schema"):
        schema = rs.get_schema(1)

    if schema is None:
        pytest.skip("No public v1 JSON schema object exposed; runtime validation tested elsewhere.")
    assert isinstance(schema, dict)
    assert schema.get("type") == "object"
    req = set(schema.get("required", []))
    assert "schema_version" in req
