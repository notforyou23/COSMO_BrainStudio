"""Tool version utilities.

This module defines the canonical version string for the project and small helpers
to stamp structured logs with consistent tool identity fields.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping, MutableMapping, Optional


TOOL_NAME = "generated_cli_tool_1766726690727"
__version__ = "0.1.0"


def get_version() -> str:
    """Return the canonical tool version string."""
    return __version__


@dataclass(frozen=True)
class ToolInfo:
    """Serializable tool identity metadata."""

    name: str = TOOL_NAME
    version: str = __version__

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def tool_info() -> ToolInfo:
    """Return tool identity information."""
    return ToolInfo()


def stamp_tool_info(record: MutableMapping[str, Any], *, key: str = "tool") -> MutableMapping[str, Any]:
    """Ensure a structured log record includes tool identity fields.

    The tool info is written to record[key] as a dict with 'name' and 'version'.
    If record already has a mapping at record[key], it is updated (not replaced).
    """
    info = tool_info().to_dict()
    existing = record.get(key)
    if isinstance(existing, Mapping):
        merged = dict(existing)
        merged.setdefault("name", info["name"])
        merged.setdefault("version", info["version"])
        record[key] = merged
    else:
        record[key] = info
    return record


def build_run_log(
    *,
    inputs: Optional[Mapping[str, Any]] = None,
    outputs: Optional[Mapping[str, Any]] = None,
    exit_code: Optional[int] = None,
    command: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Create a minimal structured run log including tool identity."""
    record: dict[str, Any] = {}
    stamp_tool_info(record)
    if inputs is not None:
        record["inputs"] = dict(inputs)
    if outputs is not None:
        record["outputs"] = dict(outputs)
    if exit_code is not None:
        record["exit_code"] = int(exit_code)
    if command is not None:
        record["command"] = list(command)
    return record


__all__ = [
    "TOOL_NAME",
    "__version__",
    "ToolInfo",
    "get_version",
    "tool_info",
    "stamp_tool_info",
    "build_run_log",
]
