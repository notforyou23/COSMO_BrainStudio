from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Dict, Any, List, Tuple


DEFAULT_SEED = 1337


def _project_root() -> Path:
    # This file lives in <root>/src/, so root is parent of this file's directory.
    return Path(__file__).resolve().parent.parent


def _outputs_dir(root: Path) -> Path:
    out = root / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


@dataclass(frozen=True)
class ToyResult:
    seed: int
    n: int
    mean: float
    stdev: float
    digest8: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "n": self.n,
            "mean": self.mean,
            "stdev": self.stdev,
            "digest8": self.digest8,
        }
def _mean_stdev(xs: List[float]) -> Tuple[float, float]:
    if not xs:
        return 0.0, 0.0
    n = len(xs)
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / n
    return m, var ** 0.5


def run_toy_experiment(seed: int = DEFAULT_SEED, n: int = 64) -> ToyResult:
    _seed_everything(seed)
    rng = random.Random(seed)

    # Deterministic sample stream (no external deps).
    xs = [rng.gauss(0.0, 1.0) for _ in range(n)]
    m, s = _mean_stdev(xs)

    # Deterministic content digest so filename can be stable & uniquely tied to the run.
    payload = json.dumps({"seed": seed, "n": n, "xs": xs}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest8 = sha256(payload).hexdigest()[:8]
    return ToyResult(seed=seed, n=n, mean=m, stdev=s, digest8=digest8)


def write_artifacts(result: ToyResult, outputs: Path) -> List[Path]:
    fname = f"goal_33_toy_experiment_seed{result.seed}_n{result.n}_{result.digest8}.json"
    path = outputs / fname
    path.write_text(json.dumps(result.to_dict(), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return [path]


def validate_artifacts(paths: List[Path]) -> None:
    if not paths:
        raise RuntimeError("No artifacts were produced.")
    missing = [str(p) for p in paths if not p.exists() or p.stat().st_size <= 0]
    if missing:
        raise RuntimeError(f"Missing/empty artifact(s): {missing}")
def main() -> int:
    root = _project_root()
    out = _outputs_dir(root)
    result = run_toy_experiment(seed=DEFAULT_SEED, n=64)
    paths = write_artifacts(result, out)
    validate_artifacts(paths)

    # Keep output short and deterministic.
    rel_paths = [str(p.relative_to(root)) for p in sorted(paths)]
    print("ARTIFACTS:" + json.dumps(rel_paths, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
