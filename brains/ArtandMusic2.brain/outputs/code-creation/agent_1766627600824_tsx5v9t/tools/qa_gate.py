from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union
import contextlib
import json
import os
import subprocess
import sys
import time
import traceback
@dataclass
class StageResult:
    name: str
    ok: bool
    started_at: float
    ended_at: float
    returncode: int = 0
    notes: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_s(self) -> float:
        return max(0.0, self.ended_at - self.started_at)
def _now() -> float:
    return time.time()


def _as_list(x: Union[str, Sequence[str]]) -> List[str]:
    if isinstance(x, str):
        return [x]
    return list(x)
def run_command(
    name: str,
    argv: Union[str, Sequence[str]],
    *,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_s: Optional[float] = None,
    capture_output: bool = True,
) -> StageResult:
    started = _now()
    notes: List[str] = []
    details: Dict[str, Any] = {"type": "command", "argv": _as_list(argv)}
    try:
        cp = subprocess.run(
            _as_list(argv),
            cwd=str(cwd) if cwd is not None else None,
            env=env,
            timeout=timeout_s,
            text=True,
            capture_output=capture_output,
            check=False,
        )
        ok = (cp.returncode == 0)
        if capture_output:
            if cp.stdout:
                details["stdout_tail"] = cp.stdout[-4000:]
            if cp.stderr:
                details["stderr_tail"] = cp.stderr[-4000:]
        if not ok:
            notes.append(f"command failed (rc={cp.returncode})")
        ended = _now()
        return StageResult(name=name, ok=ok, started_at=started, ended_at=ended, returncode=cp.returncode, notes=notes, details=details)
    except subprocess.TimeoutExpired as e:
        ended = _now()
        details["timeout_s"] = timeout_s
        if getattr(e, "stdout", None):
            details["stdout_tail"] = (e.stdout or "")[-4000:]
        if getattr(e, "stderr", None):
            details["stderr_tail"] = (e.stderr or "")[-4000:]
        notes.append("command timed out")
        return StageResult(name=name, ok=False, started_at=started, ended_at=ended, returncode=124, notes=notes, details=details)
    except Exception:
        ended = _now()
        details["exception"] = traceback.format_exc(limit=50)
        notes.append("command exception")
        return StageResult(name=name, ok=False, started_at=started, ended_at=ended, returncode=2, notes=notes, details=details)
def run_callable(
    name: str,
    fn: Callable[[], Any],
) -> StageResult:
    started = _now()
    notes: List[str] = []
    details: Dict[str, Any] = {"type": "callable", "callable": getattr(fn, "__name__", repr(fn))}
    try:
        out = fn()
        ok = True
        if out is False:
            ok = False
            notes.append("callable returned False")
        details["result"] = out
        ended = _now()
        return StageResult(name=name, ok=ok, started_at=started, ended_at=ended, returncode=0 if ok else 1, notes=notes, details=details)
    except SystemExit as e:
        code = int(e.code) if isinstance(e.code, int) else 1
        ended = _now()
        ok = (code == 0)
        notes.append(f"callable raised SystemExit({code})")
        details["system_exit"] = code
        return StageResult(name=name, ok=ok, started_at=started, ended_at=ended, returncode=code, notes=notes, details=details)
    except Exception:
        ended = _now()
        details["exception"] = traceback.format_exc(limit=50)
        notes.append("callable exception")
        return StageResult(name=name, ok=False, started_at=started, ended_at=ended, returncode=2, notes=notes, details=details)
@dataclass
class QAGateReport:
    ok: bool
    stages: List[StageResult] = field(default_factory=list)
    checks: List[StageResult] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def returncode(self) -> int:
        if self.ok:
            return 0
        # Prefer nonzero from first failing stage/check when available.
        for r in self.stages + self.checks:
            if not r.ok:
                return r.returncode or 1
        return 1
def _summarize_result(r: StageResult) -> str:
    status = "OK" if r.ok else "FAIL"
    dur = f"{r.duration_s:.2f}s"
    note = f" [{'; '.join(r.notes)}]" if r.notes else ""
    return f"{status} {r.name} ({dur}){note}"


def format_report_text(report: QAGateReport) -> str:
    lines: List[str] = []
    lines.append(f"QA_GATE: {'PASS' if report.ok else 'FAIL'} rc={report.returncode}")
    if report.meta:
        with contextlib.suppress(Exception):
            lines.append("META: " + json.dumps(report.meta, sort_keys=True))
    if report.stages:
        lines.append("STAGES:")
        lines.extend("  " + _summarize_result(r) for r in report.stages)
    if report.checks:
        lines.append("CHECKS:")
        lines.extend("  " + _summarize_result(r) for r in report.checks)
    return "\n".join(lines)
def run_pipeline(
    *,
    stages: Sequence[Tuple[str, Union[Callable[[], Any], Sequence[str], str]]],
    checks: Optional[Sequence[Tuple[str, Union[Callable[[], Any], Sequence[str], str]]]] = None,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
    stop_on_failure: bool = True,
    meta: Optional[Dict[str, Any]] = None,
) -> QAGateReport:
    st_results: List[StageResult] = []
    ck_results: List[StageResult] = []
    ok = True

    def _run_one(name: str, item: Union[Callable[[], Any], Sequence[str], str]) -> StageResult:
        if callable(item):
            return run_callable(name, item)  # type: ignore[arg-type]
        return run_command(name, item, cwd=cwd, env=env)

    for name, item in stages:
        r = _run_one(name, item)
        st_results.append(r)
        if not r.ok:
            ok = False
            if stop_on_failure:
                return QAGateReport(ok=False, stages=st_results, checks=ck_results, meta=meta or {})

    for name, item in (checks or []):
        r = _run_one(name, item)
        ck_results.append(r)
        if not r.ok:
            ok = False
            if stop_on_failure:
                break

    return QAGateReport(ok=ok, stages=st_results, checks=ck_results, meta=meta or {})
def write_report(
    report: QAGateReport,
    path: Union[str, Path],
) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(format_report_text(report) + "\n", encoding="utf-8")


def exit_with_report(report: QAGateReport, *, stream: Any = None) -> "NoReturn":
    if stream is None:
        stream = sys.stdout if report.ok else sys.stderr
    stream.write(format_report_text(report) + "\n")
    raise SystemExit(report.returncode)
