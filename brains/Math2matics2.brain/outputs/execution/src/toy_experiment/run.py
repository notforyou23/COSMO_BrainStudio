from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import json
import math
import random
from typing import Any, Dict, List, Optional, Union


DEFAULT_SEED = 123456
DEFAULT_N = 100
DEFAULT_OUTPUT_RELATIVE = Path("outputs/toy_experiment/results.json")


@dataclass(frozen=True)
class ToyExperimentResults:
    schema_version: int
    seed: int
    n: int
    distribution: str
    mean: float
    stddev: float
    min: float
    max: float
    samples: List[float]


def _project_root() -> Path:
    # .../src/toy_experiment/run.py -> parents[2] == project root
    return Path(__file__).resolve().parents[2]


def _default_output_path() -> Path:
    return _project_root() / DEFAULT_OUTPUT_RELATIVE


def run_toy_experiment(
    *,
    seed: int = DEFAULT_SEED,
    n: int = DEFAULT_N,
    output_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    if n <= 0:
        raise ValueError("n must be a positive integer")

    rng = random.Random(int(seed))
    samples = [rng.random() for _ in range(int(n))]

    mean = sum(samples) / n
    var = sum((x - mean) ** 2 for x in samples) / n
    stddev = math.sqrt(var)

    results = ToyExperimentResults(
        schema_version=1,
        seed=int(seed),
        n=int(n),
        distribution="uniform_0_1",
        mean=float(mean),
        stddev=float(stddev),
        min=float(min(samples)),
        max=float(max(samples)),
        samples=[float(x) for x in samples],
    )

    out_path = Path(output_path) if output_path is not None else _default_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(asdict(results), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return asdict(results)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic toy experiment and write a JSON results artifact.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic seed (default: %(default)s)")
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="Number of samples (default: %(default)s)")
    parser.add_argument(
        "--output",
        type=str,
        default=str(_default_output_path()),
        help="Output JSON path (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    run_toy_experiment(seed=args.seed, n=args.n, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
