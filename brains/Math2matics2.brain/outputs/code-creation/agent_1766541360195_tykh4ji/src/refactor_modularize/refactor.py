"""refactor_modularize.refactor

A small, self-contained refactoring engine for Stage 1.

It detects repeated *verbatim* fragments across input artifacts (both documentation and
code-like text), extracts them into reusable modules, and rewrites the original
artifacts to reference the extracted modules.

Design notes:
- Fragment detection is conservative: only identical blocks after light normalization
  (trim + newline canonicalization) are deduplicated.
- Rewrites are deterministic and stable for the same inputs.
- This module does not perform I/O; callers pass/receive in-memory text.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


_INCLUDE_TOKEN = "<<module:{name}>>"
_CODE_FENCE_RE = re.compile(r"(^```[\w+-]*\n.*?^```\s*$)", re.M | re.S)
@dataclass(frozen=True)
class Artifact:
    """A single input file (code or documentation)."""

    name: str
    text: str
    kind: str = "text"  # e.g. "md", "py", "toml", "text"


@dataclass(frozen=True)
class Fragment:
    """A reusable fragment occurrence within an artifact."""

    artifact: str
    start: int
    end: int
    raw: str
    norm: str
    digest: str


@dataclass(frozen=True)
class RefactorResult:
    """Refactoring plan result.

    - rewritten: artifact name -> rewritten content
    - modules: module filename -> extracted content
    - index: module filename -> list of (artifact, start, end) occurrences
    """

    rewritten: Mapping[str, str]
    modules: Mapping[str, str]
    index: Mapping[str, Sequence[Tuple[str, int, int]]]
def _normalize_block(block: str) -> str:
    block = block.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in block.strip().split("\n")).strip() + "\n"


def _digest(norm: str) -> str:
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _split_paragraph_blocks(text: str) -> List[Tuple[int, int, str]]:
    # Split on 2+ newlines while keeping spans; skip tiny blocks.
    spans: List[Tuple[int, int, str]] = []
    text_n = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"\n{2,}", text_n)
    cursor = 0
    for part in parts:
        start = text_n.find(part, cursor)
        end = start + len(part)
        cursor = end
        if len(part.strip()) >= 40:
            spans.append((start, end, part))
    return spans


def extract_fragments(artifact: Artifact) -> List[Fragment]:
    """Extract candidate fragments from an artifact.

    Candidates include fenced code blocks (```...```) and paragraph-like blocks.
    """
    text = artifact.text
    frags: List[Fragment] = []
    for m in _CODE_FENCE_RE.finditer(text):
        raw = m.group(1)
        norm = _normalize_block(raw)
        frags.append(Fragment(artifact.name, m.start(1), m.end(1), raw, norm, _digest(norm)))
    for start, end, raw in _split_paragraph_blocks(text):
        norm = _normalize_block(raw)
        frags.append(Fragment(artifact.name, start, end, raw, norm, _digest(norm)))
    return frags
def _module_filename(kind: str, digest: str, n: int) -> str:
    ext = {"md": "md", "markdown": "md", "py": "py"}.get(kind.lower(), "txt")
    return f"module_{n:03d}_{digest[:10]}.{ext}"


def plan_refactor(artifacts: Sequence[Artifact], min_dupes: int = 2) -> RefactorResult:
    """Plan + apply refactor in one step for Stage 1.

    Deduplicates exact repeated fragments across artifacts and replaces each
    occurrence with a deterministic include token: ``<<module:FILE>>``.
    """
    all_frags: List[Fragment] = []
    for a in artifacts:
        all_frags.extend(extract_fragments(a))

    by_digest: Dict[str, List[Fragment]] = {}
    for f in all_frags:
        by_digest.setdefault(f.digest, []).append(f)

    # Keep only fragments that appear in >= min_dupes artifacts/occurrences.
    reusable = {d: fs for d, fs in by_digest.items() if len(fs) >= min_dupes}
    digests_sorted = sorted(reusable, key=lambda d: (-(len(reusable[d])), d))

    modules: Dict[str, str] = {}
    index: Dict[str, List[Tuple[str, int, int]]] = {}
    digest_to_module: Dict[str, str] = {}

    for i, d in enumerate(digests_sorted, start=1):
        fs = reusable[d]
        kind = next((a.kind for a in artifacts if a.name == fs[0].artifact), "text")
        fname = _module_filename(kind, d, i)
        digest_to_module[d] = fname
        modules[fname] = fs[0].norm
        index[fname] = [(f.artifact, f.start, f.end) for f in fs]

    rewritten: Dict[str, str] = {}
    frags_by_art: Dict[str, List[Fragment]] = {}
    for f in all_frags:
        if f.digest in digest_to_module:
            frags_by_art.setdefault(f.artifact, []).append(f)

    for a in artifacts:
        frs = sorted(frags_by_art.get(a.name, []), key=lambda f: (f.start, f.end))
        # Avoid overlapping replacements: keep earliest, then skip overlaps.
        kept: List[Fragment] = []
        last_end = -1
        for f in frs:
            if f.start >= last_end:
                kept.append(f)
                last_end = f.end
        out, pos = [], 0
        for f in kept:
            out.append(a.text[pos:f.start])
            out.append(_INCLUDE_TOKEN.format(name=digest_to_module[f.digest]))
            pos = f.end
        out.append(a.text[pos:])
        rewritten[a.name] = "".join(out)

    return RefactorResult(rewritten=rewritten, modules=modules, index=index)
