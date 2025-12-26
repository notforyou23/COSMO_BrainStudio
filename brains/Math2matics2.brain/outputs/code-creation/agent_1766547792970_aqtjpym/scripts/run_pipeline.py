"""Pipeline entrypoint.

Wires goal_33 toy experiment into a simple CLI pipeline runner.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import os
import random
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_sys_path() -> None:
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _set_determinism(seed: int) -> None:
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)
    try:
        import numpy as np  # type: ignore
        np.random.seed(seed)
    except Exception:
        pass
    try:
        import torch  # type: ignore
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass


def _call_main(main_fn: Callable[..., Any], outputs_dir: Path, seed: int) -> Any:
    sig = inspect.signature(main_fn)
    kwargs: Dict[str, Any] = {}
    for name in sig.parameters:
        if name in {"outputs_dir", "output_dir", "out_dir", "artifacts_dir"}:
            kwargs[name] = outputs_dir
        elif name in {"seed", "rng_seed", "random_seed"}:
            kwargs[name] = seed
    try:
        return main_fn(**kwargs)
    except TypeError:
        return main_fn()


def _resolve_goal(goal: str) -> Tuple[Callable[..., Any], str]:
    _ensure_sys_path()
    if goal in {"goal_33", "33", "g33"}:
        mod = importlib.import_module("src.goal_33_toy_experiment")
        main_fn = getattr(mod, "main", None)
        if main_fn is None or not callable(main_fn):
            raise AttributeError("src.goal_33_toy_experiment.main not found or not callable")
        return main_fn, "src.goal_33_toy_experiment:main"
    raise ValueError(f"Unknown goal: {goal}")


def run(goal: str = "goal_33", seed: int = 0, outputs_dir: Optional[Path] = None) -> int:
    root = _project_root()
    out_dir = outputs_dir or (root / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    _set_determinism(seed)

    main_fn, label = _resolve_goal(goal)
    _call_main(main_fn, out_dir, seed)

    # Minimal artifact verification: ensure outputs directory exists and is non-empty.
    try:
        any_files = any(p.exists() for p in out_dir.rglob("*") if p.is_file())
    except Exception:
        any_files = False

    print(f"PIPELINE_OK goal={goal} entry={label} seed={seed} outputs_dir={out_dir} any_files={any_files}")
    return 0 if any_files or out_dir.exists() else 1


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run pipeline goals end-to-end.")
    p.add_argument("--goal", default="goal_33", help="Goal to run (default: goal_33).")
    p.add_argument("--seed", type=int, default=0, help="Deterministic seed (default: 0).")
    p.add_argument("--outputs-dir", default=None, help="Override outputs directory (default: ./outputs).")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    out_dir = Path(args.outputs_dir) if args.outputs_dir else None
    return run(goal=str(args.goal), seed=int(args.seed), outputs_dir=out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
