"""Minimal runnable pipeline that emits reproducible CI artifacts.

Creates an outputs directory and writes:
- outputs/run_stamp.json (machine-readable run metadata)
- outputs/run.log        (human-readable execution log)
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
REQUIRED_SCHEMA_KEYS = (
    "schema_version",
    "run_id",
    "started_at",
    "finished_at",
    "status",
    "outputs_dir",
    "run_stamp_path",
    "run_log_path",
)
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    project_root = Path(__file__).resolve().parents[1]
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex
    started_at = _utc_now_iso()
    t0 = time.time()

    run_log_path = outputs_dir / "run.log"
    run_stamp_path = outputs_dir / "run_stamp.json"

    details = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": None,
        "status": "running",
        "outputs_dir": str(outputs_dir),
        "run_stamp_path": str(run_stamp_path),
        "run_log_path": str(run_log_path),
        "argv": argv,
        "python": sys.version.split()[0],
        "cwd": os.getcwd(),
    }

    # Write an initial stamp early so CI can detect partial runs.
    run_stamp_path.write_text(json.dumps(details, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    log_lines = [
        f"started_at={started_at}",
        f"run_id={run_id}",
        f"project_root={project_root}",
        f"outputs_dir={outputs_dir}",
        f"argv={argv}",
    ]
    status = "success"
    try:
        # Minimal "pipeline" work: ensure we can write artifacts deterministically.
        (outputs_dir / ".gitkeep").write_text("", encoding="utf-8")
        log_lines.append("wrote_artifacts=run_stamp.json,run.log")
    except Exception as exc:  # pragma: no cover
        status = "error"
        log_lines.append(f"error={type(exc).__name__}:{exc}")
        raise
    finally:
        finished_at = _utc_now_iso()
        elapsed_s = round(time.time() - t0, 6)

        details["finished_at"] = finished_at
        details["status"] = status
        details["elapsed_s"] = elapsed_s

        # Validate required schema keys are present before writing final stamp.
        missing = [k for k in REQUIRED_SCHEMA_KEYS if k not in details]
        if missing:  # pragma: no cover
            raise RuntimeError(f"Missing required schema keys: {missing}")

        run_stamp_path.write_text(json.dumps(details, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_lines.append(f"finished_at={finished_at}")
        log_lines.append(f"status={status}")
        log_lines.append(f"elapsed_s={elapsed_s}")

        run_log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    return 0 if status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
