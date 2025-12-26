from __future__ import annotations
import argparse, json, os, re, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve()
for _ in range(6):
    if (ROOT.parent / "outputs").exists():
        ROOT = ROOT.parent
        break
    ROOT = ROOT.parent
OUTPUTS_DIR = ROOT / "outputs"
CASE_STUDIES_DIR = OUTPUTS_DIR / "case_studies"
INDEX_PATH = OUTPUTS_DIR / "ARTIFACT_INDEX.json"

ID_RE = re.compile(r"^[a-z0-9]+(?:[a-z0-9_-]*[a-z0-9])?$")

def _is_tty() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:
        return False

def _prompt(label: str, default: str | None = None, required: bool = False) -> str:
    if not _is_tty():
        return default or ""
    while True:
        suffix = f" [{default}]" if default else ""
        val = input(f"{label}{suffix}: ").strip()
        if not val and default is not None:
            val = default
        if val or not required:
            return val
        print("Value required.", file=sys.stderr)

def _split_csv(s: str) -> list[str]:
    if not s:
        return []
    parts = [p.strip() for p in s.split(",")]
    return [p for p in parts if p]

def _load_index() -> dict:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            raise SystemExit(f"Failed to read index: {INDEX_PATH} ({e})")
    return {"artifacts": []}

def _write_index(index: dict) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _safe_id(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9_-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-_")
    return s

def _ensure_valid_id(cs_id: str) -> str:
    cs_id = _safe_id(cs_id)
    if not cs_id or not ID_RE.match(cs_id):
        raise SystemExit("Invalid id. Use lowercase letters/numbers plus '-'/'_' (must start/end with alnum).")
    return cs_id

def _dump_yaml(data: dict) -> str:
    # Minimal YAML emitter (sufficient for our metadata shape); avoid external deps.
    def q(v: str) -> str:
        if v == "" or any(c in v for c in [":", "#", "\n", "\r", "\t", "{", "}", "[", "]", ",", """, "'"]) or v.strip() != v:
            return json.dumps(v, ensure_ascii=False)
        return v
    lines = []
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {q(str(item))}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for kk, vv in v.items():
                lines.append(f"  {kk}: {q(str(vv))}")
        else:
            lines.append(f"{k}: {q(str(v))}")
    return "\n".join(lines) + "\n"

def _write_case_study_files(cs_dir: Path, meta: dict, md_title: str, fmt: str) -> tuple[Path, Path]:
    cs_dir.mkdir(parents=True, exist_ok=True)
    meta_path = cs_dir / (f"metadata.{ 'yaml' if fmt=='yaml' else 'json' }")
    md_path = cs_dir / "case_study.md"
    if fmt == "yaml":
        meta_text = _dump_yaml(meta)
    else:
        meta_text = json.dumps(meta, indent=2, ensure_ascii=False) + "\n"
    meta_path.write_text(meta_text, encoding="utf-8")
    if not md_path.exists():
        md = (
            f"# {md_title}\n\n"
            f"**Case study ID:** `{meta['id']}`\n\n"
            "## Summary\n\n"
            f"{meta.get('summary','').strip()}\n\n"
            "## Context\n\n"
            "## Approach\n\n"
            "## Outcomes\n\n"
            "## Artifacts & Links\n\n"
        )
        md_path.write_text(md, encoding="utf-8")
    return meta_path, md_path

def _upsert_index_entry(index: dict, entry: dict) -> None:
    arts = index.setdefault("artifacts", [])
    for i, a in enumerate(arts):
        if isinstance(a, dict) and a.get("id") == entry["id"]:
            arts[i] = {**a, **entry}
            return
    arts.append(entry)

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="add_case_study", description="Scaffold a new case-study artifact and update ARTIFACT_INDEX.")
    p.add_argument("--id", dest="cs_id", help="Case study id (lowercase; may include '-'/'_').")
    p.add_argument("--title", help="Human-readable title.")
    p.add_argument("--summary", help="One-paragraph summary.")
    p.add_argument("--date", dest="cs_date", help="ISO date (YYYY-MM-DD). Default: today.")
    p.add_argument("--tags", help="Comma-separated tags.")
    p.add_argument("--authors", help="Comma-separated authors.")
    p.add_argument("--format", choices=["json", "yaml"], default="json", help="Metadata file format.")
    p.add_argument("--force", action="store_true", help="Overwrite existing metadata file and update index entry.")
    args = p.parse_args(argv)

    CASE_STUDIES_DIR.mkdir(parents=True, exist_ok=True)

    title = args.title or ""
    cs_id = args.cs_id or ""
    if not cs_id:
        if not title:
            title = _prompt("Title", required=True)
        cs_id = _prompt("ID (blank to derive from title)", default=_safe_id(title) or None)
    cs_id = _ensure_valid_id(cs_id)

    if not title:
        title = _prompt("Title", default=cs_id.replace("-", " ").replace("_", " ").title(), required=True)
    summary = args.summary or _prompt("Summary", default="", required=not _is_tty())

    cs_date = args.cs_date or _prompt("Date (YYYY-MM-DD)", default=str(date.today()))
    # Basic date sanity check
    if cs_date and not re.match(r"^\d{4}-\d{2}-\d{2}$", cs_date):
        raise SystemExit("Invalid --date; expected YYYY-MM-DD.")

    tags = _split_csv(args.tags or _prompt("Tags (comma-separated)", default=""))
    authors = _split_csv(args.authors or _prompt("Authors (comma-separated)", default=""))

    cs_dir = CASE_STUDIES_DIR / cs_id
    meta = {
        "type": "case_study",
        "id": cs_id,
        "title": title,
        "summary": summary,
        "date": cs_date,
        "tags": tags,
        "authors": authors,
        "paths": {
            "dir": str(cs_dir.relative_to(OUTPUTS_DIR)).replace(os.sep, "/"),
            "markdown": str((cs_dir / "case_study.md").relative_to(OUTPUTS_DIR)).replace(os.sep, "/"),
        },
    }

    meta_path = cs_dir / (f"metadata.{ 'yaml' if args.format=='yaml' else 'json' }")
    if meta_path.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing: {meta_path} (use --force).")

    meta_out, md_out = _write_case_study_files(cs_dir, meta, title, args.format)

    index = _load_index()
    entry = {
        "id": cs_id,
        "type": "case_study",
        "title": title,
        "date": cs_date,
        "filePath": str(meta_out.relative_to(OUTPUTS_DIR)).replace(os.sep, "/"),
        "markdownPath": str(md_out.relative_to(OUTPUTS_DIR)).replace(os.sep, "/"),
        "tags": tags,
    }
    _upsert_index_entry(index, entry)
    _write_index(index)

    print(f"OK: created/updated {meta_out} and {md_out}; index updated at {INDEX_PATH}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
