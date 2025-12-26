import inspect
import json
from pathlib import Path

import numpy as np
import pytest

# Ensure non-interactive backend for figure export tests
import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt  # noqa: E402


def _resolve_attr(mod, candidates):
    for name in candidates:
        if hasattr(mod, name):
            return getattr(mod, name)
    pytest.fail(f"Missing required API. Tried: {candidates!r}")


def _normalize(obj):
    # Normalize common container types to a JSON-stable python structure.
    if obj is None:
        return None
    if hasattr(obj, "to_dict"):
        try:
            return obj.to_dict(orient="records")  # pandas DataFrame
        except TypeError:
            return obj.to_dict()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (list, tuple)):
        return [_normalize(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    return obj


def _call_sweep(sweep_fn):
    sig = inspect.signature(sweep_fn)
    kw = {}
    # Prefer a pure deterministic runner if supported.
    if "runner" in sig.parameters:
        kw["runner"] = lambda p: {"y": float(p["x"]) ** 2}
    if "func" in sig.parameters and "runner" not in kw:
        kw["func"] = lambda p: {"y": float(p["x"]) ** 2}
    if "params_list" in sig.parameters:
        kw["params_list"] = [{"x": 0.0}, {"x": 1.0}, {"x": 2.0}]
    else:
        grid = {"x": [0.0, 1.0, 2.0]}
        for k in ("param_grid", "grid", "sweep", "params", "parameters"):
            if k in sig.parameters:
                kw[k] = grid
                break
    for k in ("seed", "random_seed", "rng_seed"):
        if k in sig.parameters:
            kw[k] = 123
    for k in ("experiment", "experiment_id", "name"):
        if k in sig.parameters and k not in kw:
            kw[k] = "experiment_1"
    for k in ("n_trials", "trials", "repeats"):
        if k in sig.parameters:
            kw[k] = 1
    return sweep_fn(**kw)


def test_sweep_reproducibility(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    import experiments as exp

    sweep_fn = _resolve_attr(exp, ["run_sweep", "parameter_sweep", "run_parameter_sweep", "sweep"])
    r1 = _normalize(_call_sweep(sweep_fn))
    r2 = _normalize(_call_sweep(sweep_fn))
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_csv_roundtrip(tmp_path):
    import experiments as exp

    sweep_fn = _resolve_attr(exp, ["run_sweep", "parameter_sweep", "run_parameter_sweep", "sweep"])
    results = _call_sweep(sweep_fn)

    save_csv = _resolve_attr(exp, ["save_results_csv", "write_results_csv", "results_to_csv", "to_csv"])
    load_csv = _resolve_attr(exp, ["load_results_csv", "read_results_csv", "results_from_csv", "from_csv"])

    path = tmp_path / "results.csv"
    save_sig = inspect.signature(save_csv)
    if len(save_sig.parameters) == 1:
        save_csv(path)
    else:
        save_csv(results, path)

    loaded = load_csv(path)
    assert json.dumps(_normalize(results), sort_keys=True) == json.dumps(_normalize(loaded), sort_keys=True)


def test_figure_export_png_svg(tmp_path):
    import experiments as exp

    export_fig = _resolve_attr(exp, ["export_figure", "save_figure", "save_figures", "savefig"])

    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 4])
    ax.set_title("export-test")

    png = tmp_path / "fig.png"
    svg = tmp_path / "fig.svg"

    sig = inspect.signature(export_fig)
    if "fig" in sig.parameters:
        export_fig(fig=fig, path=png)
        export_fig(fig=fig, path=svg)
    else:
        export_fig(fig, png)
        export_fig(fig, svg)

    assert png.exists() and png.stat().st_size > 0
    assert svg.exists() and svg.stat().st_size > 0
    plt.close(fig)
