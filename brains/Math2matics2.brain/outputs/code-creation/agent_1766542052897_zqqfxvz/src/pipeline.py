from __future__ import annotations

import json
import math
import os
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class RunMeta:
    run_id: str
    timestamp_utc: str
    python: str
    platform: str
    cwd: str


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_text(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")


def _write_json(p: Path, obj: Any) -> None:
    _write_text(p, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _log_line(fp, msg: str) -> None:
    fp.write(msg.rstrip("\n") + "\n")
    fp.flush()


def _deterministic_series(n: int = 101) -> Tuple[list[float], list[float]]:
    # Deterministic, dependency-free synthetic signal.
    xs = [i / (n - 1) for i in range(n)]
    ys = [math.sin(2 * math.pi * x) * math.exp(-1.5 * x) for x in xs]
    return xs, ys


def _summarize(xs: list[float], ys: list[float]) -> Dict[str, float]:
    mean_y = sum(ys) / len(ys)
    var_y = sum((y - mean_y) ** 2 for y in ys) / len(ys)
    auc = sum((ys[i] + ys[i + 1]) * (xs[i + 1] - xs[i]) / 2 for i in range(len(xs) - 1))
    return {
        "n": float(len(xs)),
        "mean_y": float(round(mean_y, 12)),
        "std_y": float(round(math.sqrt(var_y), 12)),
        "min_y": float(round(min(ys), 12)),
        "max_y": float(round(max(ys), 12)),
        "auc": float(round(auc, 12)),
    }


def _plot_png(path: Path, xs: list[float], ys: list[float]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.figsize": (6.4, 4.0),
            "figure.dpi": 100,
            "savefig.dpi": 100,
            "font.size": 10,
            "axes.grid": True,
            "grid.alpha": 0.3,
        }
    )
    fig, ax = plt.subplots()
    ax.plot(xs, ys, color="#1f77b4", linewidth=2)
    ax.set_title("Deterministic synthetic signal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_xlim(0, 1)
    fig.tight_layout()
    fig.savefig(path, format="png", metadata={})
    plt.close(fig)


def run(outputs_dir: Path | None = None) -> Dict[str, Any]:
    root = _root_dir()
    out = Path(outputs_dir) if outputs_dir else root / "outputs"
    _ensure_dir(out)

    meta = RunMeta(
        run_id="single-cycle",
        timestamp_utc="1970-01-01T00:00:00Z",
        python=sys.version.split()[0],
        platform=f"{platform.system()}-{platform.machine()}",
        cwd=str(Path.cwd()),
    )

    run_log = out / "run.log"
    test_log = out / "test.log"
    results_json = out / "results.json"
    fig_png = out / "figure.png"
    status_md = out / "STATUS.md"

    with run_log.open("w", encoding="utf-8") as lf:
        _log_line(lf, f"pipeline.start run_id={meta.run_id} ts={meta.timestamp_utc}")
        xs, ys = _deterministic_series()
        metrics = _summarize(xs, ys)
        results = {"meta": asdict(meta), "metrics": metrics, "artifacts": {}}
        _write_json(results_json, results)
        _log_line(lf, f"wrote {results_json.name}")
        _plot_png(fig_png, xs, ys)
        _log_line(lf, f"wrote {fig_png.name}")
        _log_line(lf, "pipeline.end ok=true")

    # Minimal "tests" for evidence pack, logged to outputs/test.log
    passed = True
    messages = []
    try:
        data = json.loads(results_json.read_text(encoding="utf-8"))
        assert "meta" in data and "metrics" in data
        assert int(data["metrics"]["n"]) == 101
        assert fig_png.exists() and fig_png.stat().st_size > 0
        assert run_log.exists() and run_log.stat().st_size > 0
        messages.append("smoke: artifacts exist and results.json minimally valid")
    except Exception as e:  # pragma: no cover
        passed = False
        messages.append(f"smoke: FAILED ({type(e).__name__}: {e})")

    with test_log.open("w", encoding="utf-8") as tf:
        _log_line(tf, f"tests.start run_id={meta.run_id}")
        for m in messages:
            _log_line(tf, m)
        _log_line(tf, f"tests.end passed={str(passed).lower()}")

    status = "\n".join(
        [
            "# Evidence Pack Status",
            "",
            f"- Pipeline: ran `src/pipeline.py` (run_id={meta.run_id}, ts={meta.timestamp_utc})",
            "- Outputs directory: `outputs/`",
            "- Artifacts:",
            f"  - `outputs/results.json`",
            f"  - `outputs/figure.png`",
            f"  - `outputs/run.log`",
            f"  - `outputs/test.log`",
            f"  - `outputs/STATUS.md`",
            f"- Smoke checks: {'PASS' if passed else 'FAIL'} (see `outputs/test.log`)",
            "",
        ]
    )
    _write_text(status_md, status)
    return {"outputs_dir": str(out), "passed": passed}


if __name__ == "__main__":
    info = run()
    print(json.dumps(info, indent=2, sort_keys=True))
