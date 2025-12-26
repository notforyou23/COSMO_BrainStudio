"""Bibliography subsystem: validate/normalize BibTeX, maintain seed references.bib, and emit a summary artifact."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import hashlib
from typing import Dict, List, Tuple, Iterable, Optional


SEED_BIB = r"""% Seed bibliography for the documentation-and-research pipeline.
% This file is intentionally small and normalized; add project-specific references over time.

@article{kingma2014adam,
  title        = {Adam: A Method for Stochastic Optimization},
  author       = {Kingma, Diederik P. and Ba, Jimmy},
  year         = {2014},
  journal      = {arXiv preprint arXiv:1412.6980},
  url          = {https://arxiv.org/abs/1412.6980}
}

@inproceedings{devlin2019bert,
  title        = {BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding},
  author       = {Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton and Toutanova, Kristina},
  year         = {2019},
  booktitle    = {Proceedings of NAACL-HLT},
  url          = {https://arxiv.org/abs/1810.04805}
}

@misc{bibtex,
  title        = {BibTeX},
  author       = {{Oren Patashnik}},
  year         = {1988},
  howpublished = {Documentation},
  url          = {http://www.bibtex.org/}
}
"""


@dataclass
class BibEntry:
    entry_type: str
    key: str
    fields: Dict[str, str]
    raw: str = ""


_REQUIRED = {
    "article": {"title", "author", "year", "journal"},
    "inproceedings": {"title", "author", "year", "booktitle"},
    "book": {"title", "author", "year", "publisher"},
    "misc": {"title", "year"},
}


def ensure_seed_references(seed_path: Path) -> bool:
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    if seed_path.exists() and seed_path.read_text(encoding="utf-8").strip():
        return False
    seed_path.write_text(SEED_BIB.strip() + "\n", encoding="utf-8")
    return True


def _strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("%"):
            continue
        out.append(line)
    return "\n".join(out)


_ENTRY_RE = re.compile(r"@(?P<type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s]+)\s*,", re.M)
_FIELD_RE = re.compile(r"(?P<k>[A-Za-z][A-Za-z0-9_\-]*)\s*=\s*(?P<v>\{(?:[^{}]|\{[^{}]*\})*\}|\"(?:\\.|[^\"])*\"|[^,\n\r]+)\s*,?", re.S)


def parse_bibtex(text: str) -> List[BibEntry]:
    t = _strip_comments(text)
    entries: List[BibEntry] = []
    i = 0
    while True:
        m = _ENTRY_RE.search(t, i)
        if not m:
            break
        etype = m.group("type").lower()
        key = m.group("key").strip()
        j = m.end()
        depth, end = 1, j
        while end < len(t) and depth > 0:
            c = t[end]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            end += 1
        body = t[j:end - 1]
        fields: Dict[str, str] = {}
        for fm in _FIELD_RE.finditer(body):
            k = fm.group("k").lower().strip()
            v = fm.group("v").strip()
            if v.endswith(","):
                v = v[:-1].strip()
            fields[k] = v
        raw = t[m.start():end]
        entries.append(BibEntry(entry_type=etype, key=key, fields=fields, raw=raw))
        i = end
    return entries


def _unbrace(v: str) -> str:
    v = v.strip()
    if v.startswith("{") and v.endswith("}"):
        return v[1:-1].strip()
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1].strip()
    return v.strip()


def _slug(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    s = re.sub(r"[^A-Za-z0-9]+", "", s)
    return s.lower() or "ref"


def normalize_key(entry: BibEntry) -> str:
    author = _unbrace(entry.fields.get("author", ""))
    year = re.findall(r"\d{4}", _unbrace(entry.fields.get("year", "")))
    title = _unbrace(entry.fields.get("title", ""))
    a = _slug(author.split(" and ")[0].split(",")[0])[:20]
    y = (year[0] if year else "")
    t = _slug(title)[:24]
    base = (a + y + t) or _slug(entry.key)
    h = hashlib.sha1((entry.entry_type + base).encode("utf-8")).hexdigest()[:6]
    return (base + h)[:40]


def normalize_bibtex(entries: Iterable[BibEntry]) -> Tuple[str, List[str]]:
    seen = set()
    warnings: List[str] = []
    blocks: List[str] = []
    for e in entries:
        et = (e.entry_type or "misc").lower()
        fields = {k.lower().strip(): v.strip() for k, v in (e.fields or {}).items() if k and v}
        key = _slug(e.key)
        if not key or key in {"ref", "_"}:
            key = normalize_key(BibEntry(et, e.key, fields))
        if key in seen:
            warnings.append(f"duplicate_key:{key}")
            key = key + "_dup"
        seen.add(key)
        ordered = []
        pref = ["title", "author", "year", "journal", "booktitle", "publisher", "howpublished", "url", "doi"]
        for k in pref:
            if k in fields:
                ordered.append((k, fields.pop(k)))
        for k in sorted(fields):
            ordered.append((k, fields[k]))
        lines = [f"@{et}{{{key},"]
        for k, v in ordered:
            vv = _unbrace(v)
            vv = re.sub(r"\s+", " ", vv).strip()
            lines.append(f"  {k:<12}= {{{vv}}},")
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks).strip() + "\n", warnings


def validate_entries(entries: Iterable[BibEntry]) -> List[str]:
    issues: List[str] = []
    for e in entries:
        req = _REQUIRED.get((e.entry_type or "").lower(), set())
        present = {k.lower() for k in (e.fields or {}).keys()}
        missing = sorted(req - present)
        if missing:
            issues.append(f"missing_fields:{e.key}:{','.join(missing)}")
        if "year" in present:
            y = _unbrace(e.fields.get("year", ""))
            if y and not re.search(r"\d{4}", y):
                issues.append(f"bad_year:{e.key}:{y}")
    return issues


def write_normalized_bib(in_path: Path, out_path: Path) -> Dict[str, object]:
    raw = in_path.read_text(encoding="utf-8") if in_path.exists() else ""
    entries = parse_bibtex(raw)
    norm_text, norm_warnings = normalize_bibtex(entries)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(norm_text, encoding="utf-8")
    issues = validate_entries(parse_bibtex(norm_text))
    return {"entries": len(entries), "warnings": norm_warnings, "issues": issues, "written": str(out_path)}


def build_bibliography_summary(bib_path: Path, seed_path: Path, summary_md_path: Path, normalized_bib_path: Optional[Path] = None) -> Dict[str, object]:
    seeded = ensure_seed_references(seed_path)
    src_path = bib_path if bib_path.exists() else seed_path
    norm_path = normalized_bib_path or (summary_md_path.parent / "references.normalized.bib")
    result = write_normalized_bib(src_path, norm_path)
    entries = parse_bibtex(norm_path.read_text(encoding="utf-8"))
    by_type: Dict[str, int] = {}
    for e in entries:
        by_type[e.entry_type] = by_type.get(e.entry_type, 0) + 1
    lines = [
        "# Bibliography Summary",
        "",
        f"- Source bib: `{src_path}`",
        f"- Seed created: `{seeded}`",
        f"- Normalized bib: `{norm_path}`",
        f"- Total entries: **{len(entries)}**",
        "- By type:",
    ]
    for t in sorted(by_type):
        lines.append(f"  - {t}: {by_type[t]}")
    if result["issues"] or result["warnings"]:
        lines += ["", "## Validation", ""]
        if result["issues"]:
            lines.append("Issues:")
            lines += [f"- {x}" for x in result["issues"]]
        if result["warnings"]:
            lines.append("Warnings:")
            lines += [f"- {x}" for x in result["warnings"]]
    summary_md_path.parent.mkdir(parents=True, exist_ok=True)
    summary_md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return {"seed_created": seeded, "source": str(src_path), "normalized": str(norm_path), "summary": str(summary_md_path), "counts": by_type, "validation": {"issues": result["issues"], "warnings": result["warnings"]}}
