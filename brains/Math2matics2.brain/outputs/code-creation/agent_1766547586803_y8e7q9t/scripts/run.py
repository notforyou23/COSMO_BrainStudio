#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


SCHEMA_VERSION = 1
STAMP_FILENAME = "run_stamp.json"
LOG_FILENAME = "run.log"


def project_root() -> Path:
    # scripts/run.py -> project root is parent of scripts/
    return Path(__file__).resolve().parents[1]


def outputs_dir(root: Path) -> Path:
    return root / "outputs"


def deterministic_stamp(root: Path, out_dir: Path) -> dict:
    # Fixed schema + fixed values (no timestamps, randomness, hostname, env, etc.)
    return {
        "schema_version": SCHEMA_VERSION,
        "project": root.name,
        "entrypoint": "scripts/run.py",
        "run": {
            "run_id": "deterministic-run-0001",
            "mode": "deterministic",
        },
        "outputs": {
            "dir": "outputs",
            "files": {
                "run_stamp_json": str(Path("outputs") / STAMP_FILENAME),
                "run_log": str(Path("outputs") / LOG_FILENAME),
            },
        },
    }


def deterministic_log_lines() -> list[str]:
    return [
        "run.py: start (deterministic)\n",
        "run.py: wrote outputs/run_stamp.json\n",
        "run.py: wrote outputs/run.log\n",
        "run.py: done\n",
    ]


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def write_text_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines)


def main() -> int:
    root = project_root()
    out_dir = outputs_dir(root)

    stamp_path = out_dir / STAMP_FILENAME
    log_path = out_dir / LOG_FILENAME

    stamp = deterministic_stamp(root, out_dir)

    write_json(stamp_path, stamp)
    write_text_lines(log_path, deterministic_log_lines())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
