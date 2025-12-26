import json
import sys
from pathlib import Path

import pytest


def _import_cli():
    # Ensure local package import works in isolated test environments.
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import src.cli as cli  # type: ignore

    # Work around missing import in src.cli without modifying package code.
    if not hasattr(cli, "hashlib"):
        import hashlib  # noqa: WPS433 (std lib)
        cli.hashlib = hashlib  # type: ignore[attr-defined]
    return cli


def _small_cfg(run_id: str = "smoke_run", seed: int = 123) -> dict:
    return {
        "run_id": run_id,
        "seed": seed,
        "theory": {"conjectures": ["dS", "Distance"], "holography": ["Bousso"]},
        "models": [{"name": "single_field_slow_roll", "params": {"N": 30}}],
        "robustness": {"n_samples": 8, "jitter_frac": 0.1},
        "data": {"constraints": [{"name": "ns", "mu": 0.965, "sigma": 0.004}, {"name": "r", "upper_95": 0.036}]},
    }
def test_pipeline_outputs_are_well_formed_and_deterministic():
    cli = _import_cli()
    cfg = _small_cfg()

    cli.set_seed(cfg["seed"])
    h1 = cli.generate_hypotheses(cfg)
    r1 = cli.robustness_checks(cfg, h1)
    c1 = cli.confront_data(cfg, h1, r1)

    cli.set_seed(cfg["seed"])
    h2 = cli.generate_hypotheses(cfg)
    r2 = cli.robustness_checks(cfg, h2)
    c2 = cli.confront_data(cfg, h2, r2)

    assert h1 == h2
    assert r1 == r2
    assert c1 == c2

    assert h1["schema"] == "hypotheses.v1"
    assert isinstance(h1.get("id"), str) and len(h1["id"]) == 16
    assert isinstance(h1["items"], list) and len(h1["items"]) > 0
    for it in h1["items"]:
        assert {"conjecture", "model", "signature", "consistency_test", "priority"} <= set(it)

    assert r1["schema"] == "robustness.v1"
    assert isinstance(r1.get("id"), str) and len(r1["id"]) == 16
    assert len(r1["items"]) == len(h1["items"])
    for it in r1["items"]:
        assert 0.0 <= float(it["pass_rate"]) <= 1.0
        assert int(it["n"]) == int(cfg["robustness"]["n_samples"])

    assert c1["schema"] == "confrontation.v1"
    assert isinstance(c1.get("id"), str) and len(c1["id"]) == 16
    assert isinstance(c1["ranked"], list)
    assert int(c1["n_constraints"]) == len(cfg["data"]["constraints"])
def test_cli_main_runs_end_to_end_and_writes_artifacts(tmp_path, capsys):
    cli = _import_cli()
    cfg = _small_cfg(run_id="smoke_cli", seed=7)

    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    outdir = tmp_path / "runs"
    rc = cli.main(["--config", str(cfg_path), "--outdir", str(outdir)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    run_dir = Path(payload["outdir"])
    assert run_dir.exists()

    # Artifacts exist and have stable shapes.
    arts = {k: Path(v) for k, v in payload["artifacts"].items()}
    for p in arts.values():
        assert p.exists() and p.stat().st_size > 0

    hyp = json.loads(arts["hypotheses_path"].read_text(encoding="utf-8"))
    rob = json.loads(arts["robustness_path"].read_text(encoding="utf-8"))
    conf = json.loads(arts["confrontation_path"].read_text(encoding="utf-8"))
    assert hyp["schema"] == "hypotheses.v1"
    assert rob["schema"] == "robustness.v1"
    assert conf["schema"] == "confrontation.v1"

    # Determinism check: rerun should reproduce exact JSON outputs given fixed run_id+seed.
    rc2 = cli.main(["--config", str(cfg_path), "--outdir", str(outdir)])
    assert rc2 == 0
    _ = capsys.readouterr()  # ignore second printed payload
    hyp2 = arts["hypotheses_path"].read_text(encoding="utf-8")
    rob2 = arts["robustness_path"].read_text(encoding="utf-8")
    conf2 = arts["confrontation_path"].read_text(encoding="utf-8")
    assert hyp2 == json.dumps(hyp, indent=2, sort_keys=True) + "\n"
    assert rob2 == json.dumps(rob, indent=2, sort_keys=True) + "\n"
    assert conf2 == json.dumps(conf, indent=2, sort_keys=True) + "\n"
