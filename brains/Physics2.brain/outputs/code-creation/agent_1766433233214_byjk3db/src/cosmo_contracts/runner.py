"""cosmo_contracts.runner

Runs contributed benchmark implementations against canonical contract test vectors
and produces a per-contract compliance report (pass/fail + diagnostics).

This module is intentionally self-contained so it can be used even when only
contracts (dicts) and implementations (callables/import paths) are available.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Union
Number = Union[int, float]


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _iterable(x: Any) -> bool:
    return isinstance(x, (list, tuple))


def _load_impl(spec: Union[str, Callable[..., Any]]) -> Callable[..., Any]:
    """Load an implementation from a callable or a 'module:attr' string."""
    if callable(spec):
        return spec
    if not isinstance(spec, str) or ":" not in spec:
        raise TypeError("Implementation spec must be callable or 'module:attr' string")
    mod, attr = spec.split(":", 1)
    fn = getattr(import_module(mod), attr)
    if not callable(fn):
        raise TypeError(f"Loaded object {spec!r} is not callable")
    return fn
def _approx_equal(a: Any, b: Any, *, atol: float, rtol: float) -> Tuple[bool, str]:
    """Deep approximate equality with useful diagnostics (no numpy required)."""
    if a is b:
        return True, ""
    if _is_number(a) and _is_number(b):
        diff = abs(a - b)
        tol = atol + rtol * abs(b)
        ok = diff <= tol
        return ok, f"abs_diff={diff} tol={tol} a={a} b={b}" if not ok else ""
    if isinstance(a, str) or isinstance(b, str):
        ok = a == b
        return ok, f"a={a!r} b={b!r}" if not ok else ""
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        if set(a.keys()) != set(b.keys()):
            return False, f"dict_keys a={sorted(a.keys())} b={sorted(b.keys())}"
        for k in a:
            ok, diag = _approx_equal(a[k], b[k], atol=atol, rtol=rtol)
            if not ok:
                return False, f"key={k!r}: {diag}"
        return True, ""
    if _iterable(a) and _iterable(b):
        if len(a) != len(b):
            return False, f"len a={len(a)} b={len(b)}"
        for i, (ai, bi) in enumerate(zip(a, b)):
            ok, diag = _approx_equal(ai, bi, atol=atol, rtol=rtol)
            if not ok:
                return False, f"idx={i}: {diag}"
        return True, ""
    ok = a == b
    return ok, f"a={a!r} b={b!r}" if not ok else ""
def _exact_equal(a: Any, b: Any) -> Tuple[bool, str]:
    if a is b:
        return True, ""
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        if set(a.keys()) != set(b.keys()):
            return False, f"dict_keys a={sorted(a.keys())} b={sorted(b.keys())}"
        for k in a:
            ok, diag = _exact_equal(a[k], b[k])
            if not ok:
                return False, f"key={k!r}: {diag}"
        return True, ""
    if _iterable(a) and _iterable(b):
        if len(a) != len(b):
            return False, f"len a={len(a)} b={len(b)}"
        for i, (ai, bi) in enumerate(zip(a, b)):
            ok, diag = _exact_equal(ai, bi)
            if not ok:
                return False, f"idx={i}: {diag}"
        return True, ""
    ok = a == b
    return ok, f"a={a!r} b={b!r}" if not ok else ""
def validate_contract(contract: Mapping[str, Any]) -> List[str]:
    """Return diagnostics (empty => structurally OK)."""
    required = ["id", "metadata", "reference", "invariants", "tolerance", "test_vector"]
    diags: List[str] = []
    for k in required:
        if k not in contract:
            diags.append(f"missing_section:{k}")
    meta_req = ["name", "version"]
    md = contract.get("metadata") if isinstance(contract.get("metadata"), Mapping) else {}
    for k in meta_req:
        if k not in md:
            diags.append(f"missing_metadata:{k}")
    tv = contract.get("test_vector")
    if tv is None or not isinstance(tv, Mapping):
        diags.append("invalid_test_vector")
    else:
        if not any(k in tv for k in ("args", "kwargs", "input")):
            diags.append("test_vector_missing_inputs")
        if "expected" not in tv:
            diags.append("test_vector_missing_expected")
    tol = contract.get("tolerance")
    if isinstance(tol, Mapping):
        pol = tol.get("policy", "exact")
        if pol not in ("exact", "approx"):
            diags.append(f"invalid_tolerance_policy:{pol}")
    return diags
def _apply_invariants(invariants: Mapping[str, Any], output: Any) -> List[str]:
    diags: List[str] = []
    if not isinstance(invariants, Mapping):
        return diags
    t = invariants.get("output_type")
    if t:
        allowed = tuple(getattr(__builtins__, t, object) for t in ([t] if isinstance(t, str) else t))
        if allowed and not isinstance(output, allowed):
            diags.append(f"invariant_output_type_failed: got={type(output).__name__}")
    keys = invariants.get("dict_keys")
    if keys is not None:
        if not isinstance(output, Mapping):
            diags.append("invariant_dict_keys_failed:not_a_dict")
        else:
            missing = [k for k in keys if k not in output]
            extra = [k for k in output.keys() if k not in set(keys)]
            if missing:
                diags.append(f"invariant_dict_missing_keys:{missing}")
            if extra:
                diags.append(f"invariant_dict_extra_keys:{sorted(extra)}")
    length = invariants.get("length")
    if length is not None:
        if not _iterable(output):
            diags.append("invariant_length_failed:not_a_sequence")
        elif len(output) != int(length):
            diags.append(f"invariant_length_failed: got={len(output)} expected={int(length)}")
    return diags
@dataclass
class ComplianceResult:
    benchmark_id: str
    passed: bool
    diagnostics: List[str]
    expected: Any = None
    actual: Any = None


def run_contract(contract: Mapping[str, Any], impl: Union[str, Callable[..., Any]]) -> ComplianceResult:
    bid = str(contract.get("id", "<unknown>"))
    diags = validate_contract(contract)
    if diags:
        return ComplianceResult(bid, False, diags)

    fn = _load_impl(impl)
    tv = contract["test_vector"]
    args = tv.get("args")
    kwargs = tv.get("kwargs")
    if "input" in tv and args is None and kwargs is None:
        inp = tv["input"]
        args = inp.get("args", []) if isinstance(inp, Mapping) else [inp]
        kwargs = inp.get("kwargs", {}) if isinstance(inp, Mapping) else {}
    args = list(args) if args is not None else []
    kwargs = dict(kwargs) if kwargs is not None else {}
    expected = tv.get("expected")

    try:
        actual = fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        return ComplianceResult(bid, False, [f"exception:{type(e).__name__}:{e}"], expected=expected)

    diags.extend(_apply_invariants(contract.get("invariants", {}), actual))

    tol = contract.get("tolerance", {}) if isinstance(contract.get("tolerance"), Mapping) else {}
    policy = tol.get("policy", "exact")
    if policy == "approx":
        atol = float(tol.get("atol", 0.0))
        rtol = float(tol.get("rtol", 0.0))
        ok, diag = _approx_equal(actual, expected, atol=atol, rtol=rtol)
    else:
        ok, diag = _exact_equal(actual, expected)
    if not ok:
        diags.append(f"mismatch:{diag}")
    passed = ok and not diags
    return ComplianceResult(bid, passed, diags, expected=expected, actual=actual)
def run_compliance(
    contracts: Iterable[Mapping[str, Any]],
    implementations: Mapping[str, Union[str, Callable[..., Any]]],
) -> Dict[str, Any]:
    """Run all contracts against provided implementations.

    Returns a JSON-serializable dict keyed by benchmark id:
    {id: {passed: bool, diagnostics: [...], expected: ..., actual: ...}}
    """
    report: Dict[str, Any] = {}
    for c in contracts:
        bid = str(c.get("id", "<unknown>"))
        impl = implementations.get(bid)
        if impl is None:
            report[bid] = {"passed": False, "diagnostics": ["missing_implementation"]}
            continue
        res = run_contract(c, impl)
        report[bid] = {
            "passed": bool(res.passed),
            "diagnostics": list(res.diagnostics),
        }
        if not res.passed:
            report[bid]["expected"] = res.expected
            report[bid]["actual"] = res.actual
    return report
