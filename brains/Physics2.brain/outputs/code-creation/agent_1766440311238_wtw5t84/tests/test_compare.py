import sys
from pathlib import Path

import pytest

# Make /src importable as a (namespace) package root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarks.compare import CompareSpec, compare
def test_abs_and_rel_tolerance_numbers():
    assert compare(1.0, 1.0009, CompareSpec(atol=1e-3)).ok
    assert not compare(1.0, 1.002, CompareSpec(atol=1e-3)).ok
    assert compare(100.0, 101.0, CompareSpec(rtol=0.02)).ok
    assert not compare(100.0, 103.0, CompareSpec(rtol=0.02)).ok
def test_per_field_override_by_full_path():
    a = {"a": 1.0, "b": 1.0}
    b = {"a": 1.2, "b": 1.2}
    spec = CompareSpec(atol=0.0, per_field={"$.b": CompareSpec(atol=0.25)})
    res = compare(a, b, spec)
    assert not res.ok
    assert [m.path for m in res.mismatches] == ["$.a"]
def test_nan_and_inf_policies_for_scalars():
    assert compare(float("nan"), float("nan")).ok
    assert not compare(float("nan"), float("nan"), CompareSpec(nan_equal=False)).ok

    assert compare(float("inf"), float("inf")).ok
    assert not compare(float("inf"), float("-inf")).ok
    assert not compare(float("inf"), float("inf"), CompareSpec(inf_equal=False)).ok
def test_shape_and_type_mismatches():
    np = pytest.importorskip("numpy")

    res = compare(np.zeros((2,)), np.zeros((2, 1)))
    assert not res.ok and res.mismatches[0].reason == "shape mismatch"

    res2 = compare({"x": 1}, {"x": "1"})
    assert not res2.ok
    m = res2.mismatches[0]
    assert (m.path, m.reason, m.a, m.b) == ("$.x", "type mismatch", "int", "str")
def test_deterministic_mismatch_paths_and_raise_message():
    a = {"b": 0, "a": 0}
    b = {"a": 1, "b": 2}
    res = compare(a, b, CompareSpec())
    assert [m.path for m in res.mismatches] == ["$.a", "$.b"]

    with pytest.raises(AssertionError) as ei:
        res.raise_on_mismatch(prefix="CI")
    msg = str(ei.value).splitlines()
    assert msg[0] == "CI:"
    assert msg[1].startswith("- $.a:")
    assert msg[2].startswith("- $.b:")
def test_numpy_array_element_mismatch_path_and_details():
    np = pytest.importorskip("numpy")
    res = compare(np.array([0.0, 1.0]), np.array([0.0, 2.0]), CompareSpec(atol=0.0, rtol=0.0))
    assert not res.ok
    assert res.mismatches[0].path == "$[1]"
    assert "diff=" in res.mismatches[0].details
