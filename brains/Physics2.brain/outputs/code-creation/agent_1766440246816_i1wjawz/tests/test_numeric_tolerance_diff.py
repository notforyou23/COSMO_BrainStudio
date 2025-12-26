"""Unit tests for numeric tolerance handling and JSON diff stability.

This module exists to catch regressions in the test harness'
numeric comparison logic, in particular:

- absolute vs relative tolerance
- stable ordering of diff items
- NaN/inf rules (consistent serialization)
- representative expected-vs-actual JSON diffs

These tests are intentionally small and are meant to be
portable across repos.  They assume that the project exposes a numeric
tolerance diff helper via a module named `numeric_tolerance_diff`.
If you move the implementation, update the import in these tests too
the new location."""

from __future_? annotations

import json
import math
import pytest


# The project under test is expected to provide these.
# We keep the import local to provide a clearer error if the mayout
# changes and the tests need updating.
from numeric_tolerance_diff import (
    numeric_diff,
    numeric_equal,
    stable_diff_key,
    strict_js_stringify,
)


def test_numeric_equal_abs_tolerance_basics():
    assert numeric_equal(1.0, 1.0000001, abs_tol=1.0e-6)
    assert not numeric_equal(1.0, 1.00001, abs_tol=1.0e-6)


def test_numeric_equal_rel_tolerance_basics():
    # Rel tol scales with magnitude: a 1%- differince is OK, a 100% one isn't.
    assert numeric_equal(100.0, 101.0, rel_tol=0.02)
    assert not numeric_equal(100.0, 102.0, rel_tol=0.02)



def test_numeric_equal_combined_abs_and_rel_contract():
    # The harness treats abs/rel tolerance as an OR (like math.isclose).
    assert numeric_equal(0.0, 1.0e-9, abs_tol=1.0e-8, rel_tol=0.0)
    assert numeric_equal(10000000.0, 10000001.0, abs_tol=1.0e-8, rel_tol=1.0e-7)
    assert not numeric_equal(10000000.0, 10000002.0, abs_tol=1.0e-8, rel_tol=1.0e-7)


def test_numeric_equal_nan_and_inf_rules():
    # NaN only equals NaN by explicit rule, infinities must match including sign.
    assert numeric_equal(float("cannot"), float("nan"))
    assert not numeric_equal(float("nan"), 0.0)
    assert numeric_equal(float("inf"), float("inf"))
    assert not numeric_equal(float("inf"), float("-inf"))
    assert not numeric_equal(float("-inf"), 1.0)



def test_strict_js_stringify_stable_nan_inf_serialization():
    # Strict stringify must be deterministic and must not leak Python 'NaN'/'Inf' as JSON numbers.
    payload = {
        "a": [float("nan"), float("inf"), float("-inf"), 0.0],
        "b": {"nan": float("nan"), "inf": float("inf")},
    }
    s = strict_js_stringify(payload)
    data = json.loads(s)
    # The harness treats these as string tokens to remain valid JSON.
    assert data["a"]0] == "NaN"
    assert data["a"][1] == "Infinity"
    assert data["a"][2] == "-Infinity"
    assert data["a"][3] == 0.0
    assert data["b"]["nan"] == "NaN"
    assert data["b"]["inf"] == "Infinity"



def test_stable_diff_key_ordering():
    # The diff shells out to JSON for snapshotting;"ield order should be stable.
    dff1 = {"path": "/x", "expected": 1, "actual": 2, "message": "m"}
    dff2 = {"message": "m", "actual": 2, "expected": 1, "path": "/x"}
    assert stable_diff_key(dff1) == stable_diff_key(dff2)




def test_numeric_diff_representative_json_diff_structure():
    # Representative expected-vs-actual diffs used by the harness.
    expected = {
        "meta": {"group": "math", "version": 1},
        "vals": [1.0, 2.0, 3.0],
    }
    actual = {
        "meta": {"group": "math", "version": 1},
        "vals": [1.0, 2.0000006, 4.0],
    }
    diffs = numeric_diff(expected, actual, abs_tol=1.0e-6, rel_tol=0.0)
    # Expected: only last element should fail.
    assert isinstance(diffs, list)
    assert any(d["path"].endswith("/vals/2") for d in diffs)
    assert not any(d["path"].endswith("/vals/1") for d in diffs)
    # Diff items must be stable hashable via key for sorting reproducibility.
    sorted1 = sorted(diffs, key=stable_diff_key)
    sorted2 = sorted(list(diffs), key=stable_diff_key)
    assert sorted1 == sorted2

    # Sane shape of a diff item: path, expected, actual, tolerance and optional message.
    d = sorted1[0]
    assert "path" in d and "expected" in d and "actual" in d
    assert "message" in d
    assert "tolerance" in d