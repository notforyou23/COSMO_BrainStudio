from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import subprocess
import sys
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Union


JSONLike = Union[None, bool, int, float, str, List["JSONLike"], Dict[str, "JSONLike"]]


def _utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds")


def _try_run(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 5) -> Optional[str]:
    try:
        out = subprocess.check_output(cmd, cwd=str(cwd) if cwd else None, stderr=subprocess.DEVNULL, timeout=timeout)
        s = out.decode("utf-8", errors="replace").strip()
        return s or None
    except Exception:
        return None


def _find_git_root(start: Path) -> Optional[Path]:
    p = start.resolve()
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def get_environment_details(base_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    base = Path(base_dir).resolve() if base_dir else Path.cwd().resolve()
    git_root = _find_git_root(base)
    details: Dict[str, Any] = {
        "timestamp_utc": _utc_now_iso(),
        "cwd": str(Path.cwd().resolve()),
        "base_dir": str(base),
        "python": {
            "version": sys.version.replace("\n", " "),
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "env_vars_subset": {k: os.environ.get(k) for k in ("CONDA_DEFAULT_ENV", "VIRTUAL_ENV", "PYTHONPATH")},
        "git": {
            "root": str(git_root) if git_root else None,
            "commit": _try_run(["git", "rev-parse", "HEAD"], cwd=git_root) if git_root else None,
            "branch": _try_run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=git_root) if git_root else None,
            "status_porcelain": _try_run(["git", "status", "--porcelain"], cwd=git_root) if git_root else None,
        },
    }
    return details


def _coerce_paths(items: Optional[Iterable[Union[str, Path]]]) -> List[str]:
    if not items:
        return []
    out: List[str] = []
    for x in items:
        try:
            out.append(str(Path(x).resolve()))
        except Exception:
            out.append(str(x))
    return out


def _json_safe(obj: Any) -> JSONLike:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Mapping):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe(v) for v in obj]
    try:
        return str(obj)
    except Exception:
        return "<unserializable>"


@dataclass
class RunLog:
    run_id: str
    run_name: str
    started_utc: str
    finished_utc: Optional[str]
    duration_seconds: Optional[float]
    status: str
    inputs: List[str]
    outputs: List[str]
    parameters: Dict[str, JSONLike]
    environment: Dict[str, Any]
    notes: Optional[str] = None


def start_run(
    run_name: str = "meta_analysis_run",
    inputs: Optional[Iterable[Union[str, Path]]] = None,
    outputs: Optional[Iterable[Union[str, Path]]] = None,
    parameters: Optional[Mapping[str, Any]] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> RunLog:
    run_id = uuid.uuid4().hex
    env = get_environment_details(base_dir=base_dir)
    return RunLog(
        run_id=run_id,
        run_name=run_name,
        started_utc=_utc_now_iso(),
        finished_utc=None,
        duration_seconds=None,
        status="started",
        inputs=_coerce_paths(inputs),
        outputs=_coerce_paths(outputs),
        parameters=_json_safe(dict(parameters or {})),  # type: ignore[arg-type]
        environment=env,
        notes=None,
    )


def finish_run(run: RunLog, status: str = "success", notes: Optional[str] = None) -> RunLog:
    finished = _dt.datetime.now(tz=_dt.timezone.utc)
    started = _dt.datetime.fromisoformat(run.started_utc)
    run.finished_utc = finished.isoformat(timespec="seconds")
    run.duration_seconds = float((finished - started).total_seconds())
    run.status = status
    if notes:
        run.notes = notes
    return run


def save_run_log(
    run: RunLog,
    outputs_dir: Union[str, Path],
    filename: Optional[str] = None,
) -> Path:
    out_dir = Path(outputs_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if filename is None:
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in run.run_name).strip("_") or "run"
        filename = f"run_log_{safe_name}_{run.run_id}_{run.started_utc.replace(':', '').replace('-', '')}.json"
    path = out_dir / filename
    payload = asdict(run)
    payload["schema_version"] = "1.0"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def log_run(
    outputs_dir: Union[str, Path],
    run_name: str = "meta_analysis_run",
    inputs: Optional[Iterable[Union[str, Path]]] = None,
    outputs: Optional[Iterable[Union[str, Path]]] = None,
    parameters: Optional[Mapping[str, Any]] = None,
    status: str = "success",
    notes: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> Path:
    run = start_run(run_name=run_name, inputs=inputs, outputs=outputs, parameters=parameters, base_dir=base_dir)
    run = finish_run(run, status=status, notes=notes)
    return save_run_log(run, outputs_dir=outputs_dir)
