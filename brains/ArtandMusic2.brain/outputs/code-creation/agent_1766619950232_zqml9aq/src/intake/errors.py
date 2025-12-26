from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union


class Severity(str, Enum):
    BLOCKING = "blocking"
    WARNING = "warning"


class ErrorCode(str, Enum):
    MISSING_FIELD = "missing_field"
    INVALID_VALUE = "invalid_value"
    TYPE_MISMATCH = "type_mismatch"
    CONFLICT = "conflict"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    CHECKLIST_VALIDATION_FAILED = "checklist_validation_failed"


Json = Dict[str, Any]
@dataclass(frozen=True)
class IntakeError:
    code: Union[ErrorCode, str]
    message: str
    path: str = ""
    severity: Union[Severity, str] = Severity.BLOCKING
    meta: Json = field(default_factory=dict)

    def to_dict(self) -> Json:
        code = self.code.value if isinstance(self.code, Enum) else str(self.code)
        severity = self.severity.value if isinstance(self.severity, Enum) else str(self.severity)
        out: Json = {"code": code, "severity": severity, "message": self.message}
        if self.path:
            out["path"] = self.path
        if self.meta:
            out["meta"] = self.meta
        return out

    def __str__(self) -> str:
        p = f" at {self.path}" if self.path else ""
        c = self.code.value if isinstance(self.code, Enum) else str(self.code)
        return f"[{c}] {self.message}{p}
class IntakeValidationError(ValueError):
    """Raised when intake validation produces one or more blocking failures."""

    def __init__(self, errors: Sequence[IntakeError], summary: str = "Intake validation failed"):
        self.errors: List[IntakeError] = list(errors)
        super().__init__(summary)

    def to_dict(self) -> Json:
        return {"ok": False, "error": str(self), "errors": [e.to_dict() for e in self.errors]}

    def format_text(self, max_lines: int = 50) -> str:
        return format_errors_text(self.errors, header=str(self), max_lines=max_lines)
def _join_path(base: str, field: str) -> str:
    if not base:
        return field
    if not field:
        return base
    if field.startswith("["):
        return f"{base}{field}"
    return f"{base}.{field}"


def missing_field(path: str, field: str = "", message: Optional[str] = None, *, meta: Optional[Json] = None) -> IntakeError:
    p = _join_path(path, field)
    msg = message or f"Missing required field: {p}" if p else "Missing required field"
    return IntakeError(code=ErrorCode.MISSING_FIELD, message=msg, path=p, severity=Severity.BLOCKING, meta=meta or {})


def invalid_value(path: str, message: str, *, code: Union[ErrorCode, str] = ErrorCode.INVALID_VALUE, meta: Optional[Json] = None) -> IntakeError:
    return IntakeError(code=code, message=message, path=path, severity=Severity.BLOCKING, meta=meta or {})


def type_mismatch(path: str, expected: str, actual: Any, *, meta: Optional[Json] = None) -> IntakeError:
    a = type(actual).__name__
    m = {"expected": expected, "actual": a}
    if meta:
        m.update(meta)
    return IntakeError(code=ErrorCode.TYPE_MISMATCH, message=f"Type mismatch: expected {expected}, got {a}", path=path, severity=Severity.BLOCKING, meta=m)
def ensure_blocking(errors: Iterable[Union[IntakeError, Json, str]]) -> List[IntakeError]:
    out: List[IntakeError] = []
    for e in errors:
        if isinstance(e, IntakeError):
            out.append(e)
        elif isinstance(e, str):
            out.append(IntakeError(code=ErrorCode.CHECKLIST_VALIDATION_FAILED, message=e))
        elif isinstance(e, dict):
            out.append(
                IntakeError(
                    code=e.get("code", ErrorCode.CHECKLIST_VALIDATION_FAILED),
                    message=e.get("message", "Validation error"),
                    path=e.get("path", ""),
                    severity=e.get("severity", Severity.BLOCKING),
                    meta=e.get("meta") or {},
                )
            )
        else:
            out.append(IntakeError(code=ErrorCode.CHECKLIST_VALIDATION_FAILED, message=str(e)))
    return out


def raise_if_blocking(errors: Sequence[IntakeError], summary: str = "Intake validation failed") -> None:
    blocking = [e for e in errors if (e.severity == Severity.BLOCKING or str(e.severity) == Severity.BLOCKING.value)]
    if blocking:
        raise IntakeValidationError(blocking, summary=summary)
def format_errors_text(errors: Sequence[IntakeError], header: str = "Validation errors", max_lines: int = 50) -> str:
    lines: List[str] = [header]
    for i, e in enumerate(errors[:max_lines], start=1):
        d = e.to_dict()
        loc = f" ({d['path']})" if d.get("path") else ""
        lines.append(f"{i}. {d['severity']}:{d['code']}{loc} - {d['message']}")
    extra = len(errors) - min(len(errors), max_lines)
    if extra > 0:
        lines.append(f"... and {extra} more")
    return "\n".join(lines)


def format_errors_json(errors: Sequence[IntakeError]) -> Json:
    return {"ok": False, "errors": [e.to_dict() for e in errors]}
