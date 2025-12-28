import csv
from pathlib import Path

import numpy as np
import pytest


def _import_symbols():
    from evconv_config.assumptions import (
        DEFAULT_ASSUMPTIONS_BY_SEGMENT,
        merge_assumptions,
        parse_user_inputs_csv,
        compare_ice_conversion_bev,
    )
    from evconv_config.drive_cycles import DRIVE_CYCLE_PROXIES, get_drive_cycle

    return (
        DEFAULT_ASSUMPTIONS_BY_SEGMENT,
        merge_assumptions,
        parse_user_inputs_csv,
        compare_ice_conversion_bev,
        DRIVE_CYCLE_PROXIES,
        get_drive_cycle,
    )


def test_defaults_merge_by_segment_and_overrides():
    (
        DEFAULTS,
        merge_assumptions,
        _parse_user_inputs_csv,
        _compare,
        _CYCLES,
        _get_cycle,
    ) = _import_symbols()

    assert set(DEFAULTS) >= {"fleet", "classic", "specialty"}
    fleet = DEFAULTS["fleet"]
    for k in ("utilization_km_per_year", "energy_price_per_kwh", "diesel_price_per_liter", "discount_rate"):
        assert k in fleet

    merged = merge_assumptions(segment="fleet", overrides={"energy_price_per_kwh": 0.42})
    assert merged["energy_price_per_kwh"] == pytest.approx(0.42)
    assert merged["utilization_km_per_year"] == fleet["utilization_km_per_year"]
    assert merged["segment"] == "fleet"

    merged2 = merge_assumptions(segment="classic", overrides={"utilization_km_per_year": 2500})
    assert merged2["segment"] == "classic"
    assert merged2["utilization_km_per_year"] == 2500
    assert merged2["energy_price_per_kwh"] == DEFAULTS["classic"]["energy_price_per_kwh"]


def test_csv_template_parsing_and_defaults_applied(tmp_path: Path):
    (
        _DEFAULTS,
        _merge,
        parse_user_inputs_csv,
        _compare,
        _CYCLES,
        _get_cycle,
    ) = _import_symbols()

    p = tmp_path / "template_user_inputs.csv"
    headers = [
        "scenario_id",
        "segment",
        "cycle",
        "energy_price_per_kwh",
        "utilization_km_per_year",
        "battery_replacement_year",
        "financing_apr",
        "financing_term_years",
    ]
    rows = [
        {
            "scenario_id": "A",
            "segment": "fleet",
            "cycle": "urban",
            "energy_price_per_kwh": "",
            "utilization_km_per_year": "32000",
            "battery_replacement_year": "",
            "financing_apr": "0.08",
            "financing_term_years": "5",
        }
    ]
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)

    parsed = parse_user_inputs_csv(p)
    assert isinstance(parsed, list) and len(parsed) == 1
    r = parsed[0]
    assert r["scenario_id"] == "A"
    assert r["segment"] == "fleet"
    assert r["cycle"] == "urban"
    assert isinstance(r["utilization_km_per_year"], (int, float))
    assert r["utilization_km_per_year"] == pytest.approx(32000)
    assert isinstance(r["energy_price_per_kwh"], (int, float))
    assert r["energy_price_per_kwh"] > 0
    assert r["battery_replacement_year"] is None or isinstance(r["battery_replacement_year"], int)


def test_drive_cycle_proxy_integrity_and_selection():
    (
        _DEFAULTS,
        _merge,
        _parse,
        _compare,
        CYCLES,
        get_drive_cycle,
    ) = _import_symbols()

    assert set(CYCLES) >= {"urban", "mixed", "highway"}
    means = {}
    for name in ("urban", "mixed", "highway"):
        cyc = get_drive_cycle(name)
        t = np.asarray(cyc["time_s"], dtype=float)
        v = np.asarray(cyc["speed_mps"], dtype=float)
        assert len(t) == len(v) and len(t) >= 60
        assert np.all(np.diff(t) > 0)
        assert np.all(v >= 0)
        means[name] = float(np.mean(v))

    assert means["urban"] < means["mixed"] < means["highway"]

    cyc2 = get_drive_cycle("urban", dt_s=1.0)
    t2 = np.asarray(cyc2["time_s"], dtype=float)
    assert np.allclose(np.diff(t2), 1.0, atol=1e-9)


def test_deterministic_scenario_comparison_outputs():
    (
        _DEFAULTS,
        merge_assumptions,
        _parse,
        compare_ice_conversion_bev,
        _CYCLES,
        _get_cycle,
    ) = _import_symbols()

    cfg = merge_assumptions(
        segment="fleet",
        overrides={
            "utilization_km_per_year": 30000,
            "energy_price_per_kwh": 0.20,
            "diesel_price_per_liter": 1.60,
            "battery_replacement_year": None,
            "financing_apr": 0.06,
            "financing_term_years": 5,
        },
    )

    out1 = compare_ice_conversion_bev(cfg, cycle="mixed")
    out2 = compare_ice_conversion_bev(cfg, cycle="mixed")
    assert out1 == out2

    for scenario in ("ice", "conversion", "bev"):
        assert scenario in out1 and isinstance(out1[scenario], dict)
        for k in ("tco_total", "energy_per_km"):
            assert k in out1[scenario]
            assert np.isfinite(out1[scenario][k])

    assert out1["bev"]["energy_per_km"] < out1["ice"]["energy_per_km"]
    assert out1["conversion"]["energy_per_km"] < out1["ice"]["energy_per_km"]
