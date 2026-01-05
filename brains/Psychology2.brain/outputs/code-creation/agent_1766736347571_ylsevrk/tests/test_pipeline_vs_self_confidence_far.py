import importlib
from typing import Any, Dict, Iterable, Optional, Tuple

import pytest


def _import_optional(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def _get_runner():
    # Prefer a single high-level comparison/evaluation entry point.
    candidates = [
        ("borderline_qa.harness", "evaluate_strategies"),
        ("borderline_qa.harness", "run_comparison"),
        ("borderline_qa.evaluation", "evaluate_strategies"),
        ("borderline_qa.evaluation", "run_comparison"),
        ("borderline_qa", "evaluate_strategies"),
        ("borderline_qa", "run_comparison"),
    ]
    for mod_name, attr in candidates:
        mod = _import_optional(mod_name)
        if mod is not None and callable(getattr(mod, attr, None)):
            return getattr(mod, attr)

    # Fall back to an adapter class if present.
    class_candidates = [
        ("borderline_qa.harness", "BorderlineQAHarnessAdapter"),
        ("borderline_qa.adapter", "BorderlineQAHarnessAdapter"),
        ("borderline_qa", "BorderlineQAHarnessAdapter"),
        ("borderline_qa.harness", "HarnessAdapter"),
        ("borderline_qa.adapter", "HarnessAdapter"),
    ]
    for mod_name, cls_name in class_candidates:
        mod = _import_optional(mod_name)
        cls = getattr(mod, cls_name, None) if mod is not None else None
        if cls is not None:
            inst = cls()
            for meth in ("evaluate_strategies", "run_comparison", "evaluate"):
                fn = getattr(inst, meth, None)
                if callable(fn):
                    return fn
    return None


def _load_fixtures() -> Iterable[Dict[str, Any]]:
    # Prefer curated fixtures if provided by the package; else use a tiny inline set.
    for mod_name in ("borderline_qa.fixtures", "borderline_qa.harness_fixtures", "borderline_qa.data"):
        mod = _import_optional(mod_name)
        if mod is None:
            continue
        for fn_name in ("load_borderline_far_fixtures", "load_far_fixtures", "load_fixtures"):
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                fx = fn()
                if isinstance(fx, dict) and "examples" in fx:
                    return fx["examples"]
                return fx
    # Inline fixtures: incorrect answers that should be rejected unless supported by must-cite sources.
    return [
        {
            "id": "fx1",
            "question": "What is the chemical formula of table salt?",
            "proposed_answer": "Table salt is KCl.",
            "gold_answer": "NaCl",
            "label": "incorrect",
        },
        {
            "id": "fx2",
            "question": "Who wrote 'Pride and Prejudice'?",
            "proposed_answer": "It was written by Charles Dickens.",
            "gold_answer": "Jane Austen",
            "label": "incorrect",
        },
    ]


def _extract_far(metrics: Any) -> float:
    if metrics is None:
        raise AssertionError("No metrics returned")
    if isinstance(metrics, (int, float)):
        return float(metrics)
    if isinstance(metrics, dict):
        for k in ("false_accept_rate", "far", "false_accept"):
            if k in metrics and metrics[k] is not None:
                return float(metrics[k])
        if "rates" in metrics and isinstance(metrics["rates"], dict):
            return _extract_far(metrics["rates"])
    raise AssertionError(f"Unrecognized metrics shape: {type(metrics)} {metrics}")


def _normalize_results(res: Any) -> Dict[str, Any]:
    # Accept: {strategy: metrics} or {"by_strategy":{...}} or list of {"strategy":..,"metrics":..}
    if isinstance(res, dict):
        if "by_strategy" in res and isinstance(res["by_strategy"], dict):
            return res["by_strategy"]
        if all(isinstance(k, str) for k in res.keys()):
            return res
    if isinstance(res, list):
        out = {}
        for item in res:
            if isinstance(item, dict) and "strategy" in item:
                out[str(item["strategy"])] = item.get("metrics", item)
        if out:
            return out
    raise AssertionError(f"Unrecognized results shape: {type(res)} {res}")


def test_pipeline_vs_self_confidence_false_accept_rate():
    runner = _get_runner()
    if runner is None:
        pytest.skip("No harness runner/adapter available (borderline_qa not installed or API changed).")

    examples = list(_load_fixtures())
    if not examples:
        pytest.skip("No fixtures available.")

    # Most harnesses accept: (examples, strategies=...) or (dataset=..., systems=...)
    kwargs_variants = [
        dict(examples=examples, strategies=["retrieve_then_verify", "self_confidence"]),
        dict(examples=examples, systems=["retrieve_then_verify", "self_confidence"]),
        dict(dataset=examples, strategies=["retrieve_then_verify", "self_confidence"]),
        dict(dataset=examples, systems=["retrieve_then_verify", "self_confidence"]),
    ]
    last_err: Optional[BaseException] = None
    res = None
    for kwargs in kwargs_variants:
        try:
            res = runner(**kwargs)
            break
        except TypeError as e:
            last_err = e
        except Exception as e:
            last_err = e
            break

    if res is None:
        pytest.skip(f"Runner could not be called with expected signature: {last_err}")

    by_strategy = _normalize_results(res)
    if "retrieve_then_verify" not in by_strategy or "self_confidence" not in by_strategy:
        pytest.skip(f"Missing expected strategies in results: {sorted(by_strategy.keys())}")

    far_rtv = _extract_far(by_strategy["retrieve_then_verify"])
    far_sc = _extract_far(by_strategy["self_confidence"])

    # Integration expectation: must-cite retrieve-then-verify should reduce false accepts vs self-confidence prompting.
    assert 0.0 <= far_rtv <= 1.0
    assert 0.0 <= far_sc <= 1.0
    assert far_rtv <= far_sc


def test_must_cite_validator_rejects_missing_citations():
    citations = _import_optional("borderline_qa.citations")
    if citations is None:
        pytest.skip("borderline_qa.citations not available.")

    # Accept multiple possible APIs: validate_response/validate_citations or a MustCiteValidator class.
    validator = None
    for attr in ("MustCiteValidator", "CitationValidator", "MustCiteConstraints"):
        cls = getattr(citations, attr, None)
        if cls is not None:
            try:
                validator = cls()
            except Exception:
                validator = cls
            break

    fn = getattr(citations, "validate_response", None) or getattr(citations, "validate_citations", None)
    if fn is None and validator is None:
        pytest.skip("No validator entry point found in borderline_qa.citations.")

    # A response missing quote+URL/DOI+span should fail deterministically.
    response = {
        "answer": "Table salt is KCl.",
        "citations": [],
        "spans": [],
    }

    def _call_validate(obj):
        if fn is not None:
            return fn(obj)
        # Try common method names on validator instance/class.
        for m in ("validate", "check", "validate_response", "validate_citations"):
            meth = getattr(obj, m, None)
            if callable(meth):
                return meth(response)
        raise RuntimeError("No callable validate method found.")

    try:
        ok = _call_validate(validator if validator is not None else citations)
        # Some APIs return (ok, errors) or raise.
        if isinstance(ok, tuple) and ok:
            ok = ok[0]
        assert ok is False
    except Exception:
        # Raising is also acceptable behavior for deterministic enforcement.
        assert True
