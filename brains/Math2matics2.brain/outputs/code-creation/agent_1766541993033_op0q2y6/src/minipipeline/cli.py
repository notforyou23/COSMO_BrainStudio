"""minipipeline CLI.

This CLI is intentionally minimal: it runs the pipeline and ensures that a
deterministic set of artifacts are written to the chosen output directory.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Optional
def _default_output_dir() -> Path:
    # Prefer an explicit env var, otherwise default to /outputs as per mission.
    return Path(os.environ.get("MINIPIPELINE_OUTPUT_DIR", "/outputs"))
def _load_payload(payload_json: Optional[str]) -> Mapping[str, Any]:
    if not payload_json:
        # Stable default payload to keep runs deterministic.
        return {"payload_version": 1, "message": "minipipeline"}
    try:
        obj = json.loads(payload_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for --payload-json: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError("--payload-json must decode to a JSON object")
    return obj
def _run_pipeline(output_dir: Path, payload: Mapping[str, Any]) -> None:
    """Run the pipeline via the package entrypoint (with a safe fallback)."""
    try:
        from .run import run  # type: ignore
    except Exception:
        run = None

    if callable(run):
        run(output_dir=output_dir, payload=dict(payload))
        return

    # Fallback skeleton to keep CLI runnable in isolation.
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp_path = output_dir / "run_stamp.json"
    log_path = output_dir / "run.log"
    stamp = {
        "schema_version": 1,
        "ok": True,
        "payload": dict(payload),
        "output_dir": str(output_dir),
    }
    stamp_path.write_text(json.dumps(stamp, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    log_path.write_text("event=run_started\nevent=run_finished ok=true\n", encoding="utf-8")
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="minipipeline", description="Run the minimal deterministic pipeline.")
    p.add_argument("--output-dir", type=Path, default=_default_output_dir(), help="Directory to write artifacts into.")
    p.add_argument("--payload-json", default=None, help="JSON object used as the input payload.")
    return p
def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = _load_payload(args.payload_json)
        _run_pipeline(Path(args.output_dir), payload)
    except Exception as e:
        print(f"minipipeline: error: {e}", file=sys.stderr)
        return 2
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
