from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import json
import traceback
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def write_json(path: Path, obj: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
@dataclass
class StepSummary:
    name: str
    status: str  # "ok" | "failed" | "skipped"
    started_at: str
    ended_at: str
    duration_s: float
    returncode: Optional[int] = None
    raw_log: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    outputs: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
class StepLogger:
    def __init__(self, build_root: Path, step_name: str):
        self.build_root = Path(build_root)
        self.step_name = step_name
        self.step_dir = ensure_dir(self.build_root / "steps" / step_name)
        self.raw_log_path = self.step_dir / "raw.log"
        self.summary_path = self.step_dir / "summary.json"
        self._t0 = datetime.now(timezone.utc)
        write_text(self.raw_log_path, f"[{utc_now_iso()}] START {step_name}\n")

    def log(self, msg: str) -> None:
        if not msg.endswith("\n"):
            msg += "\n"
        append_text(self.raw_log_path, f"[{utc_now_iso()}] {msg}")

    def record_result(
        self,
        *,
        status: str,
        returncode: Optional[int] = None,
        stdout_path: Optional[Path] = None,
        stderr_path: Optional[Path] = None,
        outputs: Optional[Dict[str, Path]] = None,
        error: Optional[str] = None,
    ) -> StepSummary:
        t1 = datetime.now(timezone.utc)
        dur = (t1 - self._t0).total_seconds()
        outmap: Dict[str, str] = {}
        if outputs:
            outmap = {k: str(Path(v)) for k, v in outputs.items()}
        summ = StepSummary(
            name=self.step_name,
            status=status,
            started_at=self._t0.isoformat(timespec="seconds"),
            ended_at=t1.isoformat(timespec="seconds"),
            duration_s=dur,
            returncode=returncode,
            raw_log=str(self.raw_log_path),
            stdout=str(stdout_path) if stdout_path else None,
            stderr=str(stderr_path) if stderr_path else None,
            outputs=outmap,
            error=error,
        )
        write_json(self.summary_path, summ.to_dict())
        self.log(f"END {self.step_name} status={status} returncode={returncode} duration_s={dur:.3f}")
        return summ
def format_exception(e: BaseException) -> str:
    return "".join(traceback.format_exception(type(e), e, e.__traceback__)).strip()


def write_final_status(
    build_root: Path,
    *,
    status: str,
    steps: Dict[str, Dict[str, Any]],
    message: Optional[str] = None,
) -> Path:
    build_root = Path(build_root)
    ensure_dir(build_root)
    final = {
        "status": status,
        "generated_at": utc_now_iso(),
        "message": message,
        "steps": steps,
    }
    summary_path = build_root / "final_summary.json"
    status_path = build_root / "STATUS.txt"
    write_json(summary_path, final)
    write_text(status_path, f"{status}\n")
    return summary_path
