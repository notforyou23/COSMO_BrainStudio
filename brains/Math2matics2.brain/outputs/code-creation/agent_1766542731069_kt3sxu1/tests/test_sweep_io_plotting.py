import os
from pathlib import Path

import pytest

os.environ.setdefault("MPLBACKEND", "Agg")
def test_sweep_run_records_and_errors():
    from experiments.sweep import run_sweep

    def runner(cfg):
        if cfg["x"] == 2:
            raise ValueError("boom")
        return {"metric": cfg["x"] * 10}

    res = run_sweep(runner, {"x": [1, 2, 3]}, base_config={"base": 5})
    assert len(res.records) == 3
    assert res.errors == 1
    r1, r2, r3 = res.records
    assert r1["base"] == 5 and r1["x"] == 1 and r1["metric"] == 10
    assert r2["x"] == 2 and r2["error"] == "ValueError" and "boom" in r2["traceback"]
    assert r3["x"] == 3 and r3["metric"] == 30
def test_io_roundtrip_save_load_run(tmp_path: Path):
    from experiments.io import SweepPaths, load_run, save_run

    run_dir = tmp_path / "run1"
    config = {"name": "demo", "params": {"lr": 0.1}}
    results = [{"lr": 0.1, "acc": 0.9, "step": 1}, {"lr": 0.1, "acc": 0.95, "step": 2}]
    metadata = {"seed": 123, "status": "ok"}

    sp = save_run(run_dir, config=config, results=results, metadata=metadata)
    assert isinstance(sp, SweepPaths)
    assert sp.config_path.exists() and sp.results_path.exists() and sp.metadata_path.exists()

    loaded = load_run(run_dir)
    assert loaded["config"] == config
    assert loaded["metadata"] == metadata
    assert loaded["results"] == results
def test_plotting_creates_png(tmp_path: Path):
    pytest.importorskip("matplotlib")

    from experiments.plotting import plot_metric_vs_param, save_figure, summarize_metrics, plot_summary_bars

    rows = [
        {"lr": 0.1, "acc": 0.90},
        {"lr": 0.1, "acc": 0.95},
        {"lr": 0.2, "acc": 0.85},
    ]

    fig, ax = plot_metric_vs_param(rows, param="lr", metric="acc", agg="mean")
    assert ax.get_xlabel() == "lr"
    assert ax.get_ylabel() == "acc"

    out_path = save_figure(fig, tmp_path / "metric_vs_param.png", close=True)
    assert out_path.exists() and out_path.stat().st_size > 0

    summary = summarize_metrics(rows, ["acc"])
    fig2, _ = plot_summary_bars(summary)
    out2 = save_figure(fig2, tmp_path / "summary", close=True)  # default suffix
    assert out2.suffix == ".png" and out2.exists() and out2.stat().st_size > 0
