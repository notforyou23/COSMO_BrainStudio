"""psyprim CLI: standardized primary-source workflows for psychology.

Commands cover project initialization, metadata checklist generation, metadata
validation, and citation/provenance reporting.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import json
import typer

app = typer.Typer(add_completion=False, help="psyprim: primary-source workflow + metadata tooling")

DEFAULT_DIRS = ("sources", "metadata", "outputs")
META_TEMPLATE_NAME = "record.template.json"
CHECKLIST_NAME = "psyprim_checklist.md"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_records(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    if path.suffix.lower() == ".jsonl":
        recs: List[Dict[str, Any]] = []
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                raise ValueError(f"{path}:{i}: invalid JSON: {e}") from e
            if not isinstance(rec, dict):
                raise ValueError(f"{path}:{i}: expected object")
            recs.append(rec)
        return recs
    obj = _read_json(path)
    if isinstance(obj, list):
        if not all(isinstance(x, dict) for x in obj):
            raise ValueError(f"{path}: expected list of objects")
        return obj
    if isinstance(obj, dict):
        return [obj]
    raise ValueError(f"{path}: expected object, list, or jsonl")


def _compact(s: str) -> str:
    return " ".join((s or "").split())


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _validate_record(rec: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    rid = rec.get("id") or rec.get("record_id") or ""
    prefix = f"[{rid or 'record'}] "
    def req(field: str) -> None:
        if rec.get(field) in (None, "", [], {}):
            errs.append(prefix + f"missing required field: {field}")
    for f in ("id", "title", "creators", "date", "language", "work_type", "source"):
        req(f)
    creators = rec.get("creators")
    if creators not in (None, "") and not (isinstance(creators, list) and all(isinstance(c, str) and c.strip() for c in creators)):
        errs.append(prefix + "creators must be a non-empty list of strings")
    src = rec.get("source")
    if isinstance(src, dict):
        for f in ("url", "repository", "accessed"):
            if src.get(f) in (None, ""):
                errs.append(prefix + f"source.{f} is required when source is an object")
    elif src not in (None, "") and not isinstance(src, str):
        errs.append(prefix + "source must be string or object")
    for block in ("edition", "translation", "public_domain", "pagination"):
        b = rec.get(block, {})
        if b not in (None, "") and not isinstance(b, dict):
            errs.append(prefix + f"{block} must be an object")
    pd = rec.get("public_domain") or {}
    if isinstance(pd, dict):
        if pd and pd.get("status") not in (None, "public_domain", "copyrighted", "unknown"):
            errs.append(prefix + "public_domain.status must be one of public_domain|copyrighted|unknown")
    pag = rec.get("pagination") or {}
    if isinstance(pag, dict) and pag:
        v = pag.get("variants")
        if v not in (None, "") and not (isinstance(v, list) and all(isinstance(x, dict) for x in v)):
            errs.append(prefix + "pagination.variants must be a list of objects")
    return errs


def _citation_line(rec: Dict[str, Any]) -> str:
    title = _compact(str(rec.get("title") or ""))
    creators = ", ".join([_compact(c) for c in _as_list(rec.get("creators")) if isinstance(c, str)])
    date = _compact(str(rec.get("date") or ""))
    lang = _compact(str(rec.get("language") or ""))
    ed = rec.get("edition") or {}
    tr = rec.get("translation") or {}
    parts = [p for p in [creators, f"({date})" if date else "", title] if p]
    tail: List[str] = []
    if isinstance(ed, dict):
        e = _compact(str(ed.get("statement") or ed.get("edition") or ""))
        if e:
            tail.append(e)
    if isinstance(tr, dict):
        t = _compact(str(tr.get("statement") or ""))
        if t:
            tail.append(f"Trans.: {t}")
    if lang:
        tail.append(f"Lang: {lang}")
    src = rec.get("source") or {}
    if isinstance(src, dict):
        repo = _compact(str(src.get("repository") or ""))
        url = _compact(str(src.get("url") or ""))
        if repo:
            tail.append(repo)
        if url:
            tail.append(url)
    elif isinstance(src, str) and src.strip():
        tail.append(_compact(src))
    return ". ".join([" ".join(parts).strip(". "), *tail]).strip(". ") + "."


def _provenance_block(rec: Dict[str, Any]) -> str:
    rid = rec.get("id") or "record"
    pd = rec.get("public_domain") or {}
    pag = rec.get("pagination") or {}
    lines = [f"- ID: {rid}", f"  Citation: {_citation_line(rec)}"]
    if isinstance(pd, dict) and pd:
        status = pd.get("status") or "unknown"
        reason = _compact(str(pd.get("basis") or pd.get("notes") or ""))
        lines.append(f"  Public-domain: {status}" + (f" ({reason})" if reason else ""))
    if isinstance(pag, dict) and pag.get("variants"):
        lines.append("  Pagination variants:")
        for v in pag.get("variants") or []:
            if not isinstance(v, dict):
                continue
            label = _compact(str(v.get("label") or v.get("edition") or "variant"))
            scheme = _compact(str(v.get("scheme") or ""))
            lines.append(f"    - {label}" + (f" [{scheme}]" if scheme else ""))
    ed = rec.get("edition") or {}
    tr = rec.get("translation") or {}
    if isinstance(ed, dict) and any(ed.get(k) for k in ("isbn", "publisher", "year", "statement")):
        lines.append("  Edition provenance: " + _compact(json.dumps({k: ed.get(k) for k in ed if ed.get(k) not in (None, '', [], {})}, ensure_ascii=False)))
    if isinstance(tr, dict) and any(tr.get(k) for k in ("translator", "publisher", "year", "statement")):
        lines.append("  Translation provenance: " + _compact(json.dumps({k: tr.get(k) for k in tr if tr.get(k) not in (None, '', [], {})}, ensure_ascii=False)))
    return "\n".join(lines)
@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Project root directory"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing template files"),
) -> None:
    """Initialize a psyprim project layout with a metadata template."""
    root = path.resolve()
    root.mkdir(parents=True, exist_ok=True)
    for d in DEFAULT_DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
    tmpl = root / "metadata" / META_TEMPLATE_NAME
    if tmpl.exists() and not force:
        typer.echo(f"Exists (use --force to overwrite): {tmpl}")
        raise typer.Exit(code=2)
    template = {
        "id": "example-1890-author-title",
        "title": "Example Primary Source Title",
        "creators": ["Surname, Given"],
        "date": "1890",
        "language": "en",
        "work_type": "book|article|chapter|letter|manuscript|dataset|other",
        "source": {"repository": "Internet Archive|HathiTrust|Library", "url": "https://...", "accessed": "YYYY-MM-DD"},
        "edition": {"statement": "2nd ed.", "publisher": "", "year": "", "isbn": ""},
        "translation": {"statement": "", "translator": "", "publisher": "", "year": ""},
        "pagination": {"variants": [{"label": "facsimile PDF", "scheme": "printed|manuscript|scan", "notes": ""}]},
        "public_domain": {"status": "unknown", "basis": "jurisdiction + rule + evidence", "notes": ""},
        "notes": "Add archival call numbers, stable IDs, or scan hashes here.",
    }
    _write_json(tmpl, template)
    checklist = root / CHECKLIST_NAME
    if not checklist.exists() or force:
        checklist.write_text(_default_checklist_text() + "\n", encoding="utf-8")
    typer.echo(f"Initialized: {root}")


def _default_checklist_text() -> str:
    return """psyprim metadata checklist (primary-source scholarship in psychology)

Core record
- [ ] Stable record id (slug), unique in project
- [ ] Title (verbatim from title page / header)
- [ ] Creators (verbatim + normalized form; include editors where relevant)
- [ ] Date (as given + normalized ISO-like if possible)
- [ ] Language code (BCP-47 or simple ISO-639-1)
- [ ] Work type (book/article/chapter/letter/manuscript/other)
- [ ] Source link + repository + access date

Edition / translation provenance
- [ ] Edition statement (edition number, publisher, place, year, identifiers)
- [ ] Translation statement (translator, year, publisher, edition used)
- [ ] Provenance evidence: scans, catalog records, archive call numbers, stable IDs

Variant pagination + quotation traceability
- [ ] Describe pagination scheme(s): printed vs scanned page numbers, manuscript folio, PDF page indices
- [ ] Provide variant mappings (if quoting/citing uses a non-canonical scheme)
- [ ] Note any missing pages, misnumbering, or OCR shifts

Public-domain / rights-cautious citation
- [ ] Public-domain status: public_domain/copyrighted/unknown
- [ ] Basis + jurisdictional rule-of-thumb + evidence (links, dates)
- [ ] Preferred citation form for PD scans / repositories

Workflow sanity checks
- [ ] Minimum required fields present
- [ ] All URLs valid + accessed dates present
- [ ] Report generated and reviewed before submission
"""


@app.command()
def checklist(
    out: Path = typer.Option(Path(CHECKLIST_NAME), "--out", "-o", help="Output checklist file (md)"),
) -> None:
    """Generate the mission-aligned metadata checklist."""
    out = out.resolve()
    out.write_text(_default_checklist_text() + "\n", encoding="utf-8")
    typer.echo(str(out))
@app.command()
def validate(
    metadata: Path = typer.Argument(..., help="Path to metadata .json/.jsonl (single record or list)"),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors (currently same as errors)"),
) -> None:
    """Validate metadata records for required fields and basic typing."""
    path = metadata.resolve()
    try:
        records = _load_records(path)
    except Exception as e:
        typer.echo(f"ERROR: {e}")
        raise typer.Exit(code=2)
    all_errs: List[str] = []
    for rec in records:
        all_errs.extend(_validate_record(rec))
    if all_errs:
        typer.echo(f"INVALID: {len(all_errs)} issue(s)")
        for msg in all_errs:
            typer.echo(" - " + msg)
        raise typer.Exit(code=1 if strict or True else 1)
    typer.echo(f"VALID: {len(records)} record(s)")


@app.command()
def report(
    metadata: Path = typer.Argument(..., help="Path to metadata .json/.jsonl (single record or list)"),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Write report to file (default: stdout)"),
    fmt: str = typer.Option("md", "--format", "-f", help="md or json"),
) -> None:
    """Produce citation + provenance report for review and submission packages."""
    path = metadata.resolve()
    records = _load_records(path)
    fmt_l = fmt.lower().strip()
    if fmt_l not in ("md", "json"):
        typer.echo("ERROR: --format must be md or json")
        raise typer.Exit(code=2)
    if fmt_l == "json":
        payload = []
        for r in records:
            payload.append(
                {
                    "id": r.get("id"),
                    "citation": _citation_line(r),
                    "public_domain": r.get("public_domain") or {},
                    "edition": r.get("edition") or {},
                    "translation": r.get("translation") or {},
                    "pagination": r.get("pagination") or {},
                    "source": r.get("source") or {},
                }
            )
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        blocks = ["# psyprim citation + provenance report", ""]
        for r in records:
            blocks.append(_provenance_block(r))
            blocks.append("")
        text = "\n".join(blocks).rstrip() + "\n"
    if out:
        outp = out.resolve()
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(text, encoding="utf-8")
        typer.echo(str(outp))
    else:
        typer.echo(text, nl=False)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
