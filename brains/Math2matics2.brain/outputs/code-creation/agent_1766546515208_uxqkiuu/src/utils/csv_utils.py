"""CSV helper utilities.

This module focuses on deterministic CSV generation:
- stable column ordering (explicit fieldnames preferred)
- canonical newlines (LF) regardless of platform
- deterministic writer settings (explicit lineterminator, no implicit extras)
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Iterable, Mapping, Sequence, Any, Optional, List, Dict, Union
def stable_fieldnames(
    fieldnames: Sequence[str],
    *,
    require_unique: bool = True,
) -> List[str]:
    """Return a validated, stable list of CSV columns.

    Args:
        fieldnames: Desired column order.
        require_unique: If True, raise on duplicates.

    Raises:
        ValueError: If fieldnames is empty or contains duplicates.
    """
    cols = list(fieldnames)
    if not cols:
        raise ValueError("fieldnames must be a non-empty sequence")
    if require_unique:
        seen = set()
        dups = [c for c in cols if (c in seen) or seen.add(c)]
        if dups:
            raise ValueError(f"duplicate fieldnames not allowed: {sorted(set(dups))}")
    return cols
def coerce_row(
    row: Mapping[str, Any],
    fieldnames: Sequence[str],
    *,
    missing: str = "",
    strict: bool = False,
) -> Dict[str, Any]:
    """Coerce a row mapping into a dict aligned to fieldnames.

    - Missing keys are filled with `missing`.
    - Extra keys are ignored by default; if strict=True they raise.

    Values are passed through as-is; the csv module will stringify them.
    """
    cols = stable_fieldnames(fieldnames)
    if strict:
        extra = set(row.keys()) - set(cols)
        if extra:
            raise ValueError(f"row has unexpected keys: {sorted(extra)}")
    out: Dict[str, Any] = {c: row.get(c, missing) for c in cols}
    return out
def render_csv_text(
    rows: Iterable[Mapping[str, Any]],
    fieldnames: Sequence[str],
    *,
    include_header: bool = True,
    missing: str = "",
    strict: bool = False,
) -> str:
    """Render rows to CSV text with canonical LF newlines.

    Determinism notes:
    - Column order is exactly `fieldnames`.
    - Line terminator is always '\n'.
    - DictWriter ignores extras unless strict=True via coerce_row.

    Returns:
        CSV content as a UTF-8 friendly Python string.
    """
    cols = stable_fieldnames(fieldnames)
    buf = io.StringIO(newline="")  # prevent universal-newline translation
    writer = csv.DictWriter(
        buf,
        fieldnames=cols,
        extrasaction="ignore",
        lineterminator="\n",
    )
    if include_header:
        writer.writeheader()
    for r in rows:
        writer.writerow(coerce_row(r, cols, missing=missing, strict=strict))
    return buf.getvalue()
def write_csv(
    path: Union[str, Path],
    rows: Iterable[Mapping[str, Any]],
    fieldnames: Sequence[str],
    *,
    include_header: bool = True,
    encoding: str = "utf-8",
    missing: str = "",
    strict: bool = False,
) -> None:
    """Write CSV deterministically to disk.

    This uses canonical LF newlines by opening with newline='\n' and
    writing CSV with lineterminator='\n'.

    Note: atomic writes are handled elsewhere (see fs utilities).
    """
    p = Path(path)
    text = render_csv_text(
        rows,
        fieldnames,
        include_header=include_header,
        missing=missing,
        strict=strict,
    )
    p.write_text(text, encoding=encoding, newline="\n")
