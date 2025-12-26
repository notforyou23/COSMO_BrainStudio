#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKER = ROOT / "outputs" / "PROJECT_TRACKER.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Entry:
    goal_id: str
    artifact_path: str
    status: str = "unknown"
    qa_result: str = "unknown"
    note: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def key(self) -> Tuple[str, str]:
        return (self.goal_id, self.artifact_path)


def _norm_path(p: str) -> str:
    p = p.strip()
    if not p:
        return p
    try:
        pp = Path(p)
        if pp.is_absolute():
            try:
                return str(pp.relative_to(ROOT)).replace("\\", "/")
            except Exception:
                return str(pp).replace("\\", "/")
        return str(pp).replace("\\", "/")
    except Exception:
        return p


def load_tracker(path: Path) -> Dict[str, Any]:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            data = {"entries": data}
        if not isinstance(data, dict):
            raise SystemExit(f"Invalid tracker format: {path}")
        data.setdefault("entries", [])
        if not isinstance(data["entries"], list):
            raise SystemExit(f"Invalid tracker entries: {path}")
        return data
    return {"entries": [], "schema": "project_tracker.v1", "created_at": now_iso()}


def save_tracker(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def upsert_entries(tracker: Dict[str, Any], incoming: List[Entry]) -> Dict[str, int]:
    entries: List[Dict[str, Any]] = tracker.get("entries", [])
    index: Dict[Tuple[str, str], int] = {}
    for i, e in enumerate(entries):
        gid = str(e.get("goal_id", ""))
        ap = str(e.get("artifact_path", ""))
        index[(gid, ap)] = i

    created = updated = 0
    ts = now_iso()
    for ent in incoming:
        ent.goal_id = str(ent.goal_id).strip()
        ent.artifact_path = _norm_path(str(ent.artifact_path))
        if not ent.goal_id or not ent.artifact_path:
            raise SystemExit("Each entry must include non-empty goal_id and artifact_path")
        k = ent.key()
        if k in index:
            cur = entries[index[k]]
            cur["status"] = ent.status or cur.get("status", "unknown")
            cur["qa_result"] = ent.qa_result or cur.get("qa_result", "unknown")
            if ent.note:
                cur["note"] = ent.note
            cur["updated_at"] = ts
            if not cur.get("created_at"):
                cur["created_at"] = ts
            updated += 1
        else:
            d = asdict(ent)
            d["artifact_path"] = _norm_path(d["artifact_path"])
            d["created_at"] = d.get("created_at") or ts
            d["updated_at"] = ts
            entries.append(d)
            index[k] = len(entries) - 1
            created += 1

    tracker["entries"] = entries
    return {"created": created, "updated": updated}


def parse_input_json(path: Path) -> List[Entry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "entries" in raw:
        raw = raw["entries"]
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raise SystemExit("Input JSON must be an object, a list of objects, or {"entries": [...]}")
    out: List[Entry] = []
    for obj in raw:
        if not isinstance(obj, dict):
            raise SystemExit("Each input entry must be a JSON object")
        out.append(Entry(
            goal_id=str(obj.get("goal_id", "")).strip(),
            artifact_path=str(obj.get("artifact_path", "")).strip(),
            status=str(obj.get("status", "unknown")).strip() or "unknown",
            qa_result=str(obj.get("qa_result", "unknown")).strip() or "unknown",
            note=str(obj.get("note", "")).strip(),
            created_at=obj.get("created_at"),
            updated_at=obj.get("updated_at"),
        ))
    return out


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Create/update outputs/PROJECT_TRACKER.json by upserting entries.")
    p.add_argument("--tracker", type=str, default=str(DEFAULT_TRACKER), help="Path to PROJECT_TRACKER.json")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=str, help="JSON file containing entry or entries to upsert")
    src.add_argument("--goal-id", type=str, help="Goal ID to upsert (single entry mode)")
    p.add_argument("--artifact", type=str, help="Artifact path for single entry mode")
    p.add_argument("--status", type=str, default="unknown", help="Status for single entry mode")
    p.add_argument("--qa", type=str, default="unknown", help="QA result for single entry mode")
    p.add_argument("--note", type=str, default="", help="Optional note for single entry mode")
    args = p.parse_args(argv)

    tracker_path = Path(args.tracker)
    tracker = load_tracker(tracker_path)

    if args.input:
        incoming = parse_input_json(Path(args.input))
    else:
        if not args.artifact:
            raise SystemExit("--artifact is required with --goal-id")
        incoming = [Entry(
            goal_id=args.goal_id,
            artifact_path=args.artifact,
            status=args.status,
            qa_result=args.qa,
            note=args.note,
        )]

    counts = upsert_entries(tracker, incoming)
    save_tracker(tracker_path, tracker)
    print(json.dumps({"tracker": str(tracker_path), **counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
