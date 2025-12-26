"""minipipeline.run

A minimal, deterministic pipeline entrypoint that always writes two artifacts:
- outputs/run_stamp.json
- outputs/run.log

The artifacts are intended to be stable across repeated runs given the same input
payload and environment (no wall-clock timestamps are used).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import platform
import sys
from typing import Any, Dict, Optional, Tuple
def _canonical_json(obj: Any) -> str:
    """Return canonical JSON (sorted keys, compact separators, newline-terminated)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _append_log_line(log_path: Path, record: Dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(_canonical_json(record))
def _stable_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    # Provide a stable default payload when none is supplied.
    if payload is None:
        return {"job": "minipipeline", "version": 1, "params": {"alpha": 1, "beta": 2}}
    # Avoid accidental mutation by callers.
    return json.loads(_canonical_json(payload))


def _env_fingerprint() -> Dict[str, Any]:
    vi = sys.version_info
    return {
        "python": f"{vi.major}.{vi.minor}.{vi.micro}",
        "implementation": platform.python_implementation(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "machine": platform.machine(),
        "os_name": os.name,
    }


def _hash_dict(d: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(_canonical_json(d).encode("utf-8"))
    return h.hexdigest()
@dataclass(frozen=True)
class RunResult:
    outputs_dir: Path
    run_stamp_path: Path
    run_log_path: Path
    run_id: str


def run(payload: Optional[Dict[str, Any]] = None, outputs_dir: Optional[Path] = None) -> RunResult:
    """Run the minimal pipeline and write deterministic artifacts."""
    out_dir = Path(outputs_dir) if outputs_dir is not None else Path(os.environ.get("OUTPUT_DIR", "outputs"))
    out_dir = out_dir.resolve()
    stamp_path = out_dir / "run_stamp.json"
    log_path = out_dir / "run.log"

    stable_payload = _stable_payload(payload)
    env = _env_fingerprint()
    run_id = _hash_dict({"payload": stable_payload, "env": env})

    stamp = {
        "run_id": run_id,
        "payload": stable_payload,
        "env": env,
        "artifacts": {"run_stamp": str(stamp_path), "run_log": str(log_path)},
    }

    _atomic_write_text(stamp_path, _canonical_json(stamp))
    _append_log_line(log_path, {"event": "run_start", "run_id": run_id})
    _append_log_line(log_path, {"event": "payload", "run_id": run_id, "payload": stable_payload})
    _append_log_line(log_path, {"event": "run_end", "run_id": run_id, "status": "ok"})

    return RunResult(out_dir, stamp_path, log_path, run_id)
def main(argv: Optional[list[str]] = None) -> int:
    """CLI entrypoint: writes artifacts and prints a short status line."""
    _ = argv if argv is not None else sys.argv[1:]
    result = run()
    # Keep stdout minimal and deterministic.
    print(_canonical_json({"run_id": result.run_id, "outputs_dir": str(result.outputs_dir)}), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
