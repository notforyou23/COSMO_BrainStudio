"""Command-line interface to run prototype experiments.

This CLI is intentionally lightweight: it standardizes seeding, output directories,
and writing a run manifest for reproducibility.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = PROJECT_ROOT / "outputs"
DEFAULT_EXPERIMENTS = {
    "ising": "src.experiments.toy_ising_emergent_classicality",
    "entanglement": "src.experiments.entanglement_graph_geometry",
}


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_params(params_json: Optional[str], params_file: Optional[str]) -> Dict[str, Any]:
    if params_json and params_file:
        raise SystemExit("Provide only one of --params-json or --params-file.")
    if params_file:
        return json.loads(Path(params_file).read_text(encoding="utf-8"))
    if params_json:
        return json.loads(params_json)
    return {}


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _resolve_experiment(name_or_module: str) -> str:
    return DEFAULT_EXPERIMENTS.get(name_or_module, name_or_module)


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np  # type: ignore

        np.random.seed(seed)
    except Exception:
        pass
def _write_manifest(outdir: Path, payload: Dict[str, Any]) -> Path:
    path = outdir / "manifest.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _call_experiment(module_name: str, *, outdir: Path, seed: int, params: Dict[str, Any]) -> Any:
    mod = importlib.import_module(module_name)
    if hasattr(mod, "run_cli"):
        # Preferred: run_cli(namespace) for maximal flexibility
        ns = argparse.Namespace(outdir=str(outdir), seed=seed, **params)
        return mod.run_cli(ns)
    if hasattr(mod, "run"):
        return mod.run(outdir=outdir, seed=seed, **params)
    if hasattr(mod, "main"):
        ns = argparse.Namespace(outdir=str(outdir), seed=seed, **params)
        return mod.main(ns)
    raise SystemExit(f"Experiment module '{module_name}' has no run/run_cli/main entry point.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="generated_script_1766430415667", add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    lp = sub.add_parser("list", help="List known experiment aliases.")
    lp.add_argument("--json", action="store_true", help="Print as JSON.")

    rp = sub.add_parser("run", help="Run an experiment by alias or module path.")
    rp.add_argument("experiment", help="Alias (e.g. 'ising') or module path (e.g. 'src.experiments.x').")
    rp.add_argument("--seed", type=int, default=0, help="Random seed (0 means auto).")
    rp.add_argument("--outdir", type=str, default=str(DEFAULT_OUTDIR), help="Output directory base.")
    rp.add_argument("--run-id", type=str, default="", help="Override run id (default: UTC timestamp).")
    rp.add_argument("--params-json", type=str, default=None, help="JSON dict of experiment parameters.")
    rp.add_argument("--params-file", type=str, default=None, help="Path to JSON file of parameters.")
    rp.add_argument("--no-manifest", action="store_true", help="Do not write manifest.json.")

    return p
def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "list":
        if args.json:
            print(json.dumps(DEFAULT_EXPERIMENTS, indent=2, sort_keys=True))
        else:
            for k, v in sorted(DEFAULT_EXPERIMENTS.items()):
                print(f"{k}\t{v}")
        return 0

    # run
    module_name = _resolve_experiment(args.experiment)
    seed = args.seed if args.seed != 0 else (abs(hash(_utc_run_id())) % (2**31 - 1))
    run_id = args.run_id or _utc_run_id()
    params = _read_params(args.params_json, args.params_file)

    base = Path(args.outdir).expanduser().resolve()
    outdir = _ensure_dir(base / module_name.split(".")[-1] / run_id)

    _seed_everything(seed)

    if not args.no_manifest:
        _write_manifest(
            outdir,
            {
                "run_id": run_id,
                "seed": seed,
                "experiment": args.experiment,
                "module": module_name,
                "params": params,
                "outdir": str(outdir),
                "timestamp_utc": run_id,
                "cwd": os.getcwd(),
            },
        )

    result = _call_experiment(module_name, outdir=outdir, seed=seed, params=params)

    # Keep console output short but informative for automation.
    print(str(outdir))
    if isinstance(result, dict) and result:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
