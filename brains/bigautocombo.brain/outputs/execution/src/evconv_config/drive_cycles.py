"""Preloaded standard drive-cycle proxies and helpers.

Cycles are lightweight, synthetic time-speed profiles intended for comparative
analysis (ICE vs conversion vs BEV), not regulatory certification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Literal, Tuple

import numpy as np


@dataclass(frozen=True)
class DriveCycle:
    name: str
    time_s: np.ndarray
    speed_mps: np.ndarray
    meta: dict

    def duration_s(self) -> float:
        return float(self.time_s[-1] - self.time_s[0])

    def distance_m(self) -> float:
        # trapezoidal integral of speed over time
        return float(np.trapz(self.speed_mps, self.time_s))

    def mean_speed_mps(self) -> float:
        d = self.distance_m()
        t = self.duration_s()
        return d / t if t > 0 else 0.0


def _as_cycle(name: str, t: Iterable[float], v: Iterable[float], **meta) -> DriveCycle:
    t = np.asarray(t, dtype=float)
    v = np.asarray(v, dtype=float)
    if t.ndim != 1 or v.ndim != 1 or t.size != v.size:
        raise ValueError("time_s and speed_mps must be 1D arrays of equal length")
    if np.any(np.diff(t) <= 0):
        raise ValueError("time_s must be strictly increasing")
    if np.any(v < 0):
        raise ValueError("speed_mps must be non-negative")
    return DriveCycle(name=name, time_s=t, speed_mps=v, meta=dict(meta))
def _make_piecewise(t_end: int, knots: Iterable[Tuple[float, float]], dt: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """Create a 1 Hz-ish profile from (time_s, speed_mps) knots using linear interpolation."""
    t = np.arange(0.0, float(t_end) + 1e-9, float(dt))
    kt, kv = zip(*knots)
    kt = np.asarray(kt, dtype=float)
    kv = np.asarray(kv, dtype=float)
    if kt[0] != 0.0:
        raise ValueError("First knot time must be 0")
    if float(kt[-1]) != float(t_end):
        raise ValueError("Last knot time must equal t_end")
    v = np.interp(t, kt, kv)
    v[v < 0] = 0.0
    return t, v


def _build_cycles() -> Dict[str, DriveCycle]:
    # Urban / last-mile: low average speed, frequent stops, small peaks (~35 mph).
    t, v = _make_piecewise(
        1800,
        [
            (0, 0), (20, 0), (60, 8), (120, 0), (180, 10), (240, 0),
            (300, 12), (360, 0), (450, 9), (510, 0), (600, 11), (660, 0),
            (780, 13), (840, 0), (960, 12), (1020, 0), (1140, 14), (1200, 0),
            (1320, 12), (1380, 0), (1500, 10), (1560, 0), (1680, 8), (1740, 0),
            (1800, 0),
        ],
        dt=1.0,
    )
    urban = _as_cycle("urban_last_mile", t, v, kind="proxy", typical_use="last-mile/urban", dt_s=1.0)

    # Mixed: moderate average speed with some arterial segments (~55 mph).
    t, v = _make_piecewise(
        2400,
        [
            (0, 0), (30, 0), (120, 12), (180, 0),
            (330, 18), (420, 10), (480, 0),
            (720, 22), (780, 15), (840, 0),
            (1080, 25), (1140, 18), (1200, 10),
            (1380, 0),
            (1560, 28), (1740, 24), (1860, 16),
            (1980, 0),
            (2100, 20), (2220, 12), (2310, 0),
            (2400, 0),
        ],
        dt=1.0,
    )
    mixed = _as_cycle("mixed", t, v, kind="proxy", typical_use="mixed/commute", dt_s=1.0)

    # Highway: mostly steady cruise with a couple ramps/speed changes (~70 mph).
    t, v = _make_piecewise(
        1800,
        [
            (0, 0), (40, 0), (120, 20), (180, 27),
            (240, 30), (360, 31), (720, 31),
            (780, 28), (840, 31), (1200, 31),
            (1320, 29), (1380, 31), (1620, 31),
            (1710, 20), (1760, 10), (1800, 0),
        ],
        dt=1.0,
    )
    highway = _as_cycle("highway", t, v, kind="proxy", typical_use="highway", dt_s=1.0)

    return {c.name: c for c in (urban, mixed, highway)}


CYCLES: Dict[str, DriveCycle] = _build_cycles()
def list_cycles() -> Tuple[str, ...]:
    """Return available cycle names."""
    return tuple(sorted(CYCLES.keys()))


def get_cycle(name: str) -> DriveCycle:
    """Fetch a cycle by name (case-insensitive, hyphens/spaces normalized)."""
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in CYCLES:
        raise KeyError(f"Unknown cycle '{name}'. Available: {', '.join(list_cycles())}")
    return CYCLES[key]


def resample_cycle(
    cycle: DriveCycle,
    dt_s: float = 1.0,
    method: Literal["linear", "previous"] = "linear",
) -> DriveCycle:
    """Resample a cycle to uniform timestep dt_s.

    linear: linear interpolation
    previous: zero-order hold (useful for step-like profiles)
    """
    if dt_s <= 0:
        raise ValueError("dt_s must be > 0")
    t0, t1 = float(cycle.time_s[0]), float(cycle.time_s[-1])
    t_new = np.arange(t0, t1 + 1e-9, float(dt_s))
    if method == "linear":
        v_new = np.interp(t_new, cycle.time_s, cycle.speed_mps)
    elif method == "previous":
        idx = np.searchsorted(cycle.time_s, t_new, side="right") - 1
        idx = np.clip(idx, 0, cycle.speed_mps.size - 1)
        v_new = cycle.speed_mps[idx]
    else:
        raise ValueError("method must be 'linear' or 'previous'")
    v_new = np.maximum(v_new, 0.0)
    meta = dict(cycle.meta)
    meta.update(resampled_from=cycle.name, dt_s=float(dt_s), resample_method=method)
    return DriveCycle(name=cycle.name, time_s=t_new, speed_mps=v_new, meta=meta)


def cycle_summary(name: str) -> dict:
    c = get_cycle(name)
    return {
        "name": c.name,
        "duration_s": c.duration_s(),
        "distance_km": c.distance_m() / 1000.0,
        "mean_speed_kph": c.mean_speed_mps() * 3.6,
        "dt_s": float(np.median(np.diff(c.time_s))),
        **{f"meta_{k}": v for k, v in (c.meta or {}).items()},
    }
