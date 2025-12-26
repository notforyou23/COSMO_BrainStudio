import json
import numpy as np
import pytest


def test_protocol_registry_smoke():
    from dgpipe.protocols import list_protocols, get_protocol

    prots = list_protocols(min_priority=90)
    assert len(prots) >= 2
    assert prots[0]["priority"] >= prots[1]["priority"]
    p0 = get_protocol(prots[0]["id"])
    assert p0["schema_version"] == "1.0"
    assert isinstance(p0["protocol_steps"], list)
    assert "params" in p0 and isinstance(p0["params"], dict)
def test_simulation_deterministic_snapshot():
    from dgpipe.simulations import DiscreteParams, NoiseModel, SimConfig, simulate_equal_time_correlator

    x = np.linspace(0.0, 5.0, 11)
    cfg = SimConfig(L=64.0, N_modes=256, k_cut=None)
    dp = DiscreteParams(a=1.0, alpha=0.2, power=2, m=0.1)
    noise = NoiseModel(sigma=1e-3, seed=123)

    out = simulate_equal_time_correlator(x, cfg=cfg, dp=dp, noise=noise)
    assert out["protocol"] == "equal_time_correlator"
    assert out["meta"]["discrete"]["alpha"] == 0.2
    np.testing.assert_allclose(out["y"][:3], [0.5728735058130552, 0.5231168896221478, 0.4181115604963545], rtol=0, atol=1e-12)
    assert all(float(s) == pytest.approx(1e-3) for s in out["yerr"])
def test_inference_recovers_alpha_map():
    from dgpipe.inference import InferenceProblem, map_fit_random
    import dgpipe.simulations as sim

    x = np.linspace(0.0, 6.0, 25)
    cfg = sim.SimConfig(L=64.0, N_modes=256)
    dp_true = sim.DiscreteParams(a=1.0, alpha=0.15, power=2, m=0.05)
    y = sim._wightman(0.0, x, cfg, dp_true)
    yobs, yerr = sim._add_noise(y, sim.NoiseModel(sigma=2e-3, seed=7))

    def model(theta, xx):
        dp = sim.DiscreteParams(a=1.0, alpha=float(theta[0]), power=2, m=0.05)
        return sim._wightman(0.0, np.asarray(xx, dtype=float), cfg, dp)

    prob = InferenceProblem(x=x, y=yobs, sigma=yerr, model=model, param_names=("alpha",), priors={"alpha": ("uniform", 0.0, 0.4)})
    rng = np.random.default_rng(0)
    best, _ = map_fit_random(prob.logpost, bounds=[(0.0, 0.4)], nsamples=3000, rng=rng)
    assert float(best[0]) == pytest.approx(0.15, abs=0.03)
def test_cli_end_to_end_smoke(tmp_path, capsys):
    from dgpipe.cli import main

    outdir = tmp_path / "out"
    rc = main(["--outdir", str(outdir), "protocols"])
    assert rc == 0 and (outdir / "protocols.json").exists()

    rc = main(
        [
            "--outdir",
            str(outdir),
            "simulate",
            "--n",
            "64",
            "--dt",
            "0.02",
            "--xi",
            "1.2",
            "--omega",
            "5.0",
            "--ell",
            "0.15",
            "--alpha",
            "1.0",
            "--rho",
            "0.8",
            "--L",
            "10.0",
            "--noise",
            "0.0",
            "--seed",
            "0",
        ]
    )
    assert rc == 0 and (outdir / "simulation.json").exists()

    sim = json.loads((outdir / "simulation.json").read_text(encoding="utf-8"))
    assert sim["model"] == "toy_discrete_dispersion_v1"
    assert len(sim["data"]["t"]) == 64 and len(sim["data"]["C"]) == 64
    assert np.isfinite(sim["data"]["mutual_info"])

    rc = main(
        [
            "--outdir",
            str(outdir),
            "infer",
            str(outdir / "simulation.json"),
            "--ell-min",
            "0.0",
            "--ell-max",
            "0.3",
            "--m",
            "61",
            "--alpha",
            "1.0",
            "--L",
            "10.0",
        ]
    )
    assert rc == 0 and (outdir / "inference.json").exists()
    inf = json.loads((outdir / "inference.json").read_text(encoding="utf-8"))
    assert "point_estimates" in inf and "ell_map" in inf["point_estimates"]
    assert float(inf["point_estimates"]["ell_map"]) == pytest.approx(0.15, abs=1e-9)
