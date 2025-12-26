from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, List, Sequence


# Canonical artifact list (relative to repo root). Used to render outputs/index.md and for CI assertions.
CANONICAL_ARTIFACTS: Sequence[str] = (
    "outputs/roadmap.md",
    "outputs/bibliography.bib",
    "outputs/coverage_matrix.csv",
    "outputs/results.json",
    "outputs/figure.png",
    "outputs/test_logs.txt",
    "outputs/index.md",
)


@dataclass(frozen=True)
class Manifest:
    repo_root: Path

    def artifact_paths(self) -> List[Path]:
        seen = set()
        out: List[Path] = []
        for rel in CANONICAL_ARTIFACTS:
            if rel in seen:
                raise ValueError(f"Duplicate canonical artifact: {rel}")
            seen.add(rel)
            out.append(self.repo_root / rel)
        return out

    def render_index_md(self) -> str:
        lines = [
            "# Outputs Manifest",
            "",
            "This file is the canonical checklist of expected pipeline artifacts.",
            "",
            "## Expected artifacts",
            "",
        ]
        for rel in sorted(CANONICAL_ARTIFACTS):
            lines.append(f"- `{rel}`")
        lines.append("")
        return "\n".join(lines)

    def write_index_md(self) -> Path:
        index_path = self.repo_root / "outputs" / "index.md"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(self.render_index_md(), encoding="utf-8", newline="\n")
        return index_path

    def parse_index_md(self, text: str) -> List[str]:
        items: List[str] = []
        for line in text.splitlines():
            s = line.strip()
            if not s.startswith(("-", "*")):
                continue
            s = s.lstrip("-*").strip()
            if not s:
                continue
            m = re.match(r"`([^`]+)`", s)
            item = (m.group(1) if m else s).strip()
            if item:
                items.append(item)
        # Keep order but remove duplicates
        deduped: List[str] = []
        seen = set()
        for i in items:
            if i not in seen:
                seen.add(i)
                deduped.append(i)
        return deduped

    def read_index_entries(self) -> List[str]:
        index_path = self.repo_root / "outputs" / "index.md"
        text = index_path.read_text(encoding="utf-8")
        return self.parse_index_md(text)


def canonical_artifacts() -> List[str]:
    return list(CANONICAL_ARTIFACTS)


def write_outputs_index(repo_root: Path) -> Path:
    return Manifest(repo_root=repo_root).write_index_md()


def expected_artifacts_from_index(repo_root: Path) -> List[Path]:
    m = Manifest(repo_root=repo_root)
    rels = m.read_index_entries()
    return [repo_root / r for r in rels]
