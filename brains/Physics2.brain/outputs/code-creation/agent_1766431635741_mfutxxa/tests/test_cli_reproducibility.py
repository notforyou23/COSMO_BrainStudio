import json
import os
import subprocess
import sys
from pathlib import Path

import qg_bench


def _run_cli(output_path: Path) -> dict:
    pkg_dir = Path(qg_bench.__file__).resolve().parent
    schema_path = pkg_dir / "schema.json"
    data_path = pkg_dir / "data" / "example_dataset.jsonl"

    env = os.environ.copy()
    # Reduce sources of nondeterminism across platforms and runs.
    env.setdefault("PYTHONHASHSEED", "0")
    env.setdefault("TZ", "UTC")

    cmd = [
        sys.executable,
        "-m",
        "qg_bench.cli",
        "--schema",
        str(schema_path),
        "--dataset",
        str(data_path),
        "--output",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, f"CLI failed:\\nSTDOUT={proc.stdout}\\nSTDERR={proc.stderr}"
    assert output_path.exists(), f"Expected output file not found: {output_path}"
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_cli_reproducibility(tmp_path: Path) -> None:
    out1 = tmp_path / "results_1.json"
    out2 = tmp_path / "results_2.json"

    r1 = _run_cli(out1)
    r2 = _run_cli(out2)

    # Full JSON should be identical for a deterministic benchmark.
    assert r1 == r2

    # And specifically the metadata/hash block must not include run-local fields.
    assert "metadata" in r1
    assert "hash" in r1
    assert r1["metadata"] == r2["metadata"]
    assert r1["hash"] == r2["hash"]
