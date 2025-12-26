from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional
import hashlib
import re


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def slugify(text: str, max_len: int = 48) -> str:
    t = _norm_ws(text).lower()
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    t = re.sub(r"[\s_-]+", "-", t).strip("-")
    return (t[:max_len].rstrip("-")) or "section"


def stable_id(path_titles: Iterable[str], salt: str = "outline.v1", n: int = 10) -> str:
    canon = "|".join(_norm_ws(x).lower() for x in path_titles)
    h = hashlib.sha256((salt + "|" + canon).encode("utf-8")).hexdigest()[:n]
    return f"s{h}"


@dataclass(frozen=True)
class Section:
    title: str
    children: List["Section"] = field(default_factory=list)
    notes: Optional[str] = None

    def with_ids(self, parent_titles: Optional[List[str]] = None) -> "SectionWithID":
        parent_titles = list(parent_titles or [])
        titles = parent_titles + [self.title]
        sid = stable_id(titles)
        kid = [c.with_ids(titles) for c in self.children]
        return SectionWithID(id=sid, title=self.title, children=kid, notes=self.notes)


@dataclass(frozen=True)
class SectionWithID:
    id: str
    title: str
    children: List["SectionWithID"] = field(default_factory=list)
    notes: Optional[str] = None

    def iter(self) -> Iterable["SectionWithID"]:
        yield self
        for c in self.children:
            yield from c.iter()


@dataclass(frozen=True)
class Outline:
    title: str
    sections: List[Section] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def with_ids(self) -> "OutlineWithIDs":
        w = [s.with_ids([self.title]) for s in self.sections]
        return OutlineWithIDs(title=self.title, sections=w, meta=dict(self.meta))


@dataclass(frozen=True)
class OutlineWithIDs:
    title: str
    sections: List[SectionWithID] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def iter_sections(self) -> Iterable[SectionWithID]:
        for s in self.sections:
            yield from s.iter()


def heading(level: int, text: str) -> str:
    lvl = max(1, min(6, int(level)))
    return f"{'#' * lvl} {_norm_ws(text)}"


def anchor(sid: str) -> str:
    return f'<a id="{sid}"></a>'


def _render_sections_outline(sections: List[SectionWithID], level: int = 2) -> List[str]:
    out: List[str] = []
    for s in sections:
        out.append(f"{heading(level, s.title)} ({s.id})")
        if s.notes:
            out.append(_norm_ws(s.notes))
        if s.children:
            out.extend(_render_sections_outline(s.children, level + 1))
    return out


def render_report_outline_md(outline: OutlineWithIDs) -> str:
    lines: List[str] = [heading(1, "REPORT_OUTLINE"), "", f"**Report Title:** {outline.title}"]
    if outline.meta:
        keys = sorted(outline.meta.keys())
        lines.append("")
        lines.append("**Metadata:**")
        for k in keys:
            lines.append(f"- **{k}**: {outline.meta[k]}")
    lines.append("")
    lines.extend(_render_sections_outline(outline.sections, level=2))
    return "\n".join(lines).rstrip() + "\n"


def _render_plan_sections(sections: List[SectionWithID], level: int = 3) -> List[str]:
    out: List[str] = []
    for s in sections:
        out.append(heading(level, s.title))
        out.append(f"- Section ID: `{s.id}`")
        out.append(f"- Anchor: `{anchor(s.id)}`")
        out.append("- Purpose:")
        out.append("- Inputs:")
        out.append("- Outputs:")
        out.append("- Acceptance criteria:")
        out.append("")
        if s.children:
            out.extend(_render_plan_sections(s.children, level + 1))
    return out


def render_plan_project_scope_and_outline_md(outline: OutlineWithIDs) -> str:
    lines: List[str] = [
        heading(1, "plan_project_scope_and_outline"),
        "",
        f"**Canonical Report Title:** {outline.title}",
        "",
        "This plan is generated from the canonical outline schema; section IDs and anchors are deterministic from the title path.",
        "",
        heading(2, "Scope"),
        "- Intended audience:",
        "- Research questions:",
        "- Assumptions & constraints:",
        "",
        heading(2, "Outline-to-Deliverables Mapping"),
        "- `REPORT_OUTLINE.md` uses the same section titles and IDs.",
        "- `DRAFT_REPORT_v0.md` uses the same IDs as HTML anchors for stable referencing.",
        "",
        heading(2, "Section Plan"),
        "",
    ]
    lines.extend(_render_plan_sections(outline.sections, level=3))
    return "\n".join(lines).rstrip() + "\n"


def _render_draft_skeleton(sections: List[SectionWithID], level: int = 2) -> List[str]:
    out: List[str] = []
    for s in sections:
        out.append(anchor(s.id))
        out.append(heading(level, s.title))
        out.append("")
        out.append("> Notes:")
        out.append("> -")
        out.append("")
        out.append("Content:")
        out.append("")
        if s.children:
            out.extend(_render_draft_skeleton(s.children, level + 1))
    return out


def render_draft_report_skeleton_md(outline: OutlineWithIDs) -> str:
    lines: List[str] = [
        heading(1, outline.title),
        "",
        f"_Deterministic outline ID salt: `outline.v1`_",
        "",
        "## Table of Contents",
        "",
    ]
    for s in outline.sections:
        lines.append(f"- [{s.title}](#{s.id})")
    lines.append("")
    lines.extend(_render_draft_skeleton(outline.sections, level=2))
    return "\n".join(lines).rstrip() + "\n"
