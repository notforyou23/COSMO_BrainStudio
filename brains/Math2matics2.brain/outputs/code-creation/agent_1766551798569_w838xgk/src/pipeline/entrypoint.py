"""Pipeline entrypoint: deterministic toy experiment writing canonical artifacts under ./outputs/."""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def _atomic_write_json(path: Path, obj: Any) -> None:
    _atomic_write_text(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


@dataclass
class RunContext:
    outputs_dir: Path
    seed: int
    log_path: Path
    results_path: Path
    stamp_path: Path
    figure_path: Path


def seed_everything(seed: int) -> Dict[str, Any]:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    info: Dict[str, Any] = {"seed": int(seed), "torch_seeded": False, "numpy_seeded": False}
    try:
        import numpy as np  # type: ignore
        np.random.seed(seed)
        info["numpy_seeded"] = True
    except Exception:
        pass
    try:
        import torch  # type: ignore
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        try:
            torch.use_deterministic_algorithms(True)
        except Exception:
            pass
        info["torch_seeded"] = True
    except Exception:
        pass
    return info


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s: str) -> int:
        for st in self.streams:
            st.write(s)
            st.flush()
        return len(s)

    def flush(self) -> None:
        for st in self.streams:
            st.flush()


def _init_run(outputs_dir: Path, seed: int) -> RunContext:
    out = _ensure_dir(outputs_dir)
    ctx = RunContext(
        outputs_dir=out,
        seed=int(seed),
        log_path=out / "run.log",
        results_path=out / "results.json",
        stamp_path=out / "run_stamp.json",
        figure_path=out / "figure.png",
    )
    return ctx


def _write_run_stamp(ctx: RunContext, seeding_info: Dict[str, Any], argv: Optional[list] = None) -> None:
    stamp = {
        "created_utc": _utc_now_iso(),
        "seed": ctx.seed,
        "argv": list(argv) if argv is not None else sys.argv[:],
        "cwd": str(Path.cwd()),
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "seeding": seeding_info,
    }
    _atomic_write_json(ctx.stamp_path, stamp)


def toy_experiment(ctx: RunContext, n: int = 1000) -> Tuple[Dict[str, Any], bool]:
    try:
        import numpy as np  # type: ignore
        rng = np.random.default_rng(ctx.seed)
        x = rng.normal(loc=0.0, scale=1.0, size=int(n))
        metrics = {
            "n": int(n),
            "mean": float(x.mean()),
            "std": float(x.std(ddof=0)),
            "min": float(x.min()),
            "max": float(x.max()),
        }
        used_plot = False
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt  # type: ignore

            fig, ax = plt.subplots(figsize=(6, 4))
            ax.hist(x, bins=40, color="#4472c4", alpha=0.85, edgecolor="white")
            ax.set_title("Toy experiment: N(0,1) samples (deterministic)")
            ax.set_xlabel("value")
            ax.set_ylabel("count")
            fig.tight_layout()
            fig.savefig(ctx.figure_path)
            plt.close(fig)
            used_plot = True
        except Exception:
            used_plot = False
        return {"metrics": metrics, "status": "ok"}, used_plot
    except Exception as e:
        return {"metrics": {}, "status": "error", "error": repr(e)}, False


def run(outputs: str = "outputs", seed: Optional[int] = None, n: int = 1000) -> Dict[str, Any]:
    outputs_dir = Path(outputs).resolve()
    chosen_seed = int(seed) if seed is not None else 1337
    ctx = _init_run(outputs_dir, chosen_seed)

    _ensure_dir(ctx.outputs_dir)
    log_f = ctx.log_path.open("w", encoding="utf-8")
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = _Tee(sys.stdout, log_f)
    sys.stderr = _Tee(sys.stderr, log_f)

    t0 = time.time()
    try:
        seeding_info = seed_everything(ctx.seed)
        _write_run_stamp(ctx, seeding_info, argv=sys.argv[:])
        print(f"[run] outputs_dir={ctx.outputs_dir}")
        print(f"[run] seed={ctx.seed} n={n}")
        payload, wrote_fig = toy_experiment(ctx, n=n)
        payload["artifacts"] = {
            "results_json": str(ctx.results_path),
            "run_stamp_json": str(ctx.stamp_path),
            "run_log": str(ctx.log_path),
            "figure_png": str(ctx.figure_path) if wrote_fig else None,
        }
        payload["runtime"] = {"seconds": round(time.time() - t0, 6)}
        _atomic_write_json(ctx.results_path, payload)
        print(f"[run] wrote {ctx.results_path.name}" + (f" and {ctx.figure_path.name}" if wrote_fig else ""))
        return payload
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout, sys.stderr = old_out, old_err
        log_f.close()


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Pipeline entrypoint for deterministic toy experiment.")
    p.add_argument("--outputs", type=str, default="outputs", help="Output directory (default: ./outputs)")
    p.add_argument("--seed", type=int, default=None, help="Deterministic seed (default: 1337)")
    p.add_argument("--n", type=int, default=1000, help="Number of samples")
    args = p.parse_args(argv)
    payload = run(outputs=args.outputs, seed=args.seed, n=args.n)
    return 0 if payload.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
