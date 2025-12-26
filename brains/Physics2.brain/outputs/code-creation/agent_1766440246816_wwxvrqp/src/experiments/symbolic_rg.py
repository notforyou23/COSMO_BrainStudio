"""Symbolic renormalization group (RG) toy experiment.

This module provides a tiny, syntax-valid experiment implementation for the
benchmark pipeline. It is intentionally lightweight (no heavy symbolic algebra
dependencies) while still behaving like a symbolic RG flow: it evolves a small
set of coupling "expressions" across coarse-graining steps in a deterministic
way.

Public API:
- ExperimentConfig
- default_config()
- run_experiment(config=None)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union
@dataclass(frozen=True)
class ExperimentConfig:
    """Configuration for the symbolic RG toy model."""

    # Couplings are keyed by simple monomial names (e.g. "phi^2", "phi^4").
    couplings: Dict[str, float] = None  # populated by default_config()
    steps: int = 4
    scale_factor: float = 2.0
    mixing_strength: float = 0.05  # small deterministic "operator mixing"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # dataclasses would include None as couplings if user constructs directly
        if d["couplings"] is None:
            d["couplings"] = {}
        return d
def default_config() -> ExperimentConfig:
    """Return a deterministic default configuration."""
    return ExperimentConfig(
        couplings={"phi^2": 1.0, "phi^4": 0.1},
        steps=4,
        scale_factor=2.0,
        mixing_strength=0.05,
    )
_MONOMIAL_RE = re.compile(r"^(?P<field>[a-zA-Z_][a-zA-Z0-9_]*)\^(?P<power>[0-9]+)$")


def _parse_monomial(name: str) -> Tuple[str, int]:
    """Parse a monomial key like 'phi^4' into ('phi', 4)."""
    m = _MONOMIAL_RE.match(name)
    if not m:
        raise ValueError(f"Invalid coupling key: {name!r} (expected like 'phi^4')")
    return m.group("field"), int(m.group("power"))
def _validate(cfg: ExperimentConfig) -> None:
    if cfg.couplings is None:
        raise ValueError("couplings must be provided (or use default_config())")
    if cfg.steps < 0:
        raise ValueError("steps must be >= 0")
    if cfg.scale_factor <= 1.0:
        raise ValueError("scale_factor must be > 1")
    if cfg.mixing_strength < 0.0:
        raise ValueError("mixing_strength must be >= 0")
    for k, v in cfg.couplings.items():
        _parse_monomial(k)
        if not isinstance(v, (int, float)):
            raise TypeError(f"Coupling {k!r} must be numeric, got {type(v).__name__}")
def _rg_step(
    couplings: Mapping[str, float], scale: float, mix: float
) -> Dict[str, float]:
    """Perform a single toy RG step.

    Rule (toy, deterministic):
    - A monomial 'phi^n' rescales by scale**(2-n).
    - A higher operator feeds into a lower one via a small mixing term:
      phi^(n+2) contributes mix * coeff to phi^n.
    """
    out: Dict[str, float] = {}
    parsed: List[Tuple[str, int, float]] = []
    for name, coeff in couplings.items():
        field, power = _parse_monomial(name)
        parsed.append((field, power, float(coeff)))

    for field, power, coeff in parsed:
        # naive engineering dimension in 2D: dim(phi^n) ~ n, so exponent (2-n)
        rescaled = coeff * (scale ** (2 - power))
        key = f"{field}^{power}"
        out[key] = out.get(key, 0.0) + rescaled

    # operator mixing: phi^(p) feeds into phi^(p-2) for p>=4
    for field, power, coeff in parsed:
        if power >= 4:
            lower = f"{field}^{power-2}"
            out[lower] = out.get(lower, 0.0) + mix * coeff

    # small cleanup: drop near-zero entries for stable JSON outputs
    out = {k: float(v) for k, v in out.items() if abs(v) > 1e-15}
    return dict(sorted(out.items()))
def run_experiment(
    config: Optional[Union[ExperimentConfig, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Run the symbolic RG flow and return JSON-serializable results."""
    if config is None:
        cfg = default_config()
    elif isinstance(config, ExperimentConfig):
        cfg = config
    elif isinstance(config, dict):
        cfg = ExperimentConfig(**config)
    else:
        raise TypeError("config must be None, ExperimentConfig, or dict")

    _validate(cfg)

    history: List[Dict[str, float]] = [dict(sorted({k: float(v) for k, v in cfg.couplings.items()}.items()))]
    for _ in range(cfg.steps):
        history.append(_rg_step(history[-1], cfg.scale_factor, cfg.mixing_strength))

    # Simple "fixed point" heuristic: L2 norm of delta between last two steps.
    if len(history) >= 2:
        keys = sorted(set(history[-1]) | set(history[-2]))
        delta2 = 0.0
        for k in keys:
            delta = history[-1].get(k, 0.0) - history[-2].get(k, 0.0)
            delta2 += delta * delta
        flow_norm = delta2 ** 0.5
    else:
        flow_norm = 0.0

    return {
        "experiment": "symbolic_rg",
        "config": cfg.to_dict(),
        "observables": {
            "couplings_by_step": history,
            "final_couplings": history[-1] if history else {},
            "flow_norm": flow_norm,
            "n_steps": cfg.steps,
        },
    }
__all__ = ["ExperimentConfig", "default_config", "run_experiment"]
