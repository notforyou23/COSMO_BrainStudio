import pytest

from cli_tool import runner


def _base_config():
    return {
        "goal": "goal_10",
        "seed": 123,
        "risk_thresholds": {"low": 0.1, "medium": 0.3, "high": 0.6},
        "claim_decomposition": True,
        "model": "example-model",
        "inputs": {"text": "hello"},
    }
def test_hash_config_is_stable_across_key_order():
    cfg1 = _base_config()
    cfg2 = {
        "inputs": {"text": "hello"},
        "model": "example-model",
        "claim_decomposition": True,
        "risk_thresholds": {"high": 0.6, "medium": 0.3, "low": 0.1},
        "seed": 123,
        "goal": "goal_10",
    }
    h1 = runner.hash_config(cfg1)
    h2 = runner.hash_config(cfg2)
    assert isinstance(h1, str) and h1
    assert h1 == h2
def test_stable_run_id_is_deterministic_and_changes_on_config_change():
    cfg = _base_config()
    rid1 = runner.stable_run_id(cfg)
    rid2 = runner.stable_run_id(cfg)
    assert isinstance(rid1, str) and rid1
    assert rid1 == rid2

    cfg_changed = _base_config()
    cfg_changed["seed"] = 124
    rid3 = runner.stable_run_id(cfg_changed)
    assert rid3 != rid1
def test_stable_run_id_is_consistent_with_hash_config():
    cfg = _base_config()
    rid = runner.stable_run_id(cfg)
    h = runner.hash_config(cfg)
    # Require the run id to be derived from the same deterministic config hash.
    assert h in rid or rid in h or rid.endswith(h[:8]) or rid.startswith(h[:8])
@pytest.mark.parametrize(
    "bad_cfg,err_substr",
    [
        ({"risk_thresholds": {"low": -0.1, "medium": 0.2, "high": 0.6}}, "risk"),
        ({"risk_thresholds": {"low": 0.1, "medium": 1.2, "high": 0.6}}, "risk"),
        ({"risk_thresholds": {"low": 0.4, "medium": 0.3, "high": 0.6}}, "risk"),
        ({"claim_decomposition": "yes"}, "claim"),
        ({"seed": -1}, "seed"),
    ],
)
def test_validate_invariants_failure_modes(bad_cfg, err_substr):
    cfg = _base_config()
    cfg.update(bad_cfg)
    with pytest.raises(ValueError) as e:
        runner.validate_invariants(cfg)
    assert err_substr.lower() in str(e.value).lower()
def test_validate_invariants_accepts_valid_config():
    cfg = _base_config()
    # Should not raise.
    runner.validate_invariants(cfg)
