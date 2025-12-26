"""Experiment sweep orchestration.

This module provides small, dependency-light utilities to:
- build parameter grids
- run a sweep with a user-supplied experiment function
- optionally persist results and hand them to plotting helpers

The I/O and plotting integrations are optional; if sibling modules are present,
they will be used, otherwise lightweight fallbacks are applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union
import json
import traceback
Params = Mapping[str, Sequence[Any]]
Config = Dict[str, Any]
Record = Dict[str, Any]
Runner = Callable[[Config], Any]
OnResult = Callable[[int, Config, Any, Optional[BaseException]], None]
def expand_grid(params: Params) -> List[Config]:
    """Return a deterministic full-factorial grid as a list of configs."""
    keys = list(params.keys())
    values: List[Sequence[Any]] = []
    for k in keys:
        v = params[k]
        if not isinstance(v, Sequence) or isinstance(v, (str, bytes)):
            raise TypeError(f"Parameter '{k}' must be a sequence of values.")
        if len(v) == 0:
            raise ValueError(f"Parameter '{k}' has no values.")
        values.append(list(v))
    return [dict(zip(keys, combo)) for combo in product(*values)]
def iter_grid(params: Params) -> Iterable[Config]:
    """Yield configs lazily for a full-factorial sweep."""
    keys = list(params.keys())
    values: List[Sequence[Any]] = []
    for k in keys:
        v = params[k]
        if not isinstance(v, Sequence) or isinstance(v, (str, bytes)):
            raise TypeError(f"Parameter '{k}' must be a sequence of values.")
        if len(v) == 0:
            raise ValueError(f"Parameter '{k}' has no values.")
        values.append(list(v))
    for combo in product(*values):
        yield dict(zip(keys, combo))
@dataclass(frozen=True)
class SweepRun:
    """Container for sweep outputs."""

    records: List[Record]
    errors: int = 0

    def to_jsonl(self, path: Union[str, Path]) -> Path:
        """Write records as JSONL. Uses experiments.io if available."""
        p = Path(path)
        try:
            from .io import write_jsonl  # type: ignore
        except Exception:
            write_jsonl = None
        if write_jsonl is not None:
            write_jsonl(p, self.records)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("w", encoding="utf-8") as f:
                for r in self.records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return p
def run_sweep(
    runner: Runner,
    grid: Union[Iterable[Config], Params],
    *,
    base_config: Optional[Mapping[str, Any]] = None,
    on_result: Optional[OnResult] = None,
    raise_errors: bool = False,
) -> SweepRun:
    """Run an experiment function over a grid.

    Args:
        runner: Callable that accepts a config dict and returns either:
            - a mapping (merged into the record), or
            - any other value (stored under 'result').
        grid: Either an iterable of configs or a Params mapping to be expanded.
        base_config: Extra config values merged into each config (base < grid).
        on_result: Optional callback (i, config, output, exception).
        raise_errors: If True, raise the first encountered exception.

    Returns:
        SweepRun with a list of records (one per config).
    """
    configs = expand_grid(grid) if isinstance(grid, Mapping) else list(grid)
    base = dict(base_config or {})
    records: List[Record] = []
    errors = 0

    for i, cfg in enumerate(configs):
        config = {**base, **cfg}
        out: Any = None
        err: Optional[BaseException] = None
        try:
            out = runner(dict(config))
        except BaseException as e:  # capture KeyboardInterrupt too if desired
            err = e
            errors += 1
            if raise_errors:
                raise
        rec: Record = dict(config)
        if err is not None:
            rec["error"] = type(err).__name__
            rec["traceback"] = "".join(traceback.format_exception(type(err), err, err.__traceback__))
        else:
            if isinstance(out, Mapping):
                rec.update(out)  # type: ignore[arg-type]
            else:
                rec["result"] = out
        records.append(rec)
        if on_result is not None:
            on_result(i, config, out, err)
    return SweepRun(records=records, errors=errors)
def load_records(path: Union[str, Path]) -> List[Record]:
    """Load sweep records from JSONL. Uses experiments.io if available."""
    p = Path(path)
    try:
        from .io import read_jsonl  # type: ignore
    except Exception:
        read_jsonl = None
    if read_jsonl is not None:
        return list(read_jsonl(p))
    records: List[Record] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
def maybe_plot(records: Sequence[Record], *args: Any, **kwargs: Any) -> Any:
    """Optional plotting hook; delegates to experiments.plotting if present."""
    try:
        from .plotting import plot_records  # type: ignore
    except Exception:
        plot_records = None
    if plot_records is None:
        raise RuntimeError("Plotting helpers are unavailable (experiments.plotting not importable).")
    return plot_records(records, *args, **kwargs)
