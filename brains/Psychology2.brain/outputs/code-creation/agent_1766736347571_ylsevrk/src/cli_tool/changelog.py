from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence
import re

_CYCLE_RE = re.compile(r"^##\s+Cycle\s+(.+?)\s*$", re.M)
_HEADER = "# CHANGELOG\n\nThis file tracks cycle-stamped changes to generated /outputs artifacts and structure.\n"
_SUBHEADER = "\n## Cycle {cycle}\n\n{body}\n"
_MIN_BODY = "- Initialized.\n"


def cycle_stamp(dt: Optional[datetime] = None) -> str:
    """Return a deterministic, filesystem-safe cycle stamp in UTC."""
    dt = dt or datetime.now(timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H-%M-%SZ")


def ensure_md_bullets(lines: Iterable[str]) -> str:
    items = []
    for raw in lines:
        s = str(raw).strip()
        if not s:
            continue
        if not (s.startswith("- ") or s.startswith("* ")):
            s = "- " + s
        items.append(s)
    return "\n".join(items).rstrip() + ("\n" if items else "")


@dataclass(frozen=True)
class ChangelogEntry:
    cycle: str
    body: str

    def render(self) -> str:
        b = self.body.strip("\n")
        b = (b + "\n") if b else _MIN_BODY
        return _SUBHEADER.format(cycle=self.cycle, body=b.rstrip("\n"))


def default_changelog_text() -> str:
    return (_HEADER + "\n").rstrip("\n") + "\n"


def validate_markdown(text: str) -> None:
    if not text.strip():
        raise ValueError("Changelog is empty.")
    if not text.lstrip().startswith("# "):
        raise ValueError("Changelog must start with a top-level Markdown heading.")
    # Ensure cycle headings are unique
    cycles = [m.group(1).strip() for m in _CYCLE_RE.finditer(text)]
    if len(cycles) != len(set(cycles)):
        raise ValueError("Duplicate cycle headings found in changelog.")
    # Ensure each cycle heading has some content after it
    for m in _CYCLE_RE.finditer(text):
        start = m.end()
        nxt = _CYCLE_RE.search(text, start)
        end = nxt.start() if nxt else len(text)
        section = text[start:end].strip()
        if not section:
            raise ValueError(f"Cycle '{m.group(1).strip()}' has an empty section.")


def ensure_changelog(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(default_changelog_text(), encoding="utf-8")
    else:
        txt = path.read_text(encoding="utf-8")
        if not txt.lstrip().startswith("# "):
            txt = default_changelog_text() + "\n" + txt.lstrip()
            path.write_text(txt.rstrip() + "\n", encoding="utf-8")
    validate_markdown(path.read_text(encoding="utf-8"))


def upsert_cycle_entry(text: str, entry: ChangelogEntry) -> str:
    rendered = entry.render().strip("\n") + "\n"
    matches = list(_CYCLE_RE.finditer(text))
    for i, m in enumerate(matches):
        if m.group(1).strip() == entry.cycle:
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            return (text[:start].rstrip() + "\n\n" + rendered + text[end:].lstrip()).rstrip() + "\n"
    # Insert after the header block (first blank-line separated paragraph set)
    parts = text.rstrip() + "\n"
    # Insert newest at top: after first H1 block
    h1_end = parts.find("\n")
    insert_at = h1_end + 1 if h1_end != -1 else 0
    # Prefer to insert after the initial header paragraph (up to first double newline)
    dbl = parts.find("\n\n", insert_at)
    insert_at = (dbl + 2) if dbl != -1 else insert_at
    return (parts[:insert_at].rstrip() + "\n\n" + rendered + parts[insert_at:].lstrip()).rstrip() + "\n"


def append_or_update(
    changelog_path: Path,
    changes: Sequence[str],
    cycle: Optional[str] = None,
) -> str:
    """Ensure changelog exists, then upsert an entry for the given cycle."""
    ensure_changelog(changelog_path)
    cyc = (cycle or "").strip() or cycle_stamp()
    body = ensure_md_bullets(changes) or _MIN_BODY
    entry = ChangelogEntry(cycle=cyc, body=body)
    txt = changelog_path.read_text(encoding="utf-8")
    new_txt = upsert_cycle_entry(txt, entry)
    validate_markdown(new_txt)
    if new_txt != txt:
        changelog_path.write_text(new_txt, encoding="utf-8")
    return cyc
