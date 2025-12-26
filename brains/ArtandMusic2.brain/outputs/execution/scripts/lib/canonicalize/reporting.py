from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, IO, Iterable, List, Optional
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(obj, (set, tuple)):
        return list(obj)
    return obj


def json_dumps(data: Any, *, sort_keys: bool = True) -> str:
    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        sort_keys=sort_keys,
        default=_to_jsonable,
    )


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_dumps(data) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
@dataclass
class Report:
    project: str
    created_at: str = field(default_factory=utc_now_iso)
    scan: Dict[str, Any] = field(default_factory=dict)
    selection: Dict[str, Any] = field(default_factory=dict)
    migration: Dict[str, Any] = field(default_factory=lambda: {"actions": [], "counts": {}})
    diagnostics: Dict[str, Any] = field(default_factory=lambda: {"warnings": [], "errors": []})

    def add_warning(self, message: str, **context: Any) -> None:
        item = {"ts": utc_now_iso(), "message": message}
        if context:
            item["context"] = context
        self.diagnostics["warnings"].append(item)

    def add_error(self, message: str, **context: Any) -> None:
        item = {"ts": utc_now_iso(), "message": message}
        if context:
            item["context"] = context
        self.diagnostics["errors"].append(item)

    def set_scan_summary(self, **data: Any) -> None:
        self.scan.update(data)

    def set_selection(self, qa_runner: Optional[Path], schema: Optional[Path], **details: Any) -> None:
        self.selection = {
            "ts": utc_now_iso(),
            "qa_runner": str(qa_runner) if qa_runner else None,
            "schema": str(schema) if schema else None,
            **details,
        }

    def add_migration_action(self, action: str, src: Optional[Path] = None, dst: Optional[Path] = None, **details: Any) -> None:
        rec: Dict[str, Any] = {"ts": utc_now_iso(), "action": action}
        if src is not None:
            rec["src"] = str(src)
        if dst is not None:
            rec["dst"] = str(dst)
        if details:
            rec["details"] = details
        self.migration["actions"].append(rec)

    def bump_count(self, key: str, n: int = 1) -> None:
        counts = self.migration.setdefault("counts", {})
        counts[key] = int(counts.get(key, 0)) + int(n)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "project": self.project,
            "created_at": self.created_at,
            "scan": self.scan,
            "selection": self.selection,
            "migration": self.migration,
            "diagnostics": self.diagnostics,
        }
class EventLogger:
    """CI-friendly structured logger: emits one JSON object per line."""

    def __init__(self, stream: Optional[IO[str]] = None, *, name: str = "canonicalize") -> None:
        self.stream = stream or sys.stderr
        self.name = name

    def emit(self, event: str, **fields: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"ts": utc_now_iso(), "name": self.name, "event": event}
        for k, v in fields.items():
            payload[k] = _to_jsonable(v)
        self.stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.stream.flush()
        return payload

    def info(self, event: str, **fields: Any) -> Dict[str, Any]:
        return self.emit(event, level="info", **fields)

    def warning(self, event: str, **fields: Any) -> Dict[str, Any]:
        return self.emit(event, level="warning", **fields)

    def error(self, event: str, **fields: Any) -> Dict[str, Any]:
        return self.emit(event, level="error", **fields)
def summarize_candidates(candidates: Iterable[Dict[str, Any]], *, limit: int = 50) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, c in enumerate(candidates):
        if i >= limit:
            out.append({"truncated": True, "limit": limit})
            break
        item = dict(c)
        for k in ("path", "src", "dst"):
            if k in item and isinstance(item[k], Path):
                item[k] = str(item[k])
        out.append(item)
    return out


def save_report(report: Report, path: Path) -> None:
    write_json(path, report.as_dict())
