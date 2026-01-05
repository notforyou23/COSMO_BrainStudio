import json
from collections.abc import Mapping, Sequence

import pytest


def _to_jsonable(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Mapping):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_to_jsonable(v) for v in obj]
    for attr in ("model_dump", "dict", "to_dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return _to_jsonable(fn())
            except TypeError:
                try:
                    return _to_jsonable(fn(exclude_none=True))
                except Exception:
                    return _to_jsonable(fn())
    if hasattr(obj, "__dict__"):
        return _to_jsonable(vars(obj))
    return str(obj)


def _contains_text(tree, needles):
    blob = json.dumps(_to_jsonable(tree), sort_keys=True).lower()
    return all(n.lower() in blob for n in needles)


def _find_keypaths(tree, key_lower, prefix=""):
    out = []
    if isinstance(tree, Mapping):
        for k, v in tree.items():
            kp = f"{prefix}.{k}" if prefix else str(k)
            if str(k).lower() == key_lower:
                out.append(kp)
            out.extend(_find_keypaths(v, key_lower, kp))
    elif isinstance(tree, Sequence) and not isinstance(tree, (str, bytes, bytearray)):
        for i, v in enumerate(tree):
            kp = f"{prefix}[{i}]"
            out.extend(_find_keypaths(v, key_lower, kp))
    return out


def _get_any(plan, *names):
    if isinstance(plan, Mapping):
        for n in names:
            if n in plan:
                return plan[n]
    for n in names:
        v = getattr(plan, n, None)
        if v is not None:
            return v
    return None


def build_plan():
    try:
        import trialplanner  # type: ignore
    except Exception as e:
        pytest.fail(f"Could not import trialplanner package: {e}")

    candidates = [
        "build_multi_wave_plan",
        "build_multiwave_plan",
        "build_plan",
        "generate_plan",
        "make_plan",
        "example_plan",
        "default_plan",
    ]
    for name in candidates:
        fn = getattr(trialplanner, name, None)
        if callable(fn):
            try:
                return fn()
            except TypeError:
                try:
                    return fn(seed=123)
                except Exception:
                    return fn()

    # If no function, look for a Plan class with a constructor/factory.
    Plan = getattr(trialplanner, "Plan", None)
    if Plan is not None:
        try:
            return Plan()  # pragma: no cover
        except Exception as e:  # pragma: no cover
            pytest.fail(f"Found trialplanner.Plan but could not instantiate: {e}")

    pytest.fail(
        "No recognizable plan-builder entry point found on trialplanner. "
        f"Tried: {', '.join(candidates)}"
    )


def test_end_to_end_plan_has_required_components():
    plan = build_plan()
    plan_dict = _to_jsonable(plan)

    # Core intervention arms
    assert _contains_text(plan_dict, ["choice", "architecture"]) or _contains_text(
        plan_dict, ["nudge"]
    ), "Plan must include a choice-architecture/nudge arm"
    assert _contains_text(
        plan_dict, ["debias"]
    ), "Plan must include a targeted debiasing arm"
    assert _contains_text(
        plan_dict, ["sleep"]
    ), "Plan must include a sleep-restoration arm"

    # ZPD (type, timing, fading)
    assert _contains_text(plan_dict, ["zpd"]), "Plan must operationalize ZPD support"
    for term in ("type", "timing", "fading"):
        assert _contains_text(
            plan_dict, [term]
        ), f"Plan must include ZPD factor: {term}"

    # Cognitive growth mediators (within-child): executive function + processing speed
    assert _contains_text(
        plan_dict, ["executive", "function"]
    ), "Plan must include executive function proximal mediator/measure"
    assert _contains_text(
        plan_dict, ["processing", "speed"]
    ), "Plan must include processing speed proximal mediator/measure"

    # Link to reasoning and real-world decisions (distal outcomes)
    assert _contains_text(plan_dict, ["reason"]), "Plan must include reasoning outcome"
    assert _contains_text(
        plan_dict, ["decision"]
    ), "Plan must include real-world decision outcome"

    # Multi-wave schedule + durability/transfer within cohorts
    for term in ("wave", "baseline", "follow"):
        assert _contains_text(plan_dict, [term]), f"Plan must encode multi-wave {term}"
    assert _contains_text(
        plan_dict, ["transfer"]
    ), "Plan must specify transfer tests (near/far)"
    assert _contains_text(
        plan_dict, ["durab"]
    ) or _contains_text(
        plan_dict, ["maintenance"]
    ), "Plan must specify durability/maintenance assessment"

    # Causal chain tests: mediation + moderation
    assert _contains_text(
        plan_dict, ["mediat"]
    ), "Plan must include mediation tests for causal chain"
    assert _contains_text(
        plan_dict, ["moder"]
    ) or _contains_text(
        plan_dict, ["interaction"]
    ), "Plan must include moderation/interaction tests"

    # Measurement schedules must name proximal mediators and distal outcomes
    schedule = _get_any(plan, "schedule", "measurement_schedule", "measurements", "timeline")
    assert schedule is not None, "Plan must include a measurement schedule/timeline object"
    schedule_dict = _to_jsonable(schedule)
    assert _contains_text(
        schedule_dict, ["executive", "function"]
    ), "Measurement schedule must include executive function"
    assert _contains_text(
        schedule_dict, ["processing", "speed"]
    ), "Measurement schedule must include processing speed"
    assert _contains_text(
        schedule_dict, ["reason"]
    ), "Measurement schedule must include reasoning"
    assert _contains_text(
        schedule_dict, ["decision"]
    ), "Measurement schedule must include decision outcomes"

    # Logistics needed to compare transfer/durability within same cohorts
    logistics = _get_any(plan, "logistics", "operations", "implementation", "fielding")
    assert logistics is not None, "Plan must include logistics/operations section"
    logistics_dict = _to_jsonable(logistics)
    for term in ("cohort", "random", "fidelity"):
        assert _contains_text(
            logistics_dict, [term]
        ), f"Logistics should address: {term}"

    # Defensive: surface likely schema locations (helps debug missing fields)
    assert not _find_keypaths(plan_dict, "todo"), "Plan must not contain TODO placeholders"
