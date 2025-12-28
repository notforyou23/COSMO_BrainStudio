"""Utilities for loading and managing historical prompt artifacts.

A prompt artifact is typically a timestamped *_prompt.txt file produced during
generation (e.g., 2025-12-28T00-10-33-623Z_src_customer_discovery_outputs_py_stage1_attempt1_prompt.txt).
This module provides small, testable helpers to discover, parse, and load them.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional, Sequence, Dict, Any
import re

_TIMESTAMP_RE = re.compile(r'^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z)_')
_STAGE_RE = re.compile(r'_stage(?P<stage>\d+)')
_ATTEMPT_RE = re.compile(r'_attempt(?P<attempt>\d+)')
@dataclass(frozen=True)
class PromptArtifact:
    path: Path
    timestamp: Optional[str] = None
    scope: Optional[str] = None
    stage: Optional[int] = None
    attempt: Optional[int] = None
    kind: str = "prompt"

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def text(self) -> str:
        return load_text(self.path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "timestamp": self.timestamp,
            "scope": self.scope,
            "stage": self.stage,
            "attempt": self.attempt,
            "kind": self.kind,
        }
def normalize_text(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in s.split("\n")]
    out = "\n".join(lines).strip()
    return out + ("\n" if out else "")


def load_text(path: Path, encoding: str = "utf-8") -> str:
    return normalize_text(path.read_text(encoding=encoding))


def _de_ts(name: str) -> str:
    m = _TIMESTAMP_RE.match(name)
    return name[m.end():] if m else name


def parse_artifact_filename(name: str) -> Dict[str, Any]:
    base = name[:-4] if name.endswith(".txt") else name
    ts = None
    m = _TIMESTAMP_RE.match(base)
    if m:
        ts = m.group("ts")
    rest = _de_ts(base)
    kind = "prompt" if rest.endswith("_prompt") else "artifact"
    stage = None
    attempt = None
    sm = _STAGE_RE.search(rest)
    if sm:
        stage = int(sm.group("stage"))
    am = _ATTEMPT_RE.search(rest)
    if am:
        attempt = int(am.group("attempt"))
    scope = rest
    if rest.endswith("_prompt"):
        scope = rest[:-7]
    return {"timestamp": ts, "scope": scope, "stage": stage, "attempt": attempt, "kind": kind}
def is_prompt_artifact(path: Path) -> bool:
    n = path.name
    return path.is_file() and n.endswith("_prompt.txt") and bool(_TIMESTAMP_RE.match(n) or "_stage" in n or "_attempt" in n)


def discover_prompt_artifacts(
    root: Path,
    *,
    recursive: bool = True,
    include_non_timestamped: bool = True,
) -> Sequence[PromptArtifact]:
    if not root.exists():
        return []
    globber = root.rglob if recursive else root.glob
    paths = [p for p in globber("*_prompt.txt") if p.is_file()]
    if not include_non_timestamped:
        paths = [p for p in paths if _TIMESTAMP_RE.match(p.name)]
    artifacts: list[PromptArtifact] = []
    for p in sorted(paths, key=lambda x: x.name):
        meta = parse_artifact_filename(p.name)
        artifacts.append(PromptArtifact(path=p, **meta))
    return artifacts


def best_artifact(
    artifacts: Sequence[PromptArtifact],
    *,
    scope: Optional[str] = None,
    stage: Optional[int] = None,
    attempt: Optional[int] = None,
    key: Optional[Callable[[PromptArtifact], Any]] = None,
) -> Optional[PromptArtifact]:
    cand = list(artifacts)
    if scope is not None:
        cand = [a for a in cand if a.scope == scope]
    if stage is not None:
        cand = [a for a in cand if a.stage == stage]
    if attempt is not None:
        cand = [a for a in cand if a.attempt == attempt]
    if not cand:
        return None
    if key is None:
        key = lambda a: (a.timestamp or "", a.stage or -1, a.attempt or -1, a.name)
    return sorted(cand, key=key)[-1]
class PromptArtifactStore:
    """Small convenience wrapper for discovery + lookup."""

    def __init__(self, root: Path, *, recursive: bool = True) -> None:
        self.root = root
        self.recursive = recursive
        self._artifacts: Optional[Sequence[PromptArtifact]] = None

    def refresh(self) -> Sequence[PromptArtifact]:
        self._artifacts = discover_prompt_artifacts(self.root, recursive=self.recursive)
        return self._artifacts

    @property
    def artifacts(self) -> Sequence[PromptArtifact]:
        return self._artifacts if self._artifacts is not None else self.refresh()

    def find(
        self,
        *,
        scope: Optional[str] = None,
        stage: Optional[int] = None,
        attempt: Optional[int] = None,
    ) -> Optional[PromptArtifact]:
        return best_artifact(self.artifacts, scope=scope, stage=stage, attempt=attempt)

    def iter_texts(
        self,
        *,
        scope: Optional[str] = None,
        stage: Optional[int] = None,
    ) -> Iterator[str]:
        for a in self.artifacts:
            if scope is not None and a.scope != scope:
                continue
            if stage is not None and a.stage != stage:
                continue
            yield a.text
