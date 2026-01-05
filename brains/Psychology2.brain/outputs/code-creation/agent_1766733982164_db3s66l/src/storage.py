from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import hashlib
import json
import os
import re
import time


_SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")


def filesystem_safe_name(name: str, max_len: int = 120) -> str:
    s = (name or "").strip()
    if not s:
        return "unnamed"
    s = _SAFE_CHARS_RE.sub("_", s)
    s = s.strip("._-")
    if not s:
        s = "unnamed"
    return s[:max_len]


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def deterministic_run_id(payload: Any, prefix: str = "run") -> str:
    h = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()[:16]
    return f"{prefix}_{h}"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _append_ndjson(path: Path, rows: Iterable[Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
            f.write("\n")
            n += 1
    return n


@dataclass(frozen=True)
class RunPaths:
    run_dir: Path
    request_json: Path
    outputs_json: Path
    outputs_ndjson: Path
    logs_ndjson: Path
    meta_json: Path


class Storage:
    """Persists run inputs/outputs under outputs/ with deterministic run IDs and export helpers.\"""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else Path.cwd()
        self.outputs_root = self.root / "outputs"
        self.runs_root = self.outputs_root / "runs"

    def get_run_paths(self, run_id: str) -> RunPaths:
        safe = filesystem_safe_name(run_id)
        run_dir = self.runs_root / safe
        return RunPaths(
            run_dir=run_dir,
            request_json=run_dir / "request.json",
            outputs_json=run_dir / "outputs.json",
            outputs_ndjson=run_dir / "outputs.ndjson",
            logs_ndjson=run_dir / "logs.ndjson",
            meta_json=run_dir / "meta.json",
        )

    def ensure_run(self, run_id: str, request: Optional[Dict[str, Any]] = None) -> RunPaths:
        paths = self.get_run_paths(run_id)
        paths.run_dir.mkdir(parents=True, exist_ok=True)
        if not paths.meta_json.exists():
            _write_json(paths.meta_json, {"run_id": run_id, "created_at": time.time()})
        if request is not None and not paths.request_json.exists():
            self.write_request(run_id, request)
        return paths

    def create_run(self, request: Dict[str, Any], prefix: str = "run") -> str:
        run_id = deterministic_run_id(request, prefix=prefix)
        self.ensure_run(run_id, request=request)
        return run_id

    def write_request(self, run_id: str, request: Dict[str, Any]) -> Path:
        paths = self.ensure_run(run_id)
        _write_json(paths.request_json, request)
        return paths.request_json

    def write_outputs_json(self, run_id: str, outputs: Any) -> Path:
        paths = self.ensure_run(run_id)
        _write_json(paths.outputs_json, outputs)
        return paths.outputs_json

    def append_outputs_ndjson(self, run_id: str, rows: Iterable[Any]) -> int:
        paths = self.ensure_run(run_id)
        return _append_ndjson(paths.outputs_ndjson, rows)

    def append_log(self, run_id: str, event: Dict[str, Any]) -> None:
        if "ts" not in event:
            event = dict(event)
            event["ts"] = time.time()
        self.append_logs(run_id, [event])

    def append_logs(self, run_id: str, events: Iterable[Dict[str, Any]]) -> int:
        paths = self.ensure_run(run_id)
        return _append_ndjson(paths.logs_ndjson, events)

    def read_request(self, run_id: str) -> Dict[str, Any]:
        paths = self.get_run_paths(run_id)
        return json.loads(paths.request_json.read_text(encoding="utf-8"))

    def read_outputs_json(self, run_id: str) -> Any:
        paths = self.get_run_paths(run_id)
        return json.loads(paths.outputs_json.read_text(encoding="utf-8"))

    def list_runs(self) -> List[str]:
        if not self.runs_root.exists():
            return []
        out: List[str] = []
        for p in sorted(self.runs_root.iterdir()):
            if p.is_dir():
                out.append(p.name)
        return out
