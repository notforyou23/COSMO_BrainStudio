import importlib
import pytest


def _get_validator_module():
    for name in ("claim_cards.validator", "src.claim_cards.validator"):
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    raise AssertionError("Could not import validator module (expected claim_cards.validator)")


def _call_validate(card: dict) -> dict:
    m = _get_validator_module()
    fn = None
    for candidate in ("validate_claim_card", "validate_card", "validate", "validate_claim"):
        if hasattr(m, candidate) and callable(getattr(m, candidate)):
            fn = getattr(m, candidate)
            break
    if fn is None:
        raise AssertionError("Validator module missing a callable validate function (e.g., validate_claim_card)")

    res = fn(card)

    out = {"valid": None, "abstain": None, "errors": [], "reason": None, "raw": res}
    if isinstance(res, tuple):
        if len(res) >= 1:
            out["valid"] = bool(res[0])
        if len(res) >= 2 and res[1] is not None:
            out["errors"] = list(res[1]) if isinstance(res[1], (list, tuple)) else [str(res[1])]
        if len(res) >= 3:
            out["abstain"] = bool(res[2])
        if len(res) >= 4 and res[3] is not None:
            out["reason"] = str(res[3])
        return out

    if isinstance(res, dict):
        for k in ("valid", "is_valid", "ok"):
            if k in res and res[k] is not None:
                out["valid"] = bool(res[k])
                break
        for k in ("abstain", "should_abstain"):
            if k in res and res[k] is not None:
                out["abstain"] = bool(res[k])
                break
        for k in ("errors", "error_messages", "issues"):
            if k in res and res[k] is not None:
                out["errors"] = list(res[k]) if isinstance(res[k], (list, tuple)) else [str(res[k])]
                break
        for k in ("reason", "abstain_reason", "message"):
            if k in res and res[k] is not None:
                out["reason"] = str(res[k])
                break
        return out

    for attr in ("valid", "is_valid", "ok"):
        if hasattr(res, attr):
            out["valid"] = bool(getattr(res, attr))
            break
    for attr in ("abstain", "should_abstain"):
        if hasattr(res, attr):
            out["abstain"] = bool(getattr(res, attr))
            break
    for attr in ("errors", "error_messages", "issues"):
        if hasattr(res, attr) and getattr(res, attr) is not None:
            e = getattr(res, attr)
            out["errors"] = list(e) if isinstance(e, (list, tuple)) else [str(e)]
            break
    for attr in ("reason", "abstain_reason", "message"):
        if hasattr(res, attr) and getattr(res, attr) is not None:
            out["reason"] = str(getattr(res, attr))
            break
    return out


def _base_valid_card() -> dict:
    return {
        "claim_text": "We reduced processing time by 40% in Q3 2024.",
        "claim_is_verbatim": True,
        "context": {
            "speaker": "Jane Doe",
            "date": "2024-10-15",
            "link": "https://example.com/transcript",
        },
        "provenance_anchor": {
            "type": "url",
            "value": "https://example.com/transcript#t=123.4",
        },
    }
def test_valid_card_passes():
    card = _base_valid_card()
    r = _call_validate(card)
    assert r["valid"] is True or r["valid"] is None, f"Unexpected result: {r}"
    assert r["abstain"] in (False, None), f"Should not abstain for a complete valid card: {r}"
    assert not r["errors"], f"Expected no errors for valid card: {r}"


@pytest.mark.parametrize("missing_key", ["claim_text", "context", "provenance_anchor"])
def test_missing_required_fields_triggers_abstention(missing_key):
    card = _base_valid_card()
    card.pop(missing_key, None)
    r = _call_validate(card)
    if r["abstain"] is not None:
        assert r["abstain"] is True, f"Expected abstention when missing {missing_key}: {r}"
    if r["valid"] is not None:
        assert r["valid"] is False, f"Expected invalid when missing {missing_key}: {r}"
    assert r["errors"] or r["reason"], f"Expected actionable errors/reason when missing {missing_key}: {r}"


@pytest.mark.parametrize("ctx_key", ["speaker", "date", "link"])
def test_missing_context_fields_triggers_abstention(ctx_key):
    card = _base_valid_card()
    card["context"].pop(ctx_key, None)
    r = _call_validate(card)
    if r["abstain"] is not None:
        assert r["abstain"] is True, f"Expected abstention when context missing {ctx_key}: {r}"
    if r["valid"] is not None:
        assert r["valid"] is False, f"Expected invalid when context missing {ctx_key}: {r}"
    assert r["errors"] or r["reason"], f"Expected actionable errors/reason when context missing {ctx_key}: {r}"


def test_non_verbatim_claim_rejected():
    card = _base_valid_card()
    card["claim_is_verbatim"] = False
    r = _call_validate(card)
    if r["valid"] is not None:
        assert r["valid"] is False, f"Non-verbatim claims must be rejected: {r}"
    assert r["errors"] or r["reason"], f"Expected actionable errors/reason for non-verbatim claim: {r}"
    if r["abstain"] is not None:
        assert r["abstain"] is False, f"Non-verbatim should be a validation failure (not abstention): {r}"


def test_missing_provenance_anchor_abstains():
    card = _base_valid_card()
    card.pop("provenance_anchor", None)
    r = _call_validate(card)
    if r["abstain"] is not None:
        assert r["abstain"] is True, f"Expected abstention when provenance anchor is missing: {r}"
    if r["valid"] is not None:
        assert r["valid"] is False, f"Expected invalid when provenance anchor is missing: {r}"
    assert r["errors"] or r["reason"], f"Expected actionable errors/reason when provenance anchor missing: {r}"
