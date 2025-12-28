from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple


def annuity_payment(principal: float, annual_rate: float, years: float) -> float:
    if years <= 0:
        return float(principal)
    r = max(0.0, float(annual_rate))
    if r == 0:
        return float(principal) / years
    return float(principal) * (r * (1 + r) ** years) / ((1 + r) ** years - 1)


def _as_cycle_arrays(cycle: Any) -> Tuple[list, list]:
    if cycle is None:
        raise ValueError("cycle is required")
    if isinstance(cycle, Mapping):
        t = cycle.get("t_s") or cycle.get("t") or cycle.get("time_s") or cycle.get("time")
        v = cycle.get("v_mps") or cycle.get("v") or cycle.get("speed_mps") or cycle.get("speed")
    else:
        t = getattr(cycle, "t_s", None) or getattr(cycle, "t", None) or getattr(cycle, "time_s", None)
        v = getattr(cycle, "v_mps", None) or getattr(cycle, "v", None) or getattr(cycle, "speed_mps", None)
    if t is None or v is None:
        raise ValueError("cycle must provide time (t_s) and speed (v_mps)")
    t = list(t)
    v = list(v)
    if len(t) != len(v) or len(t) < 2:
        raise ValueError("cycle arrays must be same length >= 2")
    return t, v


def cycle_distance_km(cycle: Any) -> float:
    t, v = _as_cycle_arrays(cycle)
    dist_m = 0.0
    for i in range(1, len(t)):
        dt = float(t[i]) - float(t[i - 1])
        if dt <= 0:
            continue
        dist_m += max(0.0, float(v[i - 1])) * dt
    return dist_m / 1000.0


def apply_toggles(d: Mapping[str, float], toggles: Optional[Mapping[str, float]]) -> Dict[str, float]:
    out = dict(d or {})
    if not toggles:
        return out
    for k, m in toggles.items():
        if m is None:
            continue
        out[k] = float(out.get(k, 0.0)) * float(m)
    return out


@dataclass
class ScenarioResult:
    name: str
    annual_km: float
    annual_cost: float
    cost_per_km: float
    annual_energy_cost: float
    annual_maintenance_cost: float
    annual_financing_cost: float
    annual_batt_repl_cost: float
    annual_other_fixed: float
    energy_kwh_per_km: float
    fuel_l_per_km: float
    cycle_km: float

    def as_dict(self) -> Dict[str, float]:
        return self.__dict__.copy()
def _get(d: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    v = d.get(key, default)
    return default if v is None else float(v)


def _annual_km(inputs: Mapping[str, Any], toggles: Optional[Mapping[str, float]]) -> float:
    base = _get(inputs, "annual_km", _get(inputs, "annual_miles", 0.0) * 1.60934)
    util_mult = 1.0
    if toggles and "utilization" in toggles:
        util_mult = float(toggles["utilization"])
    return max(0.0, base * util_mult)


def _energy_prices(inputs: Mapping[str, Any], toggles: Optional[Mapping[str, float]]) -> Dict[str, float]:
    base = {
        "electricity_usd_per_kwh": _get(inputs, "electricity_usd_per_kwh", _get(inputs, "energy_price_usd_per_kwh", 0.0)),
        "fuel_usd_per_l": _get(inputs, "fuel_usd_per_l", _get(inputs, "gas_usd_per_l", 0.0)),
    }
    if toggles and "energy_price" in toggles:
        m = float(toggles["energy_price"])
        base = {k: v * m for k, v in base.items()}
    return base


def _finance_rate(inputs: Mapping[str, Any], toggles: Optional[Mapping[str, float]]) -> float:
    r = _get(inputs, "financing_rate", _get(inputs, "apr", 0.0))
    if toggles and "financing" in toggles:
        r *= float(toggles["financing"])
    return max(0.0, r)


def _batt_repl_mult(toggles: Optional[Mapping[str, float]]) -> float:
    return float(toggles.get("battery_replacement", 1.0)) if toggles else 1.0


def compute_scenario(
    name: str,
    cycle: Any,
    inputs: Mapping[str, Any],
    params: Mapping[str, Any],
    toggles: Optional[Mapping[str, float]] = None,
) -> ScenarioResult:
    cycle_km = cycle_distance_km(cycle)
    annual_km = _annual_km(inputs, toggles)
    prices = _energy_prices(inputs, toggles)
    finance_rate = _finance_rate(inputs, toggles)

    capex = _get(params, "capex_usd", 0.0)
    term_yr = max(0.0, _get(params, "finance_term_yr", _get(inputs, "finance_term_yr", 0.0)))
    financing_cost = annuity_payment(capex, finance_rate, term_yr) if term_yr > 0 else capex

    other_fixed = _get(params, "annual_fixed_usd", 0.0) + _get(inputs, "annual_fixed_usd", 0.0)
    maint_per_km = _get(params, "maintenance_usd_per_km", _get(params, "maint_usd_per_km", 0.0))
    annual_maint = maint_per_km * annual_km

    fuel_l_per_km = _get(params, "fuel_l_per_km", 0.0)
    kwh_per_km = _get(params, "energy_kwh_per_km", _get(params, "kwh_per_km", 0.0))

    energy_cost = (fuel_l_per_km * annual_km * prices["fuel_usd_per_l"]) + (kwh_per_km * annual_km * prices["electricity_usd_per_kwh"])

    batt_repl_cost = 0.0
    batt_cost = _get(params, "battery_replacement_usd", 0.0) * _batt_repl_mult(toggles)
    batt_interval_km = _get(params, "battery_replacement_interval_km", 0.0)
    if batt_cost > 0 and batt_interval_km > 0 and annual_km > 0:
        batt_repl_cost = batt_cost * (annual_km / batt_interval_km)

    annual_cost = energy_cost + annual_maint + financing_cost + batt_repl_cost + other_fixed
    cost_per_km = annual_cost / annual_km if annual_km > 0 else float("inf")

    return ScenarioResult(
        name=name,
        annual_km=annual_km,
        annual_cost=annual_cost,
        cost_per_km=cost_per_km,
        annual_energy_cost=energy_cost,
        annual_maintenance_cost=annual_maint,
        annual_financing_cost=financing_cost,
        annual_batt_repl_cost=batt_repl_cost,
        annual_other_fixed=other_fixed,
        energy_kwh_per_km=kwh_per_km,
        fuel_l_per_km=fuel_l_per_km,
        cycle_km=cycle_km,
    )
def build_default_params(
    inputs: Mapping[str, Any],
    defaults_by_segment: Mapping[str, Mapping[str, Any]],
    segment: str,
) -> Dict[str, Dict[str, Any]]:
    seg = defaults_by_segment.get(segment, {})
    common = dict(seg.get("common", {}))
    scenarios = {}
    for s in ("ice", "conversion", "bev"):
        scenarios[s] = dict(common)
        scenarios[s].update(seg.get(s, {}))
    u = dict(inputs or {})
    for s in ("ice", "conversion", "bev"):
        prefix = s + "_"
        for k, v in list(u.items()):
            if k.startswith(prefix):
                scenarios[s][k[len(prefix) :]] = v
    return scenarios


def compare_ice_conversion_bev(
    cycle: Any,
    inputs: Mapping[str, Any],
    scenario_params: Mapping[str, Mapping[str, Any]],
    toggles: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    out = {}
    for key, nm in (("ice", "ICE"), ("conversion", "Conversion"), ("bev", "BEV")):
        res = compute_scenario(nm, cycle, inputs, scenario_params.get(key, {}), toggles=toggles)
        out[key] = res.as_dict()
    out["delta_cost_per_km"] = {
        "conversion_minus_ice": out["conversion"]["cost_per_km"] - out["ice"]["cost_per_km"],
        "bev_minus_ice": out["bev"]["cost_per_km"] - out["ice"]["cost_per_km"],
        "bev_minus_conversion": out["bev"]["cost_per_km"] - out["conversion"]["cost_per_km"],
    }
    return out
