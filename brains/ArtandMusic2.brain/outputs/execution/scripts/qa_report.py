from pathlib import Path
import json
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

QA_REPORT_FILENAME = "QA_REPORT.json"
DEFAULT_QA_SUBDIR = Path("outputs") / "qa"

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_ERROR = "ERROR"
STATUS_SKIP = "SKIP"

EXIT_CODES = {
    STATUS_PASS: 0,
    STATUS_SKIP: 0,
    STATUS_FAIL: 2,
    STATUS_ERROR: 3,
}


def qa_dir(base_dir: Optional[Path] = None) -> Path:
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    return base / DEFAULT_QA_SUBDIR


def qa_paths(base_dir: Optional[Path] = None) -> Dict[str, Path]:
    d = qa_dir(base_dir)
    return {
        "qa_dir": d,
        "report_path": d / QA_REPORT_FILENAME,
        "log_path": d / "qa.log",
    }


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _json_dumps_deterministic(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    ensure_dir(path.parent)
    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as f:
            f.write(text)
        fd = None
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, _json_dumps_deterministic(data), encoding="utf-8")


def append_log(log_path: Path, message: str) -> None:
    ensure_dir(log_path.parent)
    msg = message.rstrip("\n") + "\n"
    with open(log_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(msg)


def exit_code_for_status(status: str) -> int:
    return int(EXIT_CODES.get(status, EXIT_CODES[STATUS_ERROR]))


def minimal_report(
    status: str = STATUS_ERROR,
    mode: str = "unknown",
    summary: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": status,
        "mode": mode,
        "summary": summary,
        "checks": [],
        "errors": [],
        "warnings": [],
        "meta": {"schema_version": 1},
    }
    if details:
        payload["meta"].update(details)
    return payload


def always_write_report(
    report: Dict[str, Any],
    base_dir: Optional[Path] = None,
    log_lines: Optional[Tuple[str, ...]] = None,
) -> Dict[str, Path]:
    paths = qa_paths(base_dir)
    ensure_dir(paths["qa_dir"])
    if log_lines:
        for line in log_lines:
            append_log(paths["log_path"], line)
    atomic_write_json(paths["report_path"], report)
    return paths


def safe_finalize(
    report: Optional[Dict[str, Any]] = None,
    base_dir: Optional[Path] = None,
    log_lines: Optional[Tuple[str, ...]] = None,
) -> int:
    rep = report if isinstance(report, dict) else minimal_report()
    paths = always_write_report(rep, base_dir=base_dir, log_lines=log_lines)
    status = str(rep.get("status", STATUS_ERROR))
    append_log(paths["log_path"], f"final_status={status} exit_code={exit_code_for_status(status)}")
    return exit_code_for_status(status)
