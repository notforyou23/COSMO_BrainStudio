"""Artifact helpers for the minimal pipeline.

This module focuses on deterministic, test-friendly artifact creation:
- ensure an outputs directory exists
- write canonical JSON (stable formatting + sorted keys)
- append structured log lines (JSONL) deterministically
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping
import json
import os
@dataclass(frozen=True)
class ArtifactPaths:
    """Convenience container for common artifact file locations."""

    outputs_dir: Path

    @property
    def run_stamp_json(self) -> Path:
        return self.outputs_dir / "run_stamp.json"

    @property
    def run_log(self) -> Path:
        return self.outputs_dir / "run.log"
def ensure_outputs_dir(
    root: Path | None = None,
    dirname: str = "outputs",
    env_var: str = "MINIPIPELINE_OUTPUTS_DIR",
) -> Path:
    """Return an outputs directory path and create it if necessary.

    Resolution order:
      1) explicit env var (defaults to MINIPIPELINE_OUTPUTS_DIR)
      2) provided *root* / *dirname*
      3) current working directory / *dirname*
    """
    env_val = os.environ.get(env_var)
    if env_val:
        out = Path(env_val)
    else:
        base = root if root is not None else Path.cwd()
        out = base / dirname
    out.mkdir(parents=True, exist_ok=True)
    return out
def _canonical_json_bytes(obj: Any) -> bytes:
    """Serialize *obj* to canonical JSON bytes (stable across runs)."""
    text = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (text + "\n").encode("utf-8")
def write_json(path: Path, data: Any) -> Path:
    """Write canonical JSON to *path*, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(data))
    return path
def append_log_line(path: Path, record: Mapping[str, Any]) -> Path:
    """Append a canonical JSON log line (JSONL) to *path*.

    The caller should supply any timestamps/sequence numbers to keep the
    content deterministic. Keys are sorted and formatting is stable.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as f:
        f.write(_canonical_json_bytes(dict(record)))
    return path
def merge_defaults(
    payload: MutableMapping[str, Any], defaults: Mapping[str, Any]
) -> MutableMapping[str, Any]:
    """Update *payload* with values from *defaults* only when missing."""
    for k, v in defaults.items():
        payload.setdefault(k, v)
    return payload
def artifact_paths(root: Path | None = None) -> ArtifactPaths:
    """Return common artifact paths rooted at the resolved outputs dir."""
    return ArtifactPaths(outputs_dir=ensure_outputs_dir(root=root))
