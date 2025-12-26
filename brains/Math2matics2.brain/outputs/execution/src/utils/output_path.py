from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional, Union


_ENV_KEYS: tuple[str, ...] = ("OUTPUT_DIR", "COSMO_OUTPUT_DIR", "ARTIFACTS_DIR")


def _env_output_dir() -> Optional[str]:
    for k in _ENV_KEYS:
        v = os.getenv(k)
        if v and v.strip():
            return v.strip()
    return None


def _normalize_outputs_root(p: Path) -> Path:
    # Avoid producing absolute /outputs paths (often unwritable and non-portable).
    # If user explicitly sets /outputs (or /outputs/...), map to a relative ./outputs[/...].
    try:
        if p.is_absolute():
            parts = p.parts
            if len(parts) >= 2 and parts[1] == "outputs":
                rel = Path(*parts[1:])  # "outputs[/...]"
                return Path(".") / rel
    except Exception:
        pass
    return p


def get_output_dir() -> Path:
    v = _env_output_dir()
    base = Path(v) if v else Path("./outputs")
    base = _normalize_outputs_root(base).expanduser()
    return base


OUTPUT_DIR: Path = get_output_dir()


Pathish = Union[str, Path]


def output_path(*parts: Pathish, mkdir: bool = False) -> Path:
    p = OUTPUT_DIR
    for part in parts:
        if part is None:
            continue
        part_p = Path(part)
        if part_p.is_absolute():
            raise ValueError(f"Absolute path component not allowed for output_path(): {part_p}")
        p = p / part_p
    if mkdir:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def ensure_dir(path: Pathish) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_absolute_outputs_path(value: Pathish) -> bool:
    try:
        s = str(value)
    except Exception:
        return False
    return s == "/outputs" or s.startswith("/outputs/")


def forbid_absolute_outputs(value: Pathish, what: str = "path") -> None:
    if is_absolute_outputs_path(value):
        raise ValueError(f"Forbidden absolute /outputs reference in {what}: {value}")


def rel_to_output(path: Pathish) -> Path:
    p = Path(path)
    try:
        return p.relative_to(OUTPUT_DIR)
    except Exception:
        return p


def as_posix(path: Pathish) -> str:
    return Path(path).as_posix()
