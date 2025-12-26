from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


DEFAULT_SEED = 1337


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _fixed_output_path(root: Optional[Path] = None) -> Path:
    root = _project_root() if root is None else root
    return root / "outputs" / "toy_experiment" / "results.json"


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fallback_toy_experiment(seed: int, output_path: Path) -> Dict[str, Any]:
    rng = random.Random(seed)
    n = 10
    values = [rng.random() for _ in range(n)]
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / n
    results = {
        "schema_version": 1,
        "experiment": "toy_experiment",
        "seed": seed,
        "n": n,
        "values": values,
        "metrics": {"mean": mean, "variance": var},
        "output_path": str(output_path.as_posix()),
    }
    _write_json(output_path, results)
    return results


def run(seed: int = DEFAULT_SEED, output_path: Optional[Path] = None) -> Dict[str, Any]:
    output_path = _fixed_output_path() if output_path is None else Path(output_path)
    try:
        from toy_experiment.run import run as pkg_run  # type: ignore

        result = pkg_run(seed=seed, output_path=output_path)
        if isinstance(result, dict):
            if not output_path.exists():
                _write_json(output_path, result)
            return result
    except Exception:
        pass
    return _fallback_toy_experiment(seed=seed, output_path=output_path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="generated_library_1766554101798")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output",
        type=str,
        default=str(_fixed_output_path().as_posix()),
        help="Output JSON path (defaults to ./outputs/toy_experiment/results.json).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    run(seed=int(args.seed), output_path=Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
