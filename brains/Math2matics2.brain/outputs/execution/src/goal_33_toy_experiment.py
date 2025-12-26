from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


DEFAULT_OUT_PATH = Path("outputs") / "goal_33_results.json"


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int = 0
    n: int = 256
    mean: float = 0.0
    std: float = 1.0


def _box_muller(rng: random.Random) -> float:
    # Deterministic normal(0,1) from U(0,1) using Box-Muller.
    # Avoid log(0) by clamping u1 away from 0.
    u1 = max(rng.random(), 1e-12)
    u2 = rng.random()
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def run_experiment(config: ExperimentConfig) -> Dict[str, Any]:
    rng = random.Random(int(config.seed))
    xs = [(config.mean + config.std * _box_muller(rng)) for _ in range(int(config.n))]

    n = len(xs)
    m = sum(xs) / n if n else 0.0
    var = (sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    s = math.sqrt(var)

    def r6(v: float) -> float:
        # Stable numeric formatting: round to 6 decimals.
        return float(f"{v:.6f}")

    results: Dict[str, Any] = {
        "goal_id": 33,
        "seed": int(config.seed),
        "n": int(config.n),
        "params": {"mean": r6(float(config.mean)), "std": r6(float(config.std))},
        "metrics": {
            "mean": r6(m),
            "std": r6(s),
            "min": r6(min(xs) if xs else 0.0),
            "max": r6(max(xs) if xs else 0.0),
        },
    }
    return results


def write_results(results: Dict[str, Any], out_path: Path = DEFAULT_OUT_PATH) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(results, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    out_path.write_text(payload + "\n", encoding="utf-8")
    return out_path


def run_and_write(seed: int = 0, n: int = 256, mean: float = 0.0, std: float = 1.0, out_path: Path = DEFAULT_OUT_PATH) -> Dict[str, Any]:
    results = run_experiment(ExperimentConfig(seed=int(seed), n=int(n), mean=float(mean), std=float(std)))
    write_results(results, out_path=out_path)
    return results


def _assert_stable_artifact(path: Path) -> None:
    txt = Path(path).read_text(encoding="utf-8")
    obj = json.loads(txt)
    expected_top = ["goal_id", "metrics", "n", "params", "seed"]
    if sorted(obj.keys()) != expected_top:
        raise AssertionError(f"Unexpected top-level keys: {sorted(obj.keys())} != {expected_top}")

    metrics = obj["metrics"]
    params = obj["params"]
    for k in ["mean", "std", "min", "max"]:
        v = metrics[k]
        if not isinstance(v, (int, float)):
            raise AssertionError(f"metrics.{k} not numeric: {type(v)}")
        if f"{float(v):.6f}" != str(f"{float(v):.6f}"):
            raise AssertionError(f"metrics.{k} not 6-decimal stable")
    for k in ["mean", "std"]:
        v = params[k]
        if not isinstance(v, (int, float)):
            raise AssertionError(f"params.{k} not numeric: {type(v)}")
def smoke_test(seed: int = 123, out_path: Path = DEFAULT_OUT_PATH) -> Path:
    out_path = Path(out_path)
    run_and_write(seed=seed, out_path=out_path)
    if not out_path.exists():
        raise AssertionError(f"Expected artifact not created: {out_path}")
    _assert_stable_artifact(out_path)
    return out_path


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Goal 33 deterministic toy experiment (seedable) that writes a stable JSON artifact.")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n", type=int, default=256)
    p.add_argument("--mean", type=float, default=0.0)
    p.add_argument("--std", type=float, default=1.0)
    p.add_argument("--out", type=str, default=str(DEFAULT_OUT_PATH))
    p.add_argument("--smoke-test", action="store_true", help="Run a minimal deterministic smoke test and exit nonzero on failure.")
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    out_path = Path(args.out)
    if args.smoke_test:
        smoke_test(seed=int(args.seed), out_path=out_path)
        print(str(out_path))
        return 0

    results = run_and_write(seed=int(args.seed), n=int(args.n), mean=float(args.mean), std=float(args.std), out_path=out_path)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
