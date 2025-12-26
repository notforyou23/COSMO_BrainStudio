"""Timestamp helpers for artifact metadata.

Provides UTC-aware datetime utilities and stable ISO8601 formatting suitable
for results.json metadata fields (e.g., created_at, start_time, end_time).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
def utc_now() -> datetime:
    """Return current time as timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC.

    Naive datetimes are assumed to already represent UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
def isoformat_utc(dt: Optional[datetime] = None, *, timespec: str = "milliseconds") -> str:
    """Format a datetime (or now) as ISO8601 UTC with trailing 'Z'.

    Examples:
        2025-12-24T04:22:12.374Z
        2025-12-24T04:22:12Z
    """
    dt_utc = ensure_utc(utc_now() if dt is None else dt)

    # datetime.isoformat supports timespec for stable subsecond precision.
    s = dt_utc.isoformat(timespec=timespec)
    # Normalize +00:00 to Z.
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    elif s.endswith("00:00") and ("+" in s or "-" in s):
        # Preserve non-UTC offsets if somehow present (shouldn't happen here).
        pass
    elif dt_utc.tzinfo is timezone.utc and not s.endswith("Z"):
        # Some Python builds may omit offset for UTC; force Z.
        s += "Z"
    return s
def parse_isoformat_utc(value: str) -> datetime:
    """Parse an ISO8601 timestamp into an aware UTC datetime.

    Accepts:
      - ...Z (UTC)
      - ...+00:00 (UTC offset)
      - Naive timestamps (assumed UTC)
    """
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    return ensure_utc(dt)
def utc_epoch_millis(dt: Optional[datetime] = None) -> int:
    """Return milliseconds since Unix epoch for a UTC datetime (or now)."""
    dt_utc = ensure_utc(utc_now() if dt is None else dt)
    return int(dt_utc.timestamp() * 1000)
