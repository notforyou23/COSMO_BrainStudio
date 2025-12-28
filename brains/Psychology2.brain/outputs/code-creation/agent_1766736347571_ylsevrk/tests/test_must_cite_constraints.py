import importlib
import pytest


def _load():
    return importlib.import_module("borderline_qa.citations")


def _as_sources():
    text = (
        "Small, low-cost tweaks to choice architecture—like setting defaults, reordering options, "
        "adjusting framing, and increasing salience—can meaningfully change behavior."
    )
    src = {
        "id": "s1",
        "text": text,
        "url": "https://example.org/paper",
        "doi": "10.1000/xyz123",
        "title": "Choice architecture",
    }
    return text, [src], {"s1": src}


def _run_validate(answer, cites, sources):
    c = _load()
    src_list, src_map = sources

    def try_call(fn):
        # Common signatures seen in validators; treat exceptions as "invalid" results.
        for args in (
            (answer, cites, src_list),
            (answer, cites, src_map),
            (cites, answer, src_list),
            (cites, answer, src_map),
            (answer, src_list, cites),
            (answer, src_map, cites),
        ):
            try:
                return fn(*args)
            except TypeError:
                continue
        return None

    for name in ("validate_must_cite", "validate_citations", "validate", "validate_constraints"):
        fn = getattr(c, name, None)
        if callable(fn):
            out = try_call(fn)
            if out is not None:
                return out

    vcls = getattr(c, "MustCiteValidator", None) or getattr(c, "MustCiteConstraints", None)
    if vcls is not None:
        for init_arg in (src_list, src_map, {"sources": src_list}, {"sources": src_map}, None):
            try:
                v = vcls() if init_arg is None else vcls(init_arg)
            except TypeError:
                continue
            for mname in ("validate", "check", "__call__"):
                m = getattr(v, mname, None)
                if callable(m):
                    for args in ((answer, cites), (cites, answer), (answer, cites, src_list), (answer, cites, src_map)):
                        try:
                            return m(*args)
                        except TypeError:
                            continue
    raise AssertionError("No supported must-cite validator API found in borderline_qa.citations")


def _is_valid_result(res):
    if res is None:
        return False
    if isinstance(res, bool):
        return res
    if isinstance(res, (list, tuple, set)):
        return len(res) == 0
    if isinstance(res, dict):
        for k in ("errors", "violations", "problems"):
            if k in res and isinstance(res[k], (list, tuple)):
                return len(res[k]) == 0
        for k in ("ok", "valid", "passed"):
            if k in res and isinstance(res[k], bool):
                return res[k]
        # Unknown dict shape: be conservative.
        return False
    return False


def assert_valid(answer, cites, sources):
    try:
        res = _run_validate(answer, cites, sources)
    except Exception as e:
        raise AssertionError(f"Expected valid but got exception: {e!r}") from e
    assert _is_valid_result(res), f"Expected valid but got: {res!r}"


def assert_invalid(answer, cites, sources):
    try:
        res = _run_validate(answer, cites, sources)
    except Exception:
        return
    assert not _is_valid_result(res), f"Expected invalid but got: {res!r}"


def test_requires_url_or_doi_present():
    text, src_list, src_map = _as_sources()
    answer = "Small, low-cost tweaks to choice architecture can change behavior."
    cites = [{"quote": "Small, low-cost tweaks to choice architecture", "source_id": "s1", "url": None, "doi": None, "answer_span": [0, 43]}]
    assert_invalid(answer, cites, (src_list, src_map))


def test_quote_must_match_source_text():
    text, src_list, src_map = _as_sources()
    answer = "Defaults and framing can change behavior."
    cites = [{"quote": "This quote does not occur in the source", "source_id": "s1", "url": "https://example.org/paper", "answer_span": [0, 10]}]
    assert_invalid(answer, cites, (src_list, src_map))


def test_normalized_quote_matching_accepts_whitespace_and_dash_variants():
    text, src_list, src_map = _as_sources()
    answer = "Small, low-cost tweaks to choice architecture like setting defaults can change behavior."
    # Use plain hyphen and different spacing vs. em dash in source.
    q = "Small, low-cost tweaks to choice architecture-like setting defaults"
    cites = [{"quote": q, "source_id": "s1", "url": "https://example.org/paper", "answer_span": [0, len(q)]}]
    # If the implementation does not normalize, this will fail and expose the edge case.
    assert_valid(answer, cites, (src_list, src_map))


def test_answer_span_out_of_bounds_rejected():
    text, src_list, src_map = _as_sources()
    answer = "Defaults matter."
    cites = [{"quote": "Defaults", "source_id": "s1", "url": "https://example.org/paper", "answer_span": [0, 999]}]
    assert_invalid(answer, cites, (src_list, src_map))


def test_answer_span_must_map_to_quote_text():
    text, src_list, src_map = _as_sources()
    answer = "Defaults matter."
    # span points to "Defaults" but quote mismatches; should be rejected by span->quote consistency check.
    cites = [{"quote": "Framing", "source_id": "s1", "url": "https://example.org/paper", "answer_span": [0, 8]}]
    assert_invalid(answer, cites, (src_list, src_map))
