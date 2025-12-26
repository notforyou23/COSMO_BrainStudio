from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


class OutputPathMixin:
    """
    Shared adapter for writer modules to resolve output locations consistently.

    Usage note:
        - Prefer `self.output_path("subdir", "file.ext")` for artifact paths.
        - Use `self.ensure_output_dir("subdir")` before writing.
        - The concrete output base directory is controlled by the central helper
          in `src/output_path.py` (default: ./outputs; override via env var).

    This mixin intentionally delegates all output location logic to
    `output_path.py` to avoid hard-coded absolute paths like "/outputs/...".
    """

    output_namespace: str = ""

    def _output_mod(self):
        try:
            from .. import output_path as _op  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "OutputPathMixin requires src/output_path.py. "
                "Ensure the central output-path helper is available."
            ) from e
        return _op

    def output_dir(self, *parts: str | Path, namespace: Optional[str] = None) -> Path:
        """
        Return an output directory path derived from the central helper.
        The directory is not created automatically; call ensure_output_dir().
        """
        ns = (self.output_namespace or "").strip("/")
        if namespace is not None:
            ns = namespace.strip("/")
        base_parts: tuple[Any, ...] = (ns,) if ns else ()
        return self._output_mod().output_dir(*base_parts, *parts)

    def ensure_output_dir(self, *parts: str | Path, namespace: Optional[str] = None) -> Path:
        """Ensure and return an output directory derived from the central helper."""
        ns = (self.output_namespace or "").strip("/")
        if namespace is not None:
            ns = namespace.strip("/")
        base_parts: tuple[Any, ...] = (ns,) if ns else ()
        return self._output_mod().ensure_output_dir(*base_parts, *parts)

    def output_path(self, *parts: str | Path, namespace: Optional[str] = None) -> Path:
        """
        Return an artifact path under the output directory derived from the helper.
        Does not create parent directories; call ensure_output_dir() as needed.
        """
        ns = (self.output_namespace or "").strip("/")
        if namespace is not None:
            ns = namespace.strip("/")
        base_parts: tuple[Any, ...] = (ns,) if ns else ()
        return self._output_mod().output_path(*base_parts, *parts)

    def ensure_parent_dir(self, path: str | Path) -> Path:
        """
        Ensure the parent directory for `path` exists and return the Path.
        Use this for non-output paths (e.g., temp/debug) when necessary.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


@dataclass(frozen=True)
class OutputLocation:
    """
    Small convenience wrapper used by some writers to carry an output path.
    """
    path: Path

    def ensure_parent(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return self.path
