"""Blessed end-to-end pipeline.

This module is the single supported, stable implementation used by tests and CLI.
It is intentionally lightweight and dependency-free.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json
import math
__all__ = [
    "PipelineConfig",
    "PipelineResult",
    "Pipeline",
    "run_pipeline",
    "load_input",
]
@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Configuration for the blessed pipeline.

    artifact_dir: if set, results are written to artifact_dir / "result.json".
    raise_on_empty: if True, empty inputs raise ValueError.
    """

    artifact_dir: str | Path | None = None
    raise_on_empty: bool = True
@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Structured output for pipeline consumers and tests."""

    count: int
    mean: float
    stdev: float
    min: float
    max: float
    normalized: list[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
def load_input(value: Any) -> list[float]:
    """Load numeric input from common forms.

    Accepted:
      - Sequence/iterable of numbers (excluding strings/bytes)
      - Mapping containing key "data" with such a sequence
      - Path/str to a JSON file containing either of the above
      - JSON string containing either of the above

    Returns a list[float]. Raises ValueError/TypeError on invalid input.
    """
    if value is None:
        return []
    if isinstance(value, (str, Path)):
        s = str(value)
        p = Path(s)
        if p.suffix.lower() == ".json" and p.exists():
            obj = json.loads(p.read_text(encoding="utf-8"))
            return load_input(obj)
        # Try JSON string
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            raise ValueError("String input must be a path to a .json file or valid JSON.") from None
        return load_input(obj)
    if isinstance(value, Mapping):
        if "data" not in value:
            raise ValueError('Mapping input must contain key "data".')
        return load_input(value["data"])
    if isinstance(value, (bytes, bytearray)):
        raise TypeError("Binary input is not supported.")
    if isinstance(value, Iterable):
        out: list[float] = []
        for x in value:  # type: ignore[assignment]
            if isinstance(x, (bool, str, bytes, bytearray, dict, list, tuple, set)):
                # Allow nested sequences only via mapping/json; keep runtime predictable
                pass
            try:
                fx = float(x)
            except Exception as e:
                raise TypeError(f"All items must be numeric; got {type(x).__name__}.") from e
            if math.isnan(fx) or math.isinf(fx):
                raise ValueError("NaN/Inf values are not supported.")
            out.append(fx)
        return out
    raise TypeError(f"Unsupported input type: {type(value).__name__}.")
def _stats(data: Sequence[float]) -> tuple[float, float, float, float]:
    mn = min(data)
    mx = max(data)
    mean = sum(data) / len(data)
    if len(data) < 2:
        return mean, 0.0, mn, mx
    var = sum((x - mean) ** 2 for x in data) / (len(data) - 1)
    return mean, math.sqrt(var), mn, mx
def _normalize(data: Sequence[float], mn: float, mx: float) -> list[float]:
    if mx == mn:
        return [0.0 for _ in data]
    scale = mx - mn
    return [(x - mn) / scale for x in data]
class Pipeline:
    """Blessed pipeline runner."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def run(self, input_value: Any = None) -> PipelineResult:
        data = load_input(input_value)
        if not data and self.config.raise_on_empty:
            raise ValueError("Input data is empty.")
        if not data:
            result = PipelineResult(count=0, mean=0.0, stdev=0.0, min=0.0, max=0.0, normalized=[])
            self._maybe_write_artifact(result)
            return result

        mean, stdev, mn, mx = _stats(data)
        normalized = _normalize(data, mn, mx)
        result = PipelineResult(count=len(data), mean=mean, stdev=stdev, min=mn, max=mx, normalized=normalized)
        self._maybe_write_artifact(result)
        return result

    def _maybe_write_artifact(self, result: PipelineResult) -> None:
        if self.config.artifact_dir is None:
            return
        out_dir = Path(self.config.artifact_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "result.json"
        out_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
def run_pipeline(input_value: Any = None, config: PipelineConfig | None = None) -> PipelineResult:
    """Convenience function used by tests/CLI."""
    return Pipeline(config=config).run(input_value)
