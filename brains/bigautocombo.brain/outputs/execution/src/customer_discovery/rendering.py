from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def normalize_newlines(text: str) -> str:
    text = as_text(text)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_trailing_whitespace(text: str) -> str:
    text = normalize_newlines(text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip("\n")


def collapse_blank_lines(text: str, max_consecutive: int = 2) -> str:
    text = normalize_newlines(text)
    out: list[str] = []
    blank = 0
    for line in text.split("\n"):
        if line.strip() == "":
            blank += 1
            if blank <= max_consecutive:
                out.append("")
        else:
            blank = 0
            out.append(line)
    return "\n".join(out).strip("\n")


def ensure_terminal_newline(text: str) -> str:
    text = as_text(text)
    return text if text.endswith("\n") else (text + "\n")
def md_escape_inline(text: str) -> str:
    """Escape common Markdown metacharacters for inline contexts."""
    text = as_text(text)
    rep = {
        "\\": "\\\\",
        "`": "\\`",
        "*": "\\*",
        "_": "\\_",
        "[": "\\[",
        "]": "\\]",
        "<": "\\<",
        ">": "\\>",
    }
    for k, v in rep.items():
        text = text.replace(k, v)
    return text


def md_code_block(code: str, language: str = "") -> str:
    code = strip_trailing_whitespace(as_text(code))
    fence = "```"
    # Defensive: avoid closing fence collision.
    code = code.replace(fence, "``\u200b`")
    lang = language.strip()
    header = f"{fence}{lang}".rstrip()
    return f"{header}\n{code}\n{fence}"
def heading(text: str, level: int = 2) -> str:
    level = max(1, min(6, int(level)))
    t = strip_trailing_whitespace(as_text(text)).replace("\n", " ").strip()
    t = t.lstrip("#").strip()
    return ("#" * level) + " " + t if t else ("#" * level)


def section(title: str, body: str, level: int = 2) -> str:
    b = collapse_blank_lines(strip_trailing_whitespace(as_text(body)))
    if b == "":
        return ""
    h = heading(title, level=level)
    return f"{h}\n\n{b}"


def join_sections(sections: Iterable[str]) -> str:
    parts = [collapse_blank_lines(strip_trailing_whitespace(s)) for s in sections if as_text(s).strip()]
    parts = [p for p in parts if p]
    return "\n\n".join(parts).strip() + ("\n" if parts else "")
def bullet_list(items: Iterable[Any], bullet: str = "- ") -> str:
    lines: list[str] = []
    for it in items:
        t = collapse_blank_lines(strip_trailing_whitespace(as_text(it)))
        if not t:
            continue
        t_lines = t.split("\n")
        lines.append(f"{bullet}{t_lines[0]}")
        for cont in t_lines[1:]:
            lines.append((" " * len(bullet)) + cont)
    return "\n".join(lines)


def numbered_list(items: Iterable[Any], start: int = 1) -> str:
    lines: list[str] = []
    n = int(start)
    for it in items:
        t = collapse_blank_lines(strip_trailing_whitespace(as_text(it)))
        if not t:
            continue
        prefix = f"{n}. "
        t_lines = t.split("\n")
        lines.append(f"{prefix}{t_lines[0]}")
        for cont in t_lines[1:]:
            lines.append((" " * len(prefix)) + cont)
        n += 1
    return "\n".join(lines)


def kv_lines(data: Mapping[str, Any], key_order: Sequence[str] | None = None, sep: str = ": ") -> str:
    if data is None:
        return ""
    if key_order is None:
        keys = sorted((str(k) for k in data.keys()), key=lambda s: s.lower())
    else:
        keys = [k for k in key_order if k in data]
        rest = sorted((str(k) for k in data.keys() if k not in set(keys)), key=lambda s: s.lower())
        keys = list(keys) + rest
    out: list[str] = []
    for k in keys:
        v = data.get(k)
        if v is None or as_text(v).strip() == "":
            continue
        out.append(f"{k}{sep}{strip_trailing_whitespace(as_text(v))}")
    return "\n".join(out)
@dataclass(frozen=True)
class RenderedSection:
    title: str
    body: str
    level: int = 2

    def render(self) -> str:
        return section(self.title, self.body, level=self.level)


def render_sections(sections: Iterable[RenderedSection]) -> str:
    return join_sections(s.render() for s in sections)
