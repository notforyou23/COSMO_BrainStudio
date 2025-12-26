import argparse
import importlib
import inspect
import os
import random
from pathlib import Path


def _set_global_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    try:
        import numpy as np  # type: ignore
        np.random.seed(seed)
    except Exception:
        pass


def _resolve_runner():
    candidates = [
        ("src.pipeline", "run_pipeline"),
        ("src.pipeline", "main"),
        ("src.main", "run_pipeline"),
        ("src.main", "main"),
        ("pipeline", "run_pipeline"),
        ("pipeline", "main"),
        ("main", "run_pipeline"),
        ("main", "main"),
    ]
    for mod_name, fn_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            return fn
    raise SystemExit(
        "Could not locate pipeline runner. Expected one of: "
        + ", ".join(f"{m}.{f}" for m, f in candidates)
    )


def _call_runner(runner, *, seed: int, outputs_dir: Path, extra_args=None):
    extra_args = list(extra_args or [])
    _set_global_seed(seed)
    sig = None
    try:
        sig = inspect.signature(runner)
    except Exception:
        sig = None

    kwargs = {}
    if sig is not None:
        params = sig.parameters
        if "seed" in params:
            kwargs["seed"] = seed
        if "outputs_dir" in params:
            kwargs["outputs_dir"] = str(outputs_dir)
        elif "output_dir" in params:
            kwargs["output_dir"] = str(outputs_dir)
        elif "out_dir" in params:
            kwargs["out_dir"] = str(outputs_dir)
        if "args" in params:
            kwargs["args"] = extra_args
        elif "argv" in params:
            kwargs["argv"] = extra_args

    try:
        return runner(**kwargs)
    except TypeError:
        try:
            return runner(extra_args)
        except TypeError:
            return runner()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="entrypoint")
    ap.add_argument("--outputs-dir", default="outputs")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument(
        "--determinism",
        action="store_true",
        help="Run pipeline twice with a fixed seed and write outputs/determinism_report.json",
    )
    ns, extra = ap.parse_known_args(argv)

    outputs_dir = Path(ns.outputs_dir)
    runner = _resolve_runner()

    if ns.determinism:
        fixed_seed = 1337 if ns.seed is None else int(ns.seed)
        from src.determinism import run_determinism  # imported only when needed

        report_path = run_determinism(
            runner=runner,
            seed=fixed_seed,
            outputs_dir=outputs_dir,
            extra_args=extra,
        )
        print(str(report_path))
        return 0

    seed = 0 if ns.seed is None else int(ns.seed)
    _call_runner(runner, seed=seed, outputs_dir=outputs_dir, extra_args=extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
