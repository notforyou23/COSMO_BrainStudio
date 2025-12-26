from __future__ import annotations

import math

import pytest

from src import diff as d
@pytest.mark.parametrize(
    "a,b,abs_tol,rel_tol,expected_ok",
    [
        (1.0, 1.0, 0.0, 0.0, True),
        (1.0, 1.000000001, 1e-8, 0.0, True),  # abs tol
        (1000.0, 1000.001, 0.0, 2e-6, True),  # rel tol (1e-6 would fail)
        (1.0, 1.1, 0.05, 0.0, False),
        (0.0, 1e-9, 1e-10, 0.0, False),
    ],
)
def test_numeric_close_abs_or_rel(a, b, abs_tol, rel_tol, expected_ok):
    ok, abs_err, rel_err = d.numeric_close(a, b, abs_tol=abs_tol, rel_tol=rel_tol)
    assert ok is expected_ok
    assert abs_err >= 0.0
    assert rel_err >= 0.0
def test_numeric_close_nans_and_infs():
    ok, *_ = d.numeric_close(float("nan"), float("nan"))
    assert ok is True

    ok, *_ = d.numeric_close(float("nan"), 0.0)
    assert ok is False

    ok, *_ = d.numeric_close(float("inf"), float("inf"))
    assert ok is True

    ok, *_ = d.numeric_close(float("inf"), float("-inf"))
    assert ok is False
def test_diff_numeric_updates_stats_and_examples_are_deterministic():
    expected = {"a": 1.0, "b": [1.0, 2.0]}
    actual = {"b": [1.0, 2.2], "a": 1.2}  # key order reversed on purpose

    stats = d.diff(expected, actual, abs_tol=0.0, rel_tol=0.0, max_examples=5)

    assert stats.ok is False
    assert stats.mismatches == 2
    assert stats.max_abs_err == pytest.approx(0.2)
    assert stats.max_rel_err > 0.0

    # Deterministic ordering: keys are traversed sorted by str(k).
    assert stats.examples[0].startswith("$.a:")
    assert stats.examples[1].startswith("$.b[1]:")
def test_diff_reports_missing_and_extra_keys():
    stats = d.diff({"a": 1, "b": 2}, {"b": 2, "c": 3})
    assert stats.ok is False
    assert stats.mismatches == 2
    assert any("missing key" in e for e in stats.examples)
    assert any("unexpected key" in e for e in stats.examples)
def test_diff_length_mismatch_counts_once_and_diffs_over_overlap():
    stats = d.diff([1.0, 2.0], [1.0, 3.0, 4.0], abs_tol=0.0, rel_tol=0.0)
    assert stats.ok is False
    # one for length mismatch + one for numeric mismatch at index 1
    assert stats.mismatches == 2
    assert any("length mismatch" in e for e in stats.examples)
    assert any("$[1]:" in e for e in stats.examples)
def test_format_summary_ok_and_fail_are_stable():
    ok_stats = d.diff({"x": 1.0}, {"x": 1.0})
    s = d.format_summary(ok_stats)
    assert s.startswith("OK (mismatches=0")

    fail_stats = d.diff({"x": 1.0}, {"x": 2.0}, abs_tol=0.0, rel_tol=0.0, max_examples=1)
    s2 = d.format_summary(fail_stats)
    assert s2.startswith("FAIL (mismatches=1")
    assert "\n- $.x:" in s2
