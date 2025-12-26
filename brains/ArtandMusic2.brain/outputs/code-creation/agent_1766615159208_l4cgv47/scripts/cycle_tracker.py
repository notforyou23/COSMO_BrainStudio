from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Union

SCHEMA_VERSION = 1
DEFAULT_TRACKER_REL = Path("runtime/outputs/logs/CYCLE_TRACKER.json")

JsonDict = Dict[str, Any]
Pathish = Union[str, Path]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_posix_path(p: Pathish) -> str:
    return Path(p).as_posix()


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass


def default_tracker() -> JsonDict:
    return {"schema_version": SCHEMA_VERSION, "cycles": []}


def load_tracker(path: Pathish) -> JsonDict:
    p = Path(path)
    if not p.exists():
        return default_tracker()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        data = default_tracker()
    if not isinstance(data, dict):
        data = default_tracker()
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("cycles", [])
    if not isinstance(data["cycles"], list):
        data["cycles"] = []
    return data


def write_tracker(path: Pathish, tracker: JsonDict) -> None:
    _atomic_write_json(Path(path), tracker)


def get_cycle(tracker: JsonDict, cycle_id: str) -> Optional[JsonDict]:
    for c in tracker.get("cycles", []):
        if isinstance(c, dict) and c.get("cycle_id") == cycle_id:
            return c
    return None


def upsert_cycle(
    tracker: JsonDict,
    cycle_id: str,
    *,
    date: Optional[str] = None,
    expected_artifacts: Optional[Iterable[Pathish]] = None,
    meta: Optional[JsonDict] = None,
) -> JsonDict:
    tracker.setdefault("cycles", [])
    c = get_cycle(tracker, cycle_id)
    if c is None:
        c = {"cycle_id": cycle_id, "created_at": utc_now_iso()}
        tracker["cycles"].append(c)
    c["updated_at"] = utc_now_iso()
    if date is not None:
        c["date"] = date
    c.setdefault("expected_artifacts", [])
    if expected_artifacts is not None:
        c["expected_artifacts"] = [_to_posix_path(p) for p in expected_artifacts]
    if meta:
        m = c.setdefault("meta", {})
        if isinstance(m, dict):
            m.update(meta)
        else:
            c["meta"] = dict(meta)
    c.setdefault("validation", {"status": "unknown"})
    c.setdefault("qa_reports", {})
    return c


def set_validation_status(
    cycle: JsonDict,
    *,
    status: str,
    checked_at: Optional[str] = None,
    present: Optional[Iterable[Pathish]] = None,
    missing: Optional[Iterable[Pathish]] = None,
    message: Optional[str] = None,
) -> None:
    v = cycle.setdefault("validation", {})
    if not isinstance(v, dict):
        v = {}
        cycle["validation"] = v
    v["status"] = status
    v["checked_at"] = checked_at or utc_now_iso()
    if present is not None:
        v["present"] = [_to_posix_path(p) for p in present]
    if missing is not None:
        v["missing"] = [_to_posix_path(p) for p in missing]
    if message is not None:
        v["message"] = message


def link_qa_report(cycle: JsonDict, name: str, path: Pathish) -> None:
    qr = cycle.setdefault("qa_reports", {})
    if not isinstance(qr, dict):
        qr = {}
        cycle["qa_reports"] = qr
    qr[name] = _to_posix_path(path)
    cycle["updated_at"] = utc_now_iso()


def record_validation_run(
    tracker_path: Pathish,
    cycle_id: str,
    *,
    date: Optional[str] = None,
    expected_artifacts: Optional[Iterable[Pathish]] = None,
    status: str,
    present: Optional[Iterable[Pathish]] = None,
    missing: Optional[Iterable[Pathish]] = None,
    qa_reports: Optional[Dict[str, Pathish]] = None,
    message: Optional[str] = None,
    meta: Optional[JsonDict] = None,
) -> JsonDict:
    p = Path(tracker_path)
    tracker = load_tracker(p)
    cycle = upsert_cycle(tracker, cycle_id, date=date, expected_artifacts=expected_artifacts, meta=meta)
    set_validation_status(cycle, status=status, present=present, missing=missing, message=message)
    if qa_reports:
        for k, v in qa_reports.items():
            link_qa_report(cycle, k, v)
    write_tracker(p, tracker)
    return cycle


def ensure_tracker_file(path: Pathish = DEFAULT_TRACKER_REL) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    if not p.exists():
        write_tracker(p, default_tracker())
    return p
