import re
import pytest

def _load_api():
    candidates = [
        ("psyprim.detectors", ("extract_identifiers", "detect_primary_source_features")),
        ("psyprim.detection", ("extract_identifiers", "detect_primary_source_features")),
        ("psyprim", ("extract_identifiers", "detect_primary_source_features")),
        ("psyprim.detectors", ("extract_identifiers", "detect_features")),
        ("psyprim.detection", ("extract_identifiers", "detect_features")),
        ("psyprim", ("extract_identifiers", "detect_features")),
    ]
    last_err = None
    for modname, fnames in candidates:
        try:
            mod = __import__(modname, fromlist=["*"])
            f1 = getattr(mod, fnames[0], None)
            f2 = getattr(mod, fnames[1], None)
            if callable(f1) and callable(f2):
                return f1, f2
        except Exception as e:
            last_err = e
            continue
    raise ImportError(f"Could not import detector APIs; last error: {last_err!r}")

extract_identifiers, detect_features = _load_api()

def _as_set(x):
    if x is None:
        return set()
    if isinstance(x, (set, tuple, list)):
        return set(x)
    return {x}
@pytest.mark.parametrize(
    "text,expected_doi",
    [
        ("Smith (2019). https://doi.org/10.1037/amp0000123.", "10.1037/amp0000123"),
        ("DOI:10.1000/182; accessed 2020-01-01", "10.1000/182"),
        ("doi: 10.1111/J.1365-2648.2008.04983.x", "10.1111/J.1365-2648.2008.04983.x"),
        ("(doi:10.1037/0003-066X.59.1.29)", "10.1037/0003-066X.59.1.29"),
    ],
)
def test_extract_doi_variants(text, expected_doi):
    ids = extract_identifiers(text)
    dois = _as_set(ids.get("doi") if isinstance(ids, dict) else getattr(ids, "doi", None))
    assert expected_doi in dois

@pytest.mark.parametrize(
    "text",
    [
        "The words 'do i' appear here but no identifier.",
        "A DOI-like token 10.123/abc is too short.",
        "Ratio 10.100/200 is not a DOI in this context.",
    ],
)
def test_extract_doi_avoids_common_false_positives(text):
    ids = extract_identifiers(text)
    dois = _as_set(ids.get("doi") if isinstance(ids, dict) else getattr(ids, "doi", None))
    for d in dois:
        assert re.search(r"^10\.\d{4,9}/\S+$", d)
@pytest.mark.parametrize(
    "text,expected_isbn",
    [
        ("ISBN 978-0-13-110362-7", "9780131103627"),
        ("isbn: 0-306-40615-2", "0306406152"),
        ("(ISBN-10: 0306406152)", "0306406152"),
    ],
)
def test_extract_isbn_normalization(text, expected_isbn):
    ids = extract_identifiers(text)
    isbns = _as_set(ids.get("isbn") if isinstance(ids, dict) else getattr(ids, "isbn", None))
    assert expected_isbn in {re.sub(r"[^0-9Xx]", "", i).upper() for i in isbns}

@pytest.mark.parametrize(
    "text,expected",
    [
        ("OCLC: 12345678", "12345678"),
        ("WorldCat (OCoLC)ocm12345678", "12345678"),
        ("OCoLC 987654321", "987654321"),
    ],
)
def test_extract_oclc(text, expected):
    ids = extract_identifiers(text)
    oclc = _as_set(ids.get("oclc") if isinstance(ids, dict) else getattr(ids, "oclc", None))
    assert any(expected == re.sub(r"\D", "", x) for x in oclc)

def test_extract_repository_urls_and_handles():
    text = "Available at https://hdl.handle.net/2027/uc1.b123456 and https://archive.org/details/sometitle"
    ids = extract_identifiers(text)
    urls = _as_set(ids.get("url") if isinstance(ids, dict) else getattr(ids, "url", None))
    handles = _as_set(ids.get("handle") if isinstance(ids, dict) else getattr(ids, "handle", None))
    assert any("archive.org" in u for u in urls)
    assert any("hdl.handle.net" in u for u in urls)
    assert any("2027/uc1.b123456" in h for h in handles)
def test_detect_edition_and_translation_provenance():
    text = (
        "Freud, S. (1900/1953). The Interpretation of Dreams (J. Strachey, Trans.; 2nd ed.). "
        "London: Hogarth Press."
    )
    feats = detect_features(text)
    assert isinstance(feats, dict)
    assert feats.get("edition_provenance") or feats.get("has_edition") is True
    assert feats.get("translation_provenance") or feats.get("has_translation") is True

def test_detect_variant_pagination_roman_and_arabic():
    text = "Kant (1781). Critique of Pure Reason, pp. xiii–xv, 1–23."
    feats = detect_features(text)
    assert feats.get("variant_pagination") or feats.get("has_variant_pagination") is True

def test_detect_repository_citation_archive_call_number():
    text = (
        "Archives of the History of American Psychology (AHAP), University of Akron, "
        "Collection: Boring Papers, Box 3, Folder 2, call no. MSS-001."
    )
    feats = detect_features(text)
    assert feats.get("repository_citation") or feats.get("has_repository_citation") is True
    repos = feats.get("repositories") or feats.get("repository_names") or []
    repos = [r.lower() for r in (repos if isinstance(repos, (list, tuple, set)) else [repos])]
    assert any("akron" in r or "ahap" in r for r in repos)

@pytest.mark.parametrize(
    "text,expected_flag",
    [
        ("1st ed.; rev. ed.; 3rd edition.", "edition_provenance"),
        ("Translated by James Strachey; trans. by J. S.", "translation_provenance"),
        ("British ed.; American edition; Leipzig: 1890.", "edition_provenance"),
        ("p. xvi; pp. 1-10; fol. 12r.", "variant_pagination"),
        ("MS. 123, Box 1, Folder 4, Library of Congress.", "repository_citation"),
        ("Wellcome Collection, MS.1234; Beinecke Library, GEN MSS 123.", "repository_citation"),
    ],
)
def test_detect_feature_heuristics_cover_common_patterns(text, expected_flag):
    feats = detect_features(text)
    alt = {
        "edition_provenance": "has_edition",
        "translation_provenance": "has_translation",
        "variant_pagination": "has_variant_pagination",
        "repository_citation": "has_repository_citation",
    }
    assert feats.get(expected_flag) is True or feats.get(alt.get(expected_flag, "")) is True
