from __future__ import annotations

import argparse, json, sys, time
from dataclasses import asdict, is_dataclass
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
EXPDIR = ROOT / "src" / "experiments"
DEFAULT_RUNS = ROOT / "runs"


def _load_module(file: Path):
    name = f"_exp_{file.stem}"
    loader = SourceFileLoader(name, str(file))
    spec = spec_from_loader(name, loader)
    mod = module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _coerce(v: str) -> Any:
    for f in (json.loads,):
        try:
            return f(v)
        except Exception:
            pass
    if v.lower() in {"true", "false"}: return v.lower() == "true"
    try: return int(v)
    except Exception: pass
    try: return float(v)
    except Exception: pass
    return v


def _parse_params(items: Optional[list[str]], json_str: Optional[str]) -> Dict[str, Any]:
    p: Dict[str, Any] = {}
    if json_str:
        obj = json.loads(json_str)
        if not isinstance(obj, dict): raise SystemExit("--params-json must be a JSON object")
        p.update(obj)
    for it in items or []:
        if "=" not in it: raise SystemExit(f"Bad --param {it!r}; expected k=v")
        k, v = it.split("=", 1)
        p[k] = _coerce(v)
    return p


def _ensure_dir(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    return d


def _jsonable(x: Any) -> Any:
    if is_dataclass(x): return asdict(x)
    if isinstance(x, Path): return str(x)
    return x


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=_jsonable) + "\n", encoding="utf-8")


def _call(fn: Callable[..., Any], params: Mapping[str, Any], seed: Optional[int], out_dir: Path) -> Any:
    kw = {"params": dict(params), "seed": seed, "out_dir": out_dir}
    # gracefully drop unsupported keywords
    import inspect
    sig = inspect.signature(fn)
    out = {}
    for k, v in kw.items():
        if k in sig.parameters: out[k] = v
    # if function doesn't take "params", splat dict
    if "params" not in sig.parameters:
        out.pop("params", None)
        return fn(**dict(params), **out)
    return fn(**out)
def _experiments() -> Dict[str, Tuple[str, str, str]]:
    # id -> (filename, callable, summary)
    return {
        "random_circuit_entanglement": ("random_circuit_entanglement.py", "run_experiment", "Entanglement growth in 1D random unitary circuit"),
        "toy_lattice_decoherence": ("toy_lattice_decoherence.py", "simulate", "Decoherence diagnostics for a system qubit coupled to an env chain"),
        "symbolic_rg_flow": ("symbolic_rg_flow.py", "symbolic_derivation", "Symbolic + numeric RG flow toy model with example plots"),
    }


def list_cmd(tag: Optional[str] = None) -> int:
    exps = _experiments()
    for k, (_, _, s) in sorted(exps.items()):
        if tag and tag not in k:  # lightweight filter without extra metadata
            continue
        print(f"{k}\t{s}")
    return 0


def run_cmd(exp_id: str, params: Dict[str, Any], seed: Optional[int], out_root: Path, run_id: Optional[str]) -> int:
    exps = _experiments()
    if exp_id not in exps:
        raise SystemExit(f"Unknown experiment {exp_id!r}. Use: list")
    fname, fn_name, _ = exps[exp_id]
    mod = _load_module(EXPDIR / fname)
    fn = getattr(mod, fn_name)
    rid = run_id or f"{exp_id}_{int(time.time())}"
    out_dir = _ensure_dir(out_root / rid)
    res = _call(fn, params, seed, out_dir)
    payload = {"experiment": exp_id, "params": params, "seed": seed, "result": res}
    _write_json(out_dir / "result.json", payload)
    print(str(out_dir))
    return 0


def examples_cmd(out_root: Path, seed: int) -> int:
    # Run all experiments with their internal defaults; intended for reproducible smoke outputs.
    for exp_id in sorted(_experiments()):
        run_cmd(exp_id, {}, seed, out_root, run_id=f"example_{exp_id}")
    return 0
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="toyq", description="Reproducible toy numerical/symbolic experiments runner")
    p.add_argument("--runs", type=Path, default=DEFAULT_RUNS, help="Root directory for run outputs")
    sub = p.add_subparsers(dest="cmd", required=True)

    lp = sub.add_parser("list", help="List available experiments")
    lp.add_argument("--filter", default=None, help="Substring filter on experiment id")

    rp = sub.add_parser("run", help="Run a single experiment")
    rp.add_argument("experiment", help="Experiment id (see: list)")
    rp.add_argument("--seed", type=int, default=None, help="Random seed (if experiment supports it)")
    rp.add_argument("--run-id", default=None, help="Output subdirectory name (default: <id>_<timestamp>)")
    rp.add_argument("--params-json", default=None, help="JSON object of parameters")
    rp.add_argument("--param", action="append", default=None, help="Parameter override, like --param n=8")

    ep = sub.add_parser("examples", help="Generate example plots/tables by running all experiments")
    ep.add_argument("--seed", type=int, default=0)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    out_root = _ensure_dir(args.runs)
    if args.cmd == "list":
        return list_cmd(args.filter)
    if args.cmd == "run":
        params = _parse_params(args.param, args.params_json)
        return run_cmd(args.experiment, params, args.seed, out_root, args.run_id)
    if args.cmd == "examples":
        return examples_cmd(out_root, args.seed)
    raise SystemExit("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
