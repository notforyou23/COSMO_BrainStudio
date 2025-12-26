from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
def _import_output_utils():
    try:
        from utils.output_paths import OUTPUT_DIR, ensure_dir, out_path  # type: ignore
        return OUTPUT_DIR, ensure_dir, out_path
    except Exception:
        # Fallback for early-stage installs; still avoids any hard-coded /outputs paths.
        output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs")).resolve()

        def ensure_dir(p: Path) -> Path:
            p.mkdir(parents=True, exist_ok=True)
            return p

        def out_path(*parts: str, ensure: bool = False) -> Path:
            p = output_dir.joinpath(*parts)
            if ensure:
                ensure_dir(p if p.suffix == "" else p.parent)
            return p

        return output_dir, ensure_dir, out_path
OUTPUT_DIR, ensure_dir, out_path = _import_output_utils()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def run_pipeline(config_path: Optional[Path] = None) -> Dict[str, Any]:
    ensure_dir(OUTPUT_DIR)

    config: Dict[str, Any] = {}
    if config_path is not None:
        config_path = config_path.expanduser().resolve()
        if config_path.exists():
            config = _read_json(config_path)
            _write_json(out_path("configs", config_path.name, ensure=True), config)

    run_dir = out_path("runs", ensure=True)
    artifacts_dir = out_path("artifacts", ensure=True)

    manifest: Dict[str, Any] = {
        "output_dir": str(OUTPUT_DIR),
        "run_dir": str(run_dir),
        "artifacts_dir": str(artifacts_dir),
        "config_path": str(config_path) if config_path else None,
        "env": {"OUTPUT_DIR": os.getenv("OUTPUT_DIR")},
        "config": config,
    }

    # Always write a canonical manifest so downstream tools have a stable anchor.
    _write_json(out_path("run_manifest.json", ensure=True), manifest)

    # If writer utilities exist, let them handle additional artifacts.
    try:
        from writers.artifact_writers import write_run_manifest  # type: ignore

        write_run_manifest(manifest)
    except Exception:
        pass

    return manifest
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Main pipeline entrypoint.")
    p.add_argument(
        "--config",
        type=str,
        default=os.getenv("CONFIG_PATH", ""),
        help="Path to a JSON config file.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    config_path = Path(args.config).expanduser() if args.config else None
    run_pipeline(config_path=config_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
