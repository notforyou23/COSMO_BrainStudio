from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Union

__all__ = [
    "utcnow",
    "as_utc",
    "isoformat_utc",
    "utc_iso8601_now",
    "parse_utc_iso8601",
]


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """Return a timezone-aware UTC datetime (naive inputs are treated as UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def isoformat_utc(dt: datetime, timespec: str = "milliseconds") -> str:
    """Format a datetime as ISO8601 UTC with a trailing 'Z' (e.g., 2025-01-02T03:04:05.678Z)."""
    dtu = as_utc(dt)
    s = dtu.isoformat(timespec=timespec)
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    return s


def utc_iso8601_now(timespec: str = "milliseconds") -> str:
    """Return current UTC time as ISO8601 with trailing 'Z'."""
    return isoformat_utc(utcnow(), timespec=timespec)


def parse_utc_iso8601(value: Union[str, datetime]) -> datetime:
    """Parse an ISO8601 timestamp and return a timezone-aware UTC datetime.

    Accepts:
      - '...Z' (UTC)
      - '...+00:00' or other offsets
      - datetime objects (naive treated as UTC)
    """
    if isinstance(value, datetime):
        return as_utc(value)

    if not isinstance(value, str):
        raise TypeError(f"Expected str or datetime, got {type(value).__name__}")

    s = value.strip()
    if not s:
        raise ValueError("Empty timestamp string")

    # datetime.fromisoformat does not accept trailing 'Z' in some Python versions.
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"Invalid ISO8601 timestamp: {value!r}") from e

    return as_utc(dt)
