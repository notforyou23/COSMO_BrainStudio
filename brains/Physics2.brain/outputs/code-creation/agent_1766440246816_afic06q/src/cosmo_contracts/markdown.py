"""cosmo_contracts.markdown

Small, dependency-free helpers for generating Markdown text.

The project uses these helpers at runtime (e.g., CLI output and reports), so this
module must be import-safe and free of heavy dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple, Union


__all__ = [
    "escape_markdown",
    "heading",
    "paragraph",
    "bullet_list",
    "code_block",
    "inline_code",
    "link",
    "blockquote",
    "table",
    "join_blocks",
    "KeyValue",
    "key_value_table",
]
def escape_markdown(text: str) -> str:
    """Escape characters that commonly affect Markdown rendering.

    This is intentionally conservative: it escapes characters that are frequently
    interpreted by common Markdown renderers (GitHub-flavored Markdown).
    """
    if text is None:
        return ""
    # Backslash first, then other specials.
    specials = r"\\`*_{}\[\]()#+\-.!|>"
    out: List[str] = []
    for ch in str(text):
        if ch == "\\":  # already special-cased
            out.append("\\\\")
        elif ch in "`*_{}[]()#+-.!|>":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)
def heading(text: str, level: int = 1) -> str:
    """Return a Markdown heading."""
    lvl = 1 if level is None else int(level)
    lvl = 1 if lvl < 1 else (6 if lvl > 6 else lvl)
    return f"{'#' * lvl} {text}".rstrip()


def paragraph(text: str) -> str:
    """Normalize a string to a single Markdown paragraph."""
    if text is None:
        return ""
    # Collapse internal whitespace/newlines while keeping intentional spaces.
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    return " ".join(lines)


def inline_code(code: str) -> str:
    """Format inline code, choosing a delimiter that doesn't conflict."""
    s = "" if code is None else str(code)
    # If code contains backticks, use longer runs.
    max_run = 0
    run = 0
    for ch in s:
        if ch == "`":
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    delim = "`" * (max_run + 1 or 1)
    return f"{delim}{s}{delim}"
def code_block(code: str, language: str = "") -> str:
    """Return a fenced Markdown code block.

    If the code contains triple backticks, a longer fence is chosen.
    """
    s = "" if code is None else str(code)
    # Choose a fence longer than any backtick run in the code.
    max_run = 0
    run = 0
    for ch in s:
        if ch == "`":
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    fence = "`" * max(3, max_run + 1)
    lang = (language or "").strip()
    header = f"{fence}{lang}".rstrip()
    return "\n".join([header, s.rstrip("\n"), fence])
def bullet_list(items: Iterable[str], ordered: bool = False, start: int = 1) -> str:
    """Render a Markdown list from items."""
    if items is None:
        return ""
    lines: List[str] = []
    n = int(start) if ordered else 0
    for item in items:
        if item is None:
            continue
        txt = str(item).strip()
        if not txt:
            continue
        if ordered:
            lines.append(f"{n}. {txt}")
            n += 1
        else:
            lines.append(f"- {txt}")
    return "\n".join(lines)


def link(label: str, url: str) -> str:
    """Return a Markdown link."""
    return f"[{label}]({url})"


def blockquote(text: str) -> str:
    """Return a Markdown blockquote."""
    if text is None:
        return ""
    lines = str(text).splitlines() or [""]
    return "\n".join([f"> {ln}" if ln else ">" for ln in lines])
def _format_cell(value: object) -> str:
    s = "" if value is None else str(value)
    # Keep tables readable: escape pipes and collapse newlines.
    s = s.replace("|", "\\|")
    s = " ".join(ln.strip() for ln in s.splitlines() if ln.strip())
    return s


def table(
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    align: Optional[Sequence[str]] = None,
) -> str:
    """Render a simple GitHub-flavored Markdown table.

    align may contain 'left', 'right', 'center' entries (case-insensitive).
    """
    hdr = [str(h) for h in (headers or ())]
    if not hdr:
        return ""
    ncol = len(hdr)
    def norm_align(a: str) -> str:
        a = (a or "").lower()
        if a in {"r", "right"}:
            return "---:"
        if a in {"c", "center", "centre"}:
            return ":---:"
        return ":---"  # default left
    aligns = [norm_align(a) for a in (align or [])]
    aligns = (aligns + [":---"] * ncol)[:ncol]

    def row_line(cells: Sequence[object]) -> str:
        cells = list(cells or ())
        cells = (cells + [""] * ncol)[:ncol]
        return "| " + " | ".join(_format_cell(c) for c in cells) + " |"

    lines = [row_line(hdr), "| " + " | ".join(aligns) + " |"]
    for r in rows or ():
        lines.append(row_line(r))
    return "\n".join(lines)
def join_blocks(*blocks: Optional[str]) -> str:
    """Join markdown blocks with a single blank line between non-empty blocks."""
    out: List[str] = []
    for b in blocks:
        if not b:
            continue
        s = str(b).strip()
        if s:
            out.append(s)
    return "\n\n".join(out)


@dataclass(frozen=True)
class KeyValue:
    key: str
    value: str


def key_value_table(items: Union[Mapping[str, object], Sequence[KeyValue], Sequence[Tuple[str, object]]]) -> str:
    """Render a two-column table from key/value pairs."""
    pairs: List[Tuple[str, object]] = []
    if items is None:
        return ""
    if isinstance(items, Mapping):
        pairs = [(str(k), v) for k, v in items.items()]
    else:
        for it in items:
            if isinstance(it, KeyValue):
                pairs.append((it.key, it.value))
            else:
                k, v = it  # type: ignore[misc]
                pairs.append((str(k), v))
    return table(["Key", "Value"], [(k, v) for k, v in pairs])
