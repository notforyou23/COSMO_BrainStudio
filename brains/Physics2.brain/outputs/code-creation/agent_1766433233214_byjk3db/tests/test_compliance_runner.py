import pytest

from cosmo_contracts.runner import run_compliance, run_contract


def _contract(
    bid="BM000",
    *,
    expected=None,
    invariants=None,
    tolerance=None,
    args=None,
    kwargs=None,
):
    return {
        "id": bid,
        "metadata": {"name": bid, "version": "0.1"},
        "reference": {"algorithm": "return expected"},
        "invariants": invariants or {},
        "tolerance": tolerance or {"policy": "exact"},
        "test_vector": {"args": args or [], "kwargs": kwargs or {}, "expected": expected},
    }
def test_run_contract_passes_exact_match():
    c = _contract("BM001", expected={"x": 1, "y": [2, 3]}, invariants={"dict_keys": ["x", "y"]})

    def impl():
        return {"x": 1, "y": [2, 3]}

    res = run_contract(c, impl)
    assert res.passed is True
    assert res.diagnostics == []
def test_run_contract_reports_mismatch_with_stable_diagnostics():
    c = _contract("BM002", expected=[1, 2, 3])

    def impl():
        return [1, 999, 3]

    res = run_contract(c, impl)
    assert res.passed is False
    assert res.diagnostics and res.diagnostics[-1].startswith("mismatch:idx=1:")
    assert res.expected == [1, 2, 3]
    assert res.actual == [1, 999, 3]
@pytest.mark.parametrize(
    "tol,actual,passed,diag_prefix",
    [
        ({"policy": "approx", "atol": 1e-3, "rtol": 0.0}, 1.0009, True, None),
        ({"policy": "approx", "atol": 1e-6, "rtol": 0.0}, 1.0009, False, "mismatch:abs_diff="),
    ],
)
def test_tolerance_policy_approx_controls_pass_fail(tol, actual, passed, diag_prefix):
    c = _contract("BM003", expected=1.0, tolerance=tol)

    def impl():
        return actual

    res = run_contract(c, impl)
    assert res.passed is passed
    if diag_prefix:
        assert any(d.startswith(diag_prefix) for d in res.diagnostics)
def test_invariant_failures_cause_failure_even_when_values_match():
    c = _contract(
        "BM004",
        expected={"a": 1},
        invariants={"output_type": "list", "dict_keys": ["a"]},
    )

    def impl():
        return {"a": 1}

    res = run_contract(c, impl)
    assert res.passed is False
    # output_type fails (dict != list) and dict_keys is OK
    assert "invariant_output_type_failed: got=dict" in res.diagnostics
    assert not any(d.startswith("mismatch:") for d in res.diagnostics)
def test_run_compliance_marks_missing_implementation_and_includes_failure_payload():
    c1 = _contract("BM005", expected=5)
    c2 = _contract("BM006", expected=6)

    def impl6():
        return 0

    report = run_compliance([c1, c2], {"BM006": impl6})
    assert report["BM005"]["passed"] is False
    assert report["BM005"]["diagnostics"] == ["missing_implementation"]

    assert report["BM006"]["passed"] is False
    assert any(d.startswith("mismatch:") for d in report["BM006"]["diagnostics"])
    assert report["BM006"]["expected"] == 6
    assert report["BM006"]["actual"] == 0
