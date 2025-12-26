"""cosmo_contracts.markdown

Small, dependency-free helpers for producing GitHub-flavoured Markdown.

The project historically exposed this module as a public entrypoint; the goal
here is to keep a stable import surface and provide a minimal but useful API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence
__all__ = [
    "Markdown",
    "MarkdownBuilder",
    "escape_markdown",
    "heading",
    "paragraph",
    "bullet_list",
    "code_block",
    "table",
    "render",
]
class Markdown(str):
    """A thin marker type for strings that contain Markdown."""
def escape_markdown(text: str) -> str:
    """Escape characters that frequently break Markdown rendering.

    This is intentionally conservative and targets common inline contexts.
    """
    if not text:
        return ""
    # Escape backslash first to avoid double escaping.
    text = text.replace("\\", "\\\\")
    for ch in ("*", "_", "`", "[", "]", "<", ">", "|"):
        text = text.replace(ch, f"\\{ch}")
    return text
def heading(text: str, level: int = 1) -> Markdown:
    """Return a Markdown heading."""
    lvl = max(1, min(int(level), 6))
    return Markdown(f"{'#' * lvl} {text.strip()}\n")
def paragraph(text: str) -> Markdown:
    """Return a Markdown paragraph (terminated with a blank line)."""
    t = text.strip()
    return Markdown(f"{t}\n\n" if t else "\n")
def bullet_list(items: Iterable[Any], *, indent: int = 0) -> Markdown:
    """Render an iterable as a Markdown bullet list."""
    pad = " " * max(0, int(indent))
    lines = []
    for item in items:
        s = str(item).strip()
        if not s:
            continue
        lines.append(f"{pad}- {s}")
    return Markdown("\n".join(lines) + ("\n" if lines else ""))
def code_block(code: str, language: str = "") -> Markdown:
    """Return a fenced code block."""
    lang = language.strip()
    body = (code or "").rstrip("\n")
    return Markdown(f"```{lang}\n{body}\n```\n")
def _stringify_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Markdown):
        return str(value).strip()
    return escape_markdown(str(value)).strip()
def table(headers: Sequence[Any], rows: Sequence[Sequence[Any]]) -> Markdown:
    """Render a simple GFM table.

    Cells are escaped for safe inline rendering.
    """
    if not headers:
        raise ValueError("headers must be non-empty")
    h = [_stringify_cell(x) for x in headers]
    header_line = "| " + " | ".join(h) + " |"
    sep_line = "| " + " | ".join(["---"] * len(h)) + " |"
    row_lines = []
    for r in rows:
        cells = list(r) + [""] * (len(h) - len(r))
        cells = cells[: len(h)]
        row_lines.append("| " + " | ".join(_stringify_cell(c) for c in cells) + " |")
    return Markdown("\n".join([header_line, sep_line, *row_lines]) + "\n")
@dataclass
class MarkdownBuilder:
    """Incrementally build Markdown with convenience helpers."""

    lines: list[str] = field(default_factory=list)

    def add(self, md: Any) -> "MarkdownBuilder":
        if md is None:
            return self
        text = str(md)
        self.lines.extend(text.splitlines())
        return self

    def add_heading(self, text: str, level: int = 1) -> "MarkdownBuilder":
        return self.add(heading(text, level))

    def add_paragraph(self, text: str) -> "MarkdownBuilder":
        return self.add(paragraph(text))

    def add_bullets(self, items: Iterable[Any], *, indent: int = 0) -> "MarkdownBuilder":
        return self.add(bullet_list(items, indent=indent))

    def add_code(self, code: str, language: str = "") -> "MarkdownBuilder":
        return self.add(code_block(code, language))

    def add_table(self, headers: Sequence[Any], rows: Sequence[Sequence[Any]]) -> "MarkdownBuilder":
        return self.add(table(headers, rows))

    def build(self) -> Markdown:
        # Preserve explicit blank lines; always end with a newline for POSIX friendliness.
        return Markdown("\n".join(self.lines).rstrip("\n") + "\n")
def render(obj: Any) -> Markdown:
    """Best-effort conversion of common Python objects to Markdown.

    - str / Markdown: returned as-is
    - Mapping: renders as a 2-column table of key/value
    - Sequence: renders as a bullet list
    - Other: coerced to a paragraph
    """
    if obj is None:
        return Markdown("")
    if isinstance(obj, Markdown):
        return obj
    if isinstance(obj, str):
        return Markdown(obj if obj.endswith("\n") else obj + "\n")
    if isinstance(obj, Mapping):
        headers = ["key", "value"]
        rows = [(k, v) for k, v in obj.items()]
        return table(headers, rows)
    if isinstance(obj, (list, tuple, set, frozenset)):
        return bullet_list(obj)
    return paragraph(str(obj))
