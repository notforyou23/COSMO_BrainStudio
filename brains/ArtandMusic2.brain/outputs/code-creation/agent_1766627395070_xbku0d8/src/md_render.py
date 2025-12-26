from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple, Union


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _escape_cell(value: object) -> str:
    s = "" if value is None else str(value)
    s = normalize_newlines(s).replace("|", "\\|")
    s = " ".join(s.split())
    return s


def code_span(text: str) -> str:
    t = "" if text is None else str(text)
    if "`" not in t:
        return f"`{t}`"
    ticks = "`" * (max((len(x) for x in t.split("`")), default=1) + 1)
    return f"{ticks}{t}{ticks}"


def heading(level: int, title: str) -> str:
    lvl = max(1, min(int(level), 6))
    t = " ".join((title or "").split()).strip()
    return f"{'#' * lvl} {t}" if t else f"{'#' * lvl}"


def anchor(section_id: str) -> str:
    sid = (section_id or "").strip()
    if not sid:
        raise ValueError("section_id must be non-empty")
    if any(c in sid for c in ['"', "<", ">", "&"]):
        raise ValueError("section_id contains invalid characters")
    return f'<a id="{sid}"></a>'


def anchored_heading(level: int, title: str, section_id: str) -> str:
    return "\n".join([heading(level, title), anchor(section_id)])


def bullet_list(items: Iterable[str], indent: int = 0) -> str:
    pref = " " * max(0, int(indent))
    out: List[str] = []
    for it in items:
        s = " ".join((it or "").split()).strip()
        out.append(f"{pref}- {s}" if s else f"{pref}-")
    return "\n".join(out)


def checklist(items: Iterable[Union[str, Tuple[str, bool]]], indent: int = 0) -> str:
    pref = " " * max(0, int(indent))
    out: List[str] = []
    for it in items:
        if isinstance(it, tuple):
            text, checked = it[0], bool(it[1])
        else:
            text, checked = it, False
        s = " ".join((text or "").split()).strip()
        mark = "x" if checked else " "
        out.append(f"{pref}- [{mark}] {s}" if s else f"{pref}- [{mark}]")
    return "\n".join(out)


def table(headers: Sequence[object], rows: Sequence[Sequence[object]], aligns: Optional[Sequence[str]] = None) -> str:
    hs = [_escape_cell(h) for h in headers]
    al = list(aligns) if aligns is not None else ["l"] * len(hs)
    if len(al) != len(hs):
        raise ValueError("aligns must match header length")
    def sep(a: str) -> str:
        a = (a or "l").lower()
        if a in ("c", "center"):
            return ":---:"
        if a in ("r", "right"):
            return "---:"
        return ":---" if a in ("l", "left") else "---"
    lines = ["| " + " | ".join(hs) + " |", "| " + " | ".join(sep(a) for a in al) + " |"]
    for r in rows:
        cells = [_escape_cell(c) for c in r]
        if len(cells) < len(hs):
            cells += [""] * (len(hs) - len(cells))
        elif len(cells) > len(hs):
            cells = cells[: len(hs)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    level: int
    children: Tuple["Section", ...] = ()


def section_skeleton(sections: Sequence[Union[Section, Mapping[str, object]]], base_level: int = 1) -> str:
    def to_section(x: Union[Section, Mapping[str, object]]) -> Section:
        if isinstance(x, Section):
            return x
        m = dict(x)
        ch = tuple(to_section(c) for c in (m.get("children") or ()))
        return Section(id=str(m.get("id") or ""), title=str(m.get("title") or ""), level=int(m.get("level") or 1), children=ch)
    root = [to_section(s) for s in sections]

    blocks: List[str] = []
    def walk(s: Section, parent_delta: int = 0) -> None:
        lvl = max(1, min(6, int(base_level) + int(s.level) - 1 + parent_delta))
        blocks.append(anchored_heading(lvl, s.title, s.id))
        blocks.append("")
        for c in s.children:
            walk(c, parent_delta=0)
    for s in root:
        walk(s)
    text = "\n".join(blocks).rstrip() + "\n"
    return text
