from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import os
import random
import time
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PipelineConfig:
    seed: int = 0
    output_dir: Path = Path("outputs")
    results_filename: str = "results.json"


def _stable_experiment(rng: random.Random) -> Dict[str, Any]:
    values = [rng.random() for _ in range(5)]
    ints = [rng.randint(0, 100) for _ in range(5)]
    return {
        "values": values,
        "ints": ints,
        "summary": {
            "values_sum": sum(values),
            "ints_sum": sum(ints),
        },
    }


def run_pipeline(seed: int = 0, output_dir: Optional[os.PathLike[str] | str] = None) -> Dict[str, Any]:
    cfg = PipelineConfig(seed=int(seed), output_dir=Path(output_dir) if output_dir is not None else Path("outputs"))
    rng = random.Random(cfg.seed)

    results: Dict[str, Any] = {
        "schema_version": 1,
        "seed": cfg.seed,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(0)),
        "experiment": _stable_experiment(rng),
    }

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg.output_dir / cfg.results_filename

    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(out_path)

    return results


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Reproducible JSON-producing experiment pipeline.")
    parser.add_argument("--seed", type=int, default=0, help="Deterministic seed (int).")
    parser.add_argument("--output-dir", type=str, default="outputs", help="Directory to write outputs/results.json")
    args = parser.parse_args(argv)

    run_pipeline(seed=args.seed, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
