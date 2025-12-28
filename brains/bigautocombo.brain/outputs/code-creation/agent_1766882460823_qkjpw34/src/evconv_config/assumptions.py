"""Default segment assumptions and schema-validated override merging.

Segments: fleet, classic, specialty.
Designed for notebook ingestion: merge user CSV overrides onto defaults safely.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping, Tuple

Number = (int, float)


SEGMENTS = ("fleet", "classic", "specialty")


def default_assumptions() -> Dict[str, Dict[str, Any]]:
    """Return default assumptions by segment."""
    base = {
        "analysis": {"years": 8, "discount_rate": 0.08},
        "energy_prices": {"gasoline_usd_per_gal": 4.00, "diesel_usd_per_gal": 4.50, "electricity_usd_per_kwh": 0.18},
        "utilization": {"annual_miles": 12000, "payload_factor": 1.00},
        "financing": {"enabled": True, "apr": 0.08, "term_years": 5, "down_payment_frac": 0.10},
        "maintenance": {"ice_usd_per_mile": 0.12, "ev_usd_per_mile": 0.08},
        "tires": {"usd_per_mile": 0.02},
        "battery_replacement": {"enabled": True, "replacement_cost_usd_per_kwh": 140.0, "replacement_trigger_soh": 0.70},
    }
    fleet = deepcopy(base)
    fleet["analysis"].update({"years": 6, "discount_rate": 0.10})
    fleet["utilization"].update({"annual_miles": 28000})
    fleet["energy_prices"].update({"electricity_usd_per_kwh": 0.16})
    fleet["maintenance"].update({"ice_usd_per_mile": 0.14, "ev_usd_per_mile": 0.09})
    fleet["financing"].update({"apr": 0.09, "term_years": 4, "down_payment_frac": 0.05})

    classic = deepcopy(base)
    classic["analysis"].update({"years": 10, "discount_rate": 0.06})
    classic["utilization"].update({"annual_miles": 3000})
    classic["energy_prices"].update({"electricity_usd_per_kwh": 0.20})
    classic["maintenance"].update({"ice_usd_per_mile": 0.20, "ev_usd_per_mile": 0.10})
    classic["financing"].update({"enabled": False, "apr": 0.0, "term_years": 0, "down_payment_frac": 1.0})
    classic["battery_replacement"].update({"replacement_cost_usd_per_kwh": 180.0})

    specialty = deepcopy(base)
    specialty["analysis"].update({"years": 8, "discount_rate": 0.09})
    specialty["utilization"].update({"annual_miles": 15000, "payload_factor": 1.15})
    specialty["energy_prices"].update({"diesel_usd_per_gal": 4.80, "electricity_usd_per_kwh": 0.19})
    specialty["maintenance"].update({"ice_usd_per_mile": 0.16, "ev_usd_per_mile": 0.10})
    specialty["battery_replacement"].update({"replacement_cost_usd_per_kwh": 160.0})

    return {"fleet": fleet, "classic": classic, "specialty": specialty}


_SCHEMA: Dict[str, Dict[str, Any]] = {
    "analysis.years": {"type": int, "min": 1, "max": 25},
    "analysis.discount_rate": {"type": float, "min": 0.0, "max": 1.0},
    "energy_prices.gasoline_usd_per_gal": {"type": float, "min": 0.0},
    "energy_prices.diesel_usd_per_gal": {"type": float, "min": 0.0},
    "energy_prices.electricity_usd_per_kwh": {"type": float, "min": 0.0},
    "utilization.annual_miles": {"type": float, "min": 0.0},
    "utilization.payload_factor": {"type": float, "min": 0.0, "max": 3.0},
    "financing.enabled": {"type": bool},
    "financing.apr": {"type": float, "min": 0.0, "max": 1.0},
    "financing.term_years": {"type": int, "min": 0, "max": 15},
    "financing.down_payment_frac": {"type": float, "min": 0.0, "max": 1.0},
    "maintenance.ice_usd_per_mile": {"type": float, "min": 0.0},
    "maintenance.ev_usd_per_mile": {"type": float, "min": 0.0},
    "tires.usd_per_mile": {"type": float, "min": 0.0},
    "battery_replacement.enabled": {"type": bool},
    "battery_replacement.replacement_cost_usd_per_kwh": {"type": float, "min": 0.0},
    "battery_replacement.replacement_trigger_soh": {"type": float, "min": 0.0, "max": 1.0},
}


def schema() -> Dict[str, Dict[str, Any]]:
    """Return a copy of the override schema."""
    return deepcopy(_SCHEMA)


def _iter_paths(d: Mapping[str, Any], prefix: str = "") -> Iterable[Tuple[str, Any]]:
    for k, v in d.items():
        p = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, Mapping):
            yield from _iter_paths(v, p)
        else:
            yield p, v


def _set_path(d: Dict[str, Any], path: str, value: Any) -> None:
    keys = path.split(".")
    cur = d
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def _validate_value(path: str, value: Any, spec: Mapping[str, Any]) -> Any:
    t = spec.get("type")
    if t is bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in {"true", "false", "1", "0", "yes", "no"}:
            return value.strip().lower() in {"true", "1", "yes"}
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        raise TypeError(f"{path}: expected bool")
    if t in (int, float):
        if isinstance(value, bool):
            raise TypeError(f"{path}: expected number")
        if isinstance(value, str):
            value = value.strip()
            try:
                value = float(value) if t is float else int(float(value))
            except Exception as e:
                raise TypeError(f"{path}: could not parse number") from e
        if not isinstance(value, Number):
            raise TypeError(f"{path}: expected number")
        value = float(value) if t is float else int(value)
    elif t is not None and not isinstance(value, t):
        raise TypeError(f"{path}: expected {t.__name__}")
    if "choices" in spec and value not in set(spec["choices"]):
        raise ValueError(f"{path}: must be one of {spec['choices']}")
    if "min" in spec and value < spec["min"]:
        raise ValueError(f"{path}: must be >= {spec['min']}")
    if "max" in spec and value > spec["max"]:
        raise ValueError(f"{path}: must be <= {spec['max']}")
    return value


def merge_assumptions(segment: str, overrides: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Merge user overrides onto segment defaults with schema validation.

    Overrides may be nested dicts (matching defaults) or flat dotted-path keys.
    Unknown keys raise KeyError; type/range mismatches raise TypeError/ValueError.
    """
    if segment not in SEGMENTS:
        raise KeyError(f"Unknown segment '{segment}'. Choose from {SEGMENTS}")
    merged = deepcopy(default_assumptions()[segment])
    if not overrides:
        return merged

    flat: Dict[str, Any] = {}
    for k, v in overrides.items():
        if isinstance(v, Mapping):
            for p, pv in _iter_paths({k: v}):
                flat[p] = pv
        else:
            flat[str(k)] = v

    for path, value in flat.items():
        if path not in _SCHEMA:
            raise KeyError(f"Unknown override key '{path}'")
        coerced = _validate_value(path, value, _SCHEMA[path])
        _set_path(merged, path, coerced)

    if not merged["financing"]["enabled"]:
        merged["financing"]["apr"] = 0.0
        merged["financing"]["term_years"] = 0
        merged["financing"]["down_payment_frac"] = 1.0
    return merged
