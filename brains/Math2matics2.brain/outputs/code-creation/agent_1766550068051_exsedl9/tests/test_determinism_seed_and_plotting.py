import hashlib
import importlib
from pathlib import Path

import pytest


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _import_determinism_module():
    for mod in ("src.determinism", "determinism"):
        try:
            return importlib.import_module(mod)
        except Exception:
            continue
    pytest.fail("Could not import determinism module (expected src.determinism or determinism).")


def _call_seed_pin(mod, seed: int):
    for name in (
        "pin_seed",
        "set_seed",
        "set_global_seed",
        "set_global_determinism",
        "apply_global_seed",
        "apply_determinism",
        "configure_determinism",
    ):
        fn = getattr(mod, name, None)
        if callable(fn):
            try:
                return fn(seed)
            except TypeError:
                return fn(seed=seed)
    pytest.fail(
        "No seed pinning function found on determinism module; expected one of: "
        "pin_seed/set_seed/set_global_seed/set_global_determinism/apply_global_seed/apply_determinism/configure_determinism"
    )


def _call_plot_defaults(mod):
    for name in (
        "set_matplotlib_deterministic",
        "set_matplotlib_defaults",
        "apply_matplotlib_defaults",
        "configure_matplotlib",
        "apply_plotting_defaults",
    ):
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn()
    pytest.fail(
        "No matplotlib defaults function found on determinism module; expected one of: "
        "set_matplotlib_deterministic/set_matplotlib_defaults/apply_matplotlib_defaults/configure_matplotlib/apply_plotting_defaults"
    )
def test_seed_pinning_reproducible_sequences():
    mod = _import_determinism_module()

    _call_seed_pin(mod, 12345)
    import random

    r1 = [random.random() for _ in range(5)]
    try:
        import numpy as np
    except Exception:
        np = None
    n1 = None if np is None else np.random.RandomState(0).rand(5).tolist()
    g1 = None if np is None else np.random.rand(5).tolist()

    _call_seed_pin(mod, 12345)
    r2 = [random.random() for _ in range(5)]
    g2 = None if np is None else np.random.rand(5).tolist()

    assert r1 == r2
    if np is not None:
        assert g1 == g2
        assert n1 == np.random.RandomState(0).rand(5).tolist()

    try:
        import torch
    except Exception:
        torch = None
    if torch is not None:
        _call_seed_pin(mod, 12345)
        t1 = torch.rand(5)
        _call_seed_pin(mod, 12345)
        t2 = torch.rand(5)
        assert torch.allclose(t1, t2)
def test_matplotlib_deterministic_png_hash_stable(tmp_path: Path):
    mod = _import_determinism_module()
    _call_seed_pin(mod, 2024)
    _call_plot_defaults(mod)

    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import numpy as np

    def render(out: Path) -> str:
        _call_seed_pin(mod, 2024)
        _call_plot_defaults(mod)
        plt.close("all")
        x = np.linspace(0.0, 1.0, 200)
        y = np.sin(2 * np.pi * x) + 0.1 * np.cos(4 * np.pi * x)
        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
        ax.plot(x, y, color="#1f77b4", linewidth=1.25, antialiased=True)
        ax.set_title("Determinism Test", fontsize=10)
        ax.set_xlabel("x", fontsize=9)
        ax.set_ylabel("y", fontsize=9)
        ax.grid(True, linewidth=0.5, alpha=0.4)
        fig.tight_layout(pad=0.2)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(
            out,
            format="png",
            dpi=100,
            facecolor="white",
            edgecolor="white",
            bbox_inches=None,
            pad_inches=0.0,
            metadata={},
        )
        plt.close(fig)
        return _sha256_bytes(out.read_bytes())

    h1 = render(tmp_path / "a.png")
    h2 = render(tmp_path / "b.png")

    assert h1 == h2
