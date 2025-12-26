#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Any, Dict, Optional
ROOT = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')
TRACKER_PATH = ROOT / 'outputs' / 'PROJECT_TRACKER.json'

ALLOWED_STATUS = {'planned', 'in_progress', 'blocked', 'done', 'validated', 'failed'}

def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def _norm_evidence(paths_or_links: List[str]) -> List[str]:
    out: List[str] = []
    for s in paths_or_links:
        if not s:
            continue
        s = s.strip()
        if not s:
            continue
        p = Path(s)
        if (not s.startswith('http://') and not s.startswith('https://') and not s.startswith('file://')):
            if p.is_absolute():
                out.append(str(p))
            else:
                out.append(str((ROOT / p).resolve()))
        else:
            out.append(s)
    # de-dupe while preserving order
    seen = set()
    deduped = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        deduped.append(x)
    return deduped

def _load_tracker(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        raise SystemExit(f'Invalid JSON in tracker: {path} ({e})')
    if data is None:
        return []
    if not isinstance(data, list):
        raise SystemExit(f'Tracker must be a JSON array: {path}')
    return data

def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    os.replace(tmp, path)
@dataclass
class Entry:
    date: str
    goalId: str
    taskId: str
    status: str
    artifactsChanged: List[str]
    evidenceLinks: List[str]
    note: Optional[str] = None

def build_entry(args: argparse.Namespace) -> Entry:
    status = (args.status or '').strip()
    if status not in ALLOWED_STATUS:
        raise SystemExit(f'--status must be one of {sorted(ALLOWED_STATUS)}')
    goal = (args.goalId or '').strip()
    task = (args.taskId or '').strip()
    if not goal:
        raise SystemExit('--goalId is required')
    if not task:
        raise SystemExit('--taskId is required')

    artifacts = [a.strip() for a in (args.artifact or []) if a and a.strip()]
    artifacts = _norm_evidence(artifacts)

    evidence = _norm_evidence((args.evidence or []))
    if args.validation_log:
        evidence = _norm_evidence([args.validation_log]) + evidence

    note = (args.note or '').strip() or None
    dt = (args.date or '').strip() or _iso_utc_now()
    return Entry(
        date=dt,
        goalId=goal,
        taskId=task,
        status=status,
        artifactsChanged=artifacts,
        evidenceLinks=evidence,
        note=note,
    )
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description='Append a validated progress entry to outputs/PROJECT_TRACKER.json (append-only JSON array).'
    )
    p.add_argument('--goalId', required=True, help='Goal identifier')
    p.add_argument('--taskId', required=True, help='Task identifier')
    p.add_argument('--status', required=True, help=f"One of: {', '.join(sorted(ALLOWED_STATUS))}")
    p.add_argument('--date', help='ISO-8601 timestamp; default = current UTC (Z)')
    p.add_argument('--artifact', action='append', default=[], help='Artifact path(s) changed (repeatable)')
    p.add_argument('--evidence', action='append', default=[], help='Evidence link(s) or path(s) (repeatable)')
    p.add_argument('--validation-log', dest='validation_log', help='Validation log path (added to evidenceLinks)')
    p.add_argument('--note', help='Optional short note')
    p.add_argument('--tracker', default=str(TRACKER_PATH), help='Tracker path (default: outputs/PROJECT_TRACKER.json)')
    p.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')
    args = p.parse_args(argv)

    tracker_path = Path(args.tracker)
    if not tracker_path.is_absolute():
        tracker_path = (ROOT / tracker_path).resolve()

    entry = build_entry(args)
    ledger = _load_tracker(tracker_path)
    ledger.append({k: v for k, v in asdict(entry).items() if v is not None})

    text = json.dumps(ledger, indent=2, ensure_ascii=False) + '\n' if args.pretty else json.dumps(ledger, ensure_ascii=False) + '\n'
    _atomic_write(tracker_path, text)

    print(f'APPENDED:{tracker_path}')
    print(f'ENTRY_DATE:{entry.date}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
