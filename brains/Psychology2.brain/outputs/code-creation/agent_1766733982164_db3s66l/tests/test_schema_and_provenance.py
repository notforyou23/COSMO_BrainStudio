import re
import pytest

MODULE_CANDIDATES = (
    "psyprim",
    "psyprim.cli",
    "psyprim.schema",
    "psyprim.provenance",
    "psyprim.variant",
    "psyprim.citation",
)

def _import_attr(*names):
    last_err = None
    for mod_name in MODULE_CANDIDATES:
        try:
            mod = __import__(mod_name, fromlist=["*"])
        except Exception as e:
            last_err = e
            continue
        for n in names:
            if hasattr(mod, n):
                return getattr(mod, n)
    tried = ", ".join(MODULE_CANDIDATES)
    raise AssertionError(f"Expected one of {names} in modules: {tried}. Last import error: {last_err!r}")
def test_metadata_schema_validation_missing_required_fields_raises():
    validate = _import_attr("validate_metadata", "validate_metadata_schema", "validate_metadata_dict")
    with pytest.raises(Exception):
        validate({})

def test_metadata_schema_validation_accepts_reasonable_minimal_record():
    validate = _import_attr("validate_metadata", "validate_metadata_schema", "validate_metadata_dict")
    record = {
        "title": "A Study of Habit Formation",
        "creators": [{"name": "Smith, Jane"}],
        "date": "1932-01-01",
        "source_type": "primary_source",
        "repository": {"name": "Zenodo", "id": "12345", "url": "https://zenodo.org/record/12345"},
        "access_date": "2025-01-01",
        "file_sha256": "0" * 64,
        "notes": "Test fixture for schema validation.",
    }
    validate(record)
def test_provenance_flags_mutual_exclusion_rules():
    validate_flags = _import_attr(
        "validate_provenance_flags",
        "normalize_provenance_flags",
        "check_provenance_flags",
    )
    bad = {"primary_source": True, "secondary_source": True}
    with pytest.raises(Exception):
        validate_flags(bad)

def test_provenance_flags_allows_single_classification():
    validate_flags = _import_attr(
        "validate_provenance_flags",
        "normalize_provenance_flags",
        "check_provenance_flags",
    )
    ok = {"primary_source": True, "secondary_source": False}
    out = validate_flags(ok)
    assert out is None or isinstance(out, (dict, str))
def test_variant_numbering_is_deterministic_across_dict_order():
    variant_fn = _import_attr(
        "variant_number",
        "deterministic_variant_number",
        "variant_id",
        "compute_variant_id",
    )
    meta_a = {"title": "T", "date": "1900-01-01", "repository": {"name": "R", "id": "X"}}
    meta_b = {"repository": {"id": "X", "name": "R"}, "date": "1900-01-01", "title": "T"}
    content = "Same content; should yield same variant number."
    v1 = variant_fn(meta_a, content)
    v2 = variant_fn(meta_b, content)
    assert v1 == v2
    assert isinstance(v1, (int, str))
    if isinstance(v1, str):
        assert len(v1) > 0
def test_repository_citation_link_generation_is_url_like_and_contains_identifier():
    link_fn = _import_attr(
        "repository_citation_link",
        "make_repository_citation_link",
        "build_repository_link",
        "repository_link",
    )
    link = link_fn({"name": "Zenodo", "id": "12345"})
    assert isinstance(link, str) and link
    assert re.match(r"^https?://", link)
    assert "12345" in link

def test_repository_citation_link_generation_osf_style_identifier():
    link_fn = _import_attr(
        "repository_citation_link",
        "make_repository_citation_link",
        "build_repository_link",
        "repository_link",
    )
    link = link_fn({"name": "OSF", "id": "abcd1"})
    assert isinstance(link, str) and link
    assert re.match(r"^https?://", link)
    assert "abcd1" in link
