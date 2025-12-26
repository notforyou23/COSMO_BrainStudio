#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_DIRS = [
    "outputs",
    "outputs/qa",
    "outputs/qa/logs",
    "outputs/qa/templates",
    "outputs/qa/reports",
    "outputs/qa/artifacts",
]

@dataclass
class Result:
    root: str
    created: list[str]
    existed: list[str]
    missing_after: list[str]
    ok: bool
    timestamp_utc: str
    cwd: str
    python: str
    argv: list[str]
    dry_run: bool

def _utc_now():
    return datetime.now(timezone.utc)

def _ts():
    return _utc_now().strftime("%Y-%m-%dT%H-%M-%S-%fZ")

def _ensure_dirs(root: Path, dry_run: bool) -> tuple[list[str], list[str]]:
    created, existed = [], []
    for rel in EXPECTED_DIRS:
        p = (root / rel).resolve()
        if p.exists():
            existed.append(rel)
            continue
        if not dry_run:
            p.mkdir(parents=True, exist_ok=True)
        created.append(rel)
    return created, existed

def _verify(root: Path) -> list[str]:
    missing = []
    for rel in EXPECTED_DIRS:
        if not (root / rel).is_dir():
            missing.append(rel)
    return missing

def _write_log(root: Path, payload: dict) -> Path:
    log_dir = root / "outputs/qa/logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"init_outputs_{payload['timestamp_utc']}.jsonl"
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return log_path

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Create and verify outputs directory scaffold; write a run log.")
    ap.add_argument("--root", default=None, help="Project root (defaults to directory containing this script).")
    ap.add_argument("--dry-run", action="store_true", help="Do not create directories or write logs.")
    ap.add_argument("--no-log", action="store_true", help="Do not write a run log.")
    ap.add_argument("--json", action="store_true", help="Print result as JSON.")
    ns = ap.parse_args(argv)

    root = Path(ns.root).expanduser().resolve() if ns.root else Path(__file__).resolve().parent
    created, existed = _ensure_dirs(root, ns.dry_run)
    missing_after = _verify(root)
    ok = len(missing_after) == 0

    res = Result(
        root=str(root),
        created=created,
        existed=existed,
        missing_after=missing_after,
        ok=ok,
        timestamp_utc=_ts(),
        cwd=str(Path.cwd().resolve()),
        python=sys.version.split()[0],
        argv=list(sys.argv),
        dry_run=bool(ns.dry_run),
    )
    payload = asdict(res)

    log_path = None
    if (not ns.dry_run) and (not ns.no_log):
        log_path = _write_log(root, payload)
        payload["log_path"] = str(log_path)

    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        status = "OK" if ok else "MISSING"
        print(f"{status}: root={payload['root']} created={len(created)} existed={len(existed)} missing={len(missing_after)}")
        if log_path:
            print(f"LOG:{log_path}")

    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
