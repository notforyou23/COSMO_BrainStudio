from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union
import getpass
import json
import os
import platform
import socket
import sys
import traceback
JSON = Dict[str, Any]


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _ensure_dir(p: Union[str, Path]) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_relpath(p: Union[str, Path], base: Union[str, Path]) -> str:
    p = Path(p)
    base = Path(base)
    try:
        return str(p.resolve().relative_to(base.resolve()))
    except Exception:
        return str(p)
def collect_environment(extra: Optional[Mapping[str, Any]] = None) -> JSON:
    env: JSON = {
        "ts_utc": _utc_ts(),
        "user": getpass.getuser(),
        "cwd": str(Path.cwd()),
        "python": {
            "executable": sys.executable,
            "version": sys.version.replace("\n", " "),
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "host": {"hostname": socket.gethostname()},
        "pid": os.getpid(),
    }
    if extra:
        env["extra"] = dict(extra)
    return env
def _json_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    try:
        return asdict(obj)  # type: ignore[arg-type]
    except Exception:
        return str(obj)


def write_jsonl(path: Union[str, Path], records: Iterable[Mapping[str, Any]]) -> Path:
    path = Path(path)
    _ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, default=_json_default) + "\n")
    return path


def write_text(path: Union[str, Path], text: str) -> Path:
    path = Path(path)
    _ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")
    return path
@dataclass
class RunLogPaths:
    directory: Path
    jsonl_path: Path
    text_path: Optional[Path] = None


def _format_text_summary(payload: Mapping[str, Any]) -> str:
    lines = []
    lines.append(f"timestamp_utc: {payload.get('ts_utc')}")
    lines.append(f"event: {payload.get('event', 'run')}")
    proj = payload.get("project")
    if proj:
        lines.append(f"project: {proj}")
    status = payload.get("status")
    if status:
        lines.append(f"status: {status}")
    created = payload.get("created_dirs")
    if isinstance(created, Sequence):
        lines.append(f"created_dirs: {len(created)}")
    missing = payload.get("missing_paths")
    if isinstance(missing, Sequence):
        lines.append(f"missing_paths: {len(missing)}")
    env = payload.get("environment", {})
    if isinstance(env, Mapping):
        py = env.get("python", {})
        lines.append(f"python: {py.get('version', '')}".strip())
        lines.append(f"cwd: {env.get('cwd', '')}".strip())
    err = payload.get("error")
    if err:
        lines.append(f"error: {err}")
    return "\n".join([ln for ln in lines if ln]) + "\n"
def write_run_log(
    logs_dir: Union[str, Path],
    *,
    event: str = "init_outputs",
    project: Optional[str] = None,
    status: str = "ok",
    verification: Optional[Mapping[str, Any]] = None,
    created_dirs: Optional[Sequence[Union[str, Path]]] = None,
    missing_paths: Optional[Sequence[Union[str, Path]]] = None,
    templates: Optional[Sequence[Union[str, Path]]] = None,
    reports: Optional[Sequence[Union[str, Path]]] = None,
    extra_env: Optional[Mapping[str, Any]] = None,
    write_text_file: bool = True,
    jsonl_filename: Optional[str] = None,
    text_filename: Optional[str] = None,
) -> Tuple[JSON, RunLogPaths]:
    logs_dir = _ensure_dir(logs_dir)
    ts = _utc_ts().replace(":", "").replace("-", "")
    jsonl_name = jsonl_filename or f"{ts}_{event}.jsonl"
    text_name = text_filename or f"{ts}_{event}.log"

    payload: JSON = {
        "ts_utc": _utc_ts(),
        "event": event,
        "project": project,
        "status": status,
        "environment": collect_environment(extra_env),
    }

    def _norm_list(vals: Optional[Sequence[Union[str, Path]]]) -> Optional[Sequence[str]]:
        if vals is None:
            return None
        return [str(Path(v)) for v in vals]

    if verification is not None:
        payload["verification"] = dict(verification)
    if created_dirs is not None:
        payload["created_dirs"] = _norm_list(created_dirs)
    if missing_paths is not None:
        payload["missing_paths"] = _norm_list(missing_paths)
    if templates is not None:
        payload["templates"] = _norm_list(templates)
    if reports is not None:
        payload["reports"] = _norm_list(reports)

    jsonl_path = logs_dir / jsonl_name
    write_jsonl(jsonl_path, [payload])

    text_path: Optional[Path] = None
    if write_text_file:
        text_path = logs_dir / text_name
        write_text(text_path, _format_text_summary(payload))

    return payload, RunLogPaths(directory=logs_dir, jsonl_path=jsonl_path, text_path=text_path)


def write_exception_run_log(
    logs_dir: Union[str, Path],
    *,
    event: str = "init_outputs",
    project: Optional[str] = None,
    exc: Optional[BaseException] = None,
    verification: Optional[Mapping[str, Any]] = None,
    extra_env: Optional[Mapping[str, Any]] = None,
) -> Tuple[JSON, RunLogPaths]:
    err = None
    tb = None
    if exc is not None:
        err = repr(exc)
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    payload, paths = write_run_log(
        logs_dir,
        event=event,
        project=project,
        status="error",
        verification=verification,
        extra_env=extra_env,
        write_text_file=True,
    )
    if err:
        payload["error"] = err
    if tb:
        payload["traceback"] = tb
    write_jsonl(paths.jsonl_path, [payload])
    if paths.text_path:
        write_text(paths.text_path, _format_text_summary(payload))
    return payload, paths
