"""Customer discovery output generation (refactored).

Public API:
- generate_customer_discovery_output(payload, *, title=None, fmt="markdown") -> str
- build_customer_discovery_sections(payload) -> list[tuple[str, str]]

`payload` is a dict-like object that may contain keys like:
summary, problem, audience, personas, hypotheses, interview_questions,
insights, risks, next_steps, sources, metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence
def _norm_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    return str(x).strip()


def _as_list(x: Any) -> list[Any]:
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _md_heading(title: str, level: int = 2) -> str:
    t = _norm_text(title)
    return f"{'#' * max(1, int(level))} {t}".rstrip()


def _join_blocks(blocks: Iterable[str]) -> str:
    parts = [b.strip() for b in blocks if _norm_text(b)]
    return "\n\n".join(parts).strip()


def _render_bullets(items: Sequence[Any]) -> str:
    out = []
    for it in items:
        if isinstance(it, Mapping):
            line = _norm_text(it.get("text") or it.get("title") or it.get("name") or it)
        else:
            line = _norm_text(it)
        if line:
            out.append(f"- {line}")
    return "\n".join(out).strip()


def _render_numbered(items: Sequence[Any]) -> str:
    out = []
    for i, it in enumerate(items, 1):
        line = _norm_text(it.get("text") if isinstance(it, Mapping) else it)
        if line:
            out.append(f"{i}. {line}")
    return "\n".join(out).strip()


def _render_kv(obj: Mapping[str, Any], *, keys: Sequence[str] | None = None) -> str:
    if not obj:
        return ""
    ks = list(keys) if keys else [k for k in obj.keys() if k not in {"items", "list"}]
    rows = []
    for k in ks:
        v = obj.get(k)
        if v is None or v == "":
            continue
        if isinstance(v, (list, tuple)):
            vv = ", ".join(_norm_text(x) for x in v if _norm_text(x))
        else:
            vv = _norm_text(v)
        if vv:
            rows.append(f"- **{_norm_text(k)}**: {vv}")
    return "\n".join(rows).strip()
@dataclass(frozen=True)
class CustomerDiscoveryOutput:
    title: str
    sections: list[tuple[str, str]]

    def render(self, fmt: str = "markdown") -> str:
        fmt = (fmt or "markdown").lower()
        if fmt not in {"markdown", "md", "text", "txt"}:
            raise ValueError(f"Unsupported format: {fmt}")
        is_md = fmt in {"markdown", "md"}
        blocks: list[str] = []
        if _norm_text(self.title):
            blocks.append(_md_heading(self.title, 1) if is_md else self.title.strip())
        for name, body in self.sections:
            if not _norm_text(body):
                continue
            blocks.append((_md_heading(name, 2) + "\n\n" + body.strip()) if is_md else (name.strip() + "\n" + body.strip()))
        return _join_blocks(blocks) + ("\n" if blocks else "")


def _get(payload: Any, key: str, default: Any = None) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(key, default)
    return getattr(payload, key, default)


def build_customer_discovery_sections(payload: Any) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []

    def add(title: str, body: str) -> None:
        b = _norm_text(body)
        if b:
            sections.append((title, b))

    add("Summary", _norm_text(_get(payload, "summary")))
    add("Problem", _norm_text(_get(payload, "problem")))
    add("Audience", _norm_text(_get(payload, "audience")))

    personas = _get(payload, "personas")
    if isinstance(personas, Mapping):
        body = _render_kv(personas) or _norm_text(personas)
        add("Personas", body)
    else:
        body = _render_bullets(_as_list(personas))
        add("Personas", body)

    hypotheses = _get(payload, "hypotheses")
    if isinstance(hypotheses, Mapping):
        body = _render_kv(hypotheses) or _norm_text(hypotheses)
        add("Hypotheses", body)
    else:
        body = _render_numbered(_as_list(hypotheses))
        add("Hypotheses", body)

    questions = _get(payload, "interview_questions") or _get(payload, "questions")
    q_body = _render_numbered(_as_list(questions))
    add("Interview Questions", q_body)

    insights = _get(payload, "insights")
    i_body = _render_bullets(_as_list(insights))
    add("Insights", i_body)

    risks = _get(payload, "risks")
    r_body = _render_bullets(_as_list(risks))
    add("Risks", r_body)

    next_steps = _get(payload, "next_steps") or _get(payload, "actions")
    ns_body = _render_numbered(_as_list(next_steps))
    add("Next Steps", ns_body)

    sources = _get(payload, "sources")
    s_body = _render_bullets(_as_list(sources))
    add("Sources", s_body)

    metadata = _get(payload, "metadata")
    if isinstance(metadata, Mapping):
        add("Metadata", _render_kv(metadata))
    elif _norm_text(metadata):
        add("Metadata", _norm_text(metadata))

    return sections


def generate_customer_discovery_output(payload: Any, *, title: str | None = None, fmt: str = "markdown") -> str:
    t = _norm_text(title) or _norm_text(_get(payload, "title")) or "Customer Discovery"
    out = CustomerDiscoveryOutput(title=t, sections=build_customer_discovery_sections(payload))
    return out.render(fmt=fmt)


__all__ = [
    "CustomerDiscoveryOutput",
    "build_customer_discovery_sections",
    "generate_customer_discovery_output",
]
