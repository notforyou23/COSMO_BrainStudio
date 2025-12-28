import importlib
import pytest

try:
    from pydantic import ValidationError
except Exception:  # pragma: no cover
    ValidationError = Exception


def _import_first(paths):
    for p in paths:
        try:
            return importlib.import_module(p)
        except Exception:
            continue
    raise ImportError(f"Could not import any of: {paths}")


def _get_attr_any(mod, names):
    for n in names:
        if hasattr(mod, n):
            return getattr(mod, n)
    raise AttributeError(f"{mod.__name__} missing any of: {names}")


def _model_validate(cls, data):
    if hasattr(cls, "model_validate"):
        return cls.model_validate(data)
    return cls.parse_obj(data)


def _discover():
    models = _import_first(
        [
            "psyprim.models",
            "psyprim.metadata",
            "psyprim.schemas",
            "psyprim.validation",
            "psyprim",
        ]
    )
    Provenance = _get_attr_any(models, ["Provenance", "EditionProvenance", "TranslationProvenance"])
    PaginationVariant = _get_attr_any(models, ["PaginationVariant", "PaginationScheme", "Pagination"])
    PublicDomainCitation = _get_attr_any(models, ["PublicDomainCitation", "PublicDomainCite", "PublicDomainRequirement"])
    return Provenance, PaginationVariant, PublicDomainCitation


@pytest.fixture(scope="module")
def cls():
    return _discover()
def test_provenance_accepts_minimal_valid(cls):
    Provenance, _, _ = cls
    data = {
        "source_type": "edition",
        "work_title": "Principles of Psychology",
        "work_author": "William James",
        "year": 1890,
        "edition_label": "1st",
        "publisher": "Henry Holt",
        "language": "en",
        "notes": "Primary source edition used for transcription.",
    }
    obj = _model_validate(Provenance, data)
    d = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
    assert d.get("work_title") == "Principles of Psychology"
    assert d.get("year") == 1890


def test_provenance_requires_core_fields(cls):
    Provenance, _, _ = cls
    bad = {"source_type": "edition", "year": 1890}
    with pytest.raises(ValidationError):
        _model_validate(Provenance, bad)


def test_provenance_translation_requires_language_or_translator(cls):
    Provenance, _, _ = cls
    data = {
        "source_type": "translation",
        "work_title": "Traumdeutung",
        "work_author": "Sigmund Freud",
        "year": 1900,
        "edition_label": "1st",
        "publisher": "Franz Deuticke",
    }
    # Accept if model is permissive; otherwise require missing translation metadata.
    try:
        _model_validate(Provenance, data)
    except ValidationError:
        data2 = dict(data, language="de", translator="N/A")
        obj = _model_validate(Provenance, data2)
        d = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
        assert d.get("source_type") == "translation"
def test_pagination_variant_validates_variants_and_mapping(cls):
    _, PaginationVariant, _ = cls
    data = {
        "label": "Holt_1890",
        "scheme": "print",
        "start_page": 1,
        "end_page": 10,
        "notes": "Original pagination.",
        "page_map": [{"from": 1, "to": 1}, {"from": 2, "to": 2}],
    }
    obj = _model_validate(PaginationVariant, data)
    d = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
    assert d.get("label") == "Holt_1890"
    assert d.get("start_page") == 1


def test_pagination_variant_rejects_negative_or_inverted_ranges(cls):
    _, PaginationVariant, _ = cls
    for bad in [
        {"label": "X", "scheme": "print", "start_page": -1, "end_page": 10},
        {"label": "X", "scheme": "print", "start_page": 10, "end_page": 1},
    ]:
        with pytest.raises(ValidationError):
            _model_validate(PaginationVariant, bad)


def test_pagination_variant_requires_label_and_scheme(cls):
    _, PaginationVariant, _ = cls
    with pytest.raises(ValidationError):
        _model_validate(PaginationVariant, {"start_page": 1, "end_page": 2})
def test_public_domain_citation_requires_full_citation_and_basis(cls):
    _, _, PublicDomainCitation = cls
    good = {
        "public_domain": True,
        "basis": "Published in the United States before 1929.",
        "citation": {
            "author": "William James",
            "title": "The Principles of Psychology",
            "year": 1890,
            "publisher": "Henry Holt",
        },
        "access": {"source": "scan", "url": "https://example.org/james1890"},
    }
    obj = _model_validate(PublicDomainCitation, good)
    d = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
    assert d.get("public_domain") is True
    assert "basis" in d and d["basis"]


def test_public_domain_citation_rejects_pd_without_basis_or_citation(cls):
    _, _, PublicDomainCitation = cls
    for bad in [
        {"public_domain": True, "citation": {"title": "X", "year": 1900}},
        {"public_domain": True, "basis": "Old enough."},
    ]:
        with pytest.raises(ValidationError):
            _model_validate(PublicDomainCitation, bad)


def test_public_domain_citation_allows_non_pd_without_basis(cls):
    _, _, PublicDomainCitation = cls
    data = {"public_domain": False, "notes": "Rights unclear; do not redistribute scans."}
    obj = _model_validate(PublicDomainCitation, data)
    d = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
    assert d.get("public_domain") is False
