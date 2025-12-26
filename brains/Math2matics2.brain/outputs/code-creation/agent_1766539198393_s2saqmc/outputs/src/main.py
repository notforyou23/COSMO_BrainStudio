#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


@dataclass(frozen=True)
class RunConfig:
    seed: int
    n: int
    out_dir: str


def generate_numbers(seed: int, n: int) -> list[float]:
    rng = random.Random(seed)
    return [round(rng.random(), 12) for _ in range(n)]


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Deterministic output generator + run logger")
    p.add_argument("--seed", type=int, default=0, help="PRNG seed (default: 0)")
    p.add_argument("--n", type=int, default=10, help="How many numbers to generate")
    p.add_argument(
        "--out-dir",
        default=None,
        help="Base outputs directory (default: project outputs/ next to src/)",
    )
    args = p.parse_args(argv)

    src_dir = Path(__file__).resolve().parent
    outputs_dir = Path(args.out_dir).resolve() if args.out_dir else src_dir.parent
    artifacts_dir = outputs_dir / "artifacts"
    logs_dir = outputs_dir / "logs"

    cfg = RunConfig(seed=int(args.seed), n=int(args.n), out_dir=str(outputs_dir))
    started = _utc_now()

    nums = generate_numbers(cfg.seed, cfg.n)
    summary = {
        "count": len(nums),
        "min": min(nums) if nums else None,
        "max": max(nums) if nums else None,
        "sum": round(sum(nums), 12),
    }

    artifact = {"config": asdict(cfg), "numbers": nums, "summary": summary}
    artifact_text = _json_dumps(artifact) + "\n"
    artifact_bytes = artifact_text.encode("utf-8")
    artifact_hash = _sha256_bytes(artifact_bytes)

    artifact_path = artifacts_dir / f"numbers_seed{cfg.seed}_n{cfg.n}.json"
    write_text_atomic(artifact_path, artifact_text)

    run_log: Dict[str, Any] = {
        "started_utc": started,
        "finished_utc": _utc_now(),
        "argv": sys.argv,
        "cwd": str(Path.cwd()),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "env": {"PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED")},
        "config": asdict(cfg),
        "artifact": {
            "path": str(artifact_path),
            "sha256": artifact_hash,
            "bytes": len(artifact_bytes),
        },
    }

    log_name = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_seed{cfg.seed}.json"
    log_path = logs_dir / log_name
    write_text_atomic(log_path, _json_dumps(run_log) + "\n")

    # Keep stdout minimal and stable for tooling.
    print(str(artifact_path))
    print(str(log_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
