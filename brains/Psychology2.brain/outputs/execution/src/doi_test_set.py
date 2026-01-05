"""
Small, fixed DOI test set used by the end-to-end DOI pipeline run.

Design goals:
- Cover Crossref and DataCite-like DOIs that should resolve in normal conditions.
- Include normalization edge cases (case, URL prefix, whitespace).
- Include explicit negative cases (malformed DOI, syntactically valid but unregistered).
- Provide provenance/notes and expected resolvability for per-DOI reporting.
"""

from __future__ import annotations

from typing import Any, Dict, List

DOI_TEST_SET_VERSION: str = "v1"
DOI_TEST_SET_NAME: str = "small_fixed_doi_set"
DOI_TEST_SET: List[Dict[str, Any]] = [
    {
        "id": "crossref_classic_watson_crick_1953",
        "input": "10.1038/171737a0",
        "expected_resolvable": True,
        "expected_primary_provider": "crossref",
        "provenance": "Widely cited Nature article DOI; commonly resolvable via Crossref.",
        "notes": "Canonical Crossref DOI; stable long-term.",
    },
    {
        "id": "crossref_pmid_style_example_1997",
        "input": "10.1126/science.275.5305.1320",
        "expected_resolvable": True,
        "expected_primary_provider": "crossref",
        "provenance": "Science journal DOI; commonly used in API examples.",
        "notes": "Good for title/author metadata extraction.",
    },
    {
        "id": "crossref_normalization_uppercase",
        "input": "10.1145/2783446.2783605",
        "expected_resolvable": True,
        "expected_primary_provider": "crossref",
        "provenance": "ACM DOI; tests normal path resolution.",
        "notes": "Ensure pipeline preserves DOI semantics and lowercases normalized form.",
    },
    {
        "id": "crossref_normalization_url_prefix",
        "input": "https://doi.org/10.1109/5.771073",
        "expected_resolvable": True,
        "expected_primary_provider": "crossref",
        "provenance": "IEEE DOI; tests stripping doi.org prefix.",
        "notes": "Input is a URL; pipeline should normalize to DOI.",
    },
    {
        "id": "crossref_normalization_whitespace",
        "input": "  10.1007/978-3-319-24544-4_1  ",
        "expected_resolvable": True,
        "expected_primary_provider": "crossref",
        "provenance": "Springer book chapter DOI; tests trimming whitespace.",
        "notes": "Input has leading/trailing spaces.",
    },
    {
        "id": "datacite_zenodo_software_example",
        "input": "10.5281/zenodo.3248877",
        "expected_resolvable": True,
        "expected_primary_provider": "datacite",
        "provenance": "Zenodo DOIs are registered via DataCite; common in research software/data.",
        "notes": "Should exercise DataCite JSON metadata path.",
    },
    {
        "id": "datacite_figshare_like_example",
        "input": "10.6084/m9.figshare.9782777",
        "expected_resolvable": True,
        "expected_primary_provider": "datacite",
        "provenance": "Figshare-style DOI prefix often registered with DataCite.",
        "notes": "Useful to test creator/title/publisher fields.",
    },
    {
        "id": "negative_syntactically_valid_but_unregistered",
        "input": "10.5555/12345678",
        "expected_resolvable": False,
        "expected_primary_provider": None,
        "provenance": "Commonly used as a placeholder DOI in documentation; should not resolve.",
        "notes": "Expect provider 404/NotFound mapping to explicit failure reason.",
    },
    {
        "id": "negative_malformed_missing_prefix",
        "input": "11.1038/171737a0",
        "expected_resolvable": False,
        "expected_primary_provider": None,
        "provenance": "Intentionally malformed (nonexistent prefix pattern).",
        "notes": "Should fail validation/normalization before provider calls.",
    },
    {
        "id": "negative_not_a_doi",
        "input": "not-a-doi",
        "expected_resolvable": False,
        "expected_primary_provider": None,
        "provenance": "Intentionally invalid string.",
        "notes": "Should trigger invalid format with clear reason.",
    },
]


def get_doi_test_set() -> List[Dict[str, Any]]:
    """Return a shallow copy of the fixed DOI test set."""
    return list(DOI_TEST_SET)
