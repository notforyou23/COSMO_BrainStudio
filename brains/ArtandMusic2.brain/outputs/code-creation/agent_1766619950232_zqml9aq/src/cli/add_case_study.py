#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if not s:
        raise SystemExit("ERROR: slug/title produced empty slug; provide --slug explicitly.")
    return s


def _load_schema(schema_path: Path) -> Dict[str, Any]:
    if not schema_path.exists():
        raise SystemExit(
            f"ERROR: schema not found: {schema_path}\n"
            "Create schemas/METADATA_SCHEMA.json and re-run."
        )
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"ERROR: failed to load schema JSON: {schema_path}\n{e}")


def _type_name(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int) and not isinstance(v, bool):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def _validate_minimal(schema: Dict[str, Any], doc: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(doc, dict):
        return [f"Document must be an object, got {_type_name(doc)}."]
    required = schema.get("required", [])
    props = schema.get("properties", {})
    for k in required:
        if k not in doc:
            errs.append(f"Missing required field: {k}")
    if schema.get("additionalProperties") is False and isinstance(props, dict):
        extra = sorted(set(doc.keys()) - set(props.keys()))
        if extra:
            errs.append(f"Unknown fields not allowed by schema: {', '.join(extra)}")
    for k, spec in (props or {}).items():
        if k not in doc:
            continue
        v = doc[k]
        if not isinstance(spec, dict):
            continue
        t = spec.get("type")
        if t:
            ok = True
            if t == "string":
                ok = isinstance(v, str)
            elif t == "integer":
                ok = isinstance(v, int) and not isinstance(v, bool)
            elif t == "number":
                ok = (isinstance(v, int) and not isinstance(v, bool)) or isinstance(v, float)
            elif t == "boolean":
                ok = isinstance(v, bool)
            elif t == "object":
                ok = isinstance(v, dict)
            elif t == "array":
                ok = isinstance(v, list)
            if not ok:
                errs.append(f"Field '{k}' must be of type {t}, got {_type_name(v)}")
        if spec.get("format") == "uri" and isinstance(v, str):
            if not re.match(r"^https?://", v):
                errs.append(f"Field '{k}' must be an http(s) URL.")
        if spec.get("format") == "date" and isinstance(v, str):
            if not re.match(r"^\\d{4}-\\d{2}-\\d{2}$", v):
                errs.append(f"Field '{k}' must be YYYY-MM-DD.")
        if isinstance(v, list) and isinstance(spec.get("items"), dict):
            it = spec["items"]
            it_t = it.get("type")
            it_fmt = it.get("format")
            for i, item in enumerate(v):
                if it_t == "string" and not isinstance(item, str):
                    errs.append(f"Field '{k}[{i}]' must be string, got {_type_name(item)}")
                if it_fmt == "uri" and isinstance(item, str) and not re.match(r"^https?://", item):
                    errs.append(f"Field '{k}[{i}]' must be an http(s) URL.")
    # Lightweight cross-field expectations (helpful even if schema is permissive)
    if "authoritative_urls" in doc:
        urls = doc.get("authoritative_urls")
        if not (isinstance(urls, list) and all(isinstance(u, str) for u in urls)):
            errs.append("Field 'authoritative_urls' must be an array of strings (http(s) URLs).")
    rights = doc.get("rights") if isinstance(doc, dict) else None
    if rights is not None and not isinstance(rights, dict):
        errs.append("Field 'rights' must be an object.")
    return errs


def _write_if_absent(path: Path, text: str) -> None:
    if path.exists():
        raise SystemExit(f"ERROR: refuses to overwrite existing file: {path}")
    path.write_text(text, encoding="utf-8")


def build_metadata(slug: str, title: str, summary: str, license_id: str, rights_holder: str,
                   urls: List[str], published: str | None) -> Dict[str, Any]:
    md: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "id": slug,
        "title": title,
        "summary": summary,
        "published_date": published or date.today().isoformat(),
        "authoritative_urls": urls,
        "rights": {
            "license": license_id,
            "rights_holder": rights_holder,
            "notes": "Provide clear licensing and attribution; no content is downloaded by this tool."
        },
        "tags": [],
    }
    return md


def build_md_stub(title: str, json_name: str) -> str:
    return (
        f"# {title}\\n\\n"
        f"Metadata: `{json_name}`\\n\\n"
        "## Summary\\n\\n"
        "- What is this case study about?\\n\\n"
        "## Methods\\n\\n"
        "- What methods were used?\\n\\n"
        "## Sources (authoritative links only)\\n\\n"
        "- List authoritative URLs that support the claims.\\n"
    )


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="add_case_study", description="Create a case-study JSON/MD stub and validate metadata.")
    p.add_argument("--title", required=True, help="Case study title.")
    p.add_argument("--slug", help="Optional stable identifier; defaults to slugified title.")
    p.add_argument("--summary", default="", help="One-paragraph summary (can be empty initially).")
    p.add_argument("--published-date", dest="published_date", help="YYYY-MM-DD (defaults to today).")
    p.add_argument("--license", dest="license_id", required=True, help="License identifier (e.g., CC-BY-4.0, CC0-1.0, Proprietary).")
    p.add_argument("--rights-holder", required=True, help="Entity holding rights (person/org).")
    p.add_argument("--url", dest="urls", action="append", default=[], help="Authoritative URL (repeatable, http(s) only).")
    p.add_argument("--outdir", default=str(Path("outputs") / "case_studies"), help="Output directory (relative or absolute).")
    args = p.parse_args(argv)

    slug = _slugify(args.slug or args.title)
    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = (Path.cwd() / outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    schema_path = (Path.cwd() / "schemas" / "METADATA_SCHEMA.json").resolve()
    schema = _load_schema(schema_path)

    for u in args.urls:
        if not re.match(r"^https?://", u):
            raise SystemExit(f"ERROR: --url must be http(s): {u}")

    meta = build_metadata(
        slug=slug,
        title=args.title.strip(),
        summary=args.summary.strip(),
        license_id=args.license_id.strip(),
        rights_holder=args.rights_holder.strip(),
        urls=args.urls,
        published=args.published_date.strip() if args.published_date else None,
    )

    errs = _validate_minimal(schema, meta)
    if errs:
        msg = "ERROR: metadata failed schema validation:\\n" + "\\n".join(f"- {e}" for e in errs)
        raise SystemExit(msg)

    json_path = outdir / f"{slug}.json"
    md_path = outdir / f"{slug}.md"
    _write_if_absent(json_path, json.dumps(meta, indent=2, ensure_ascii=False) + "\\n")
    _write_if_absent(md_path, build_md_stub(args.title.strip(), json_path.name))

    sys.stdout.write(f"OK: wrote {json_path}\\nOK: wrote {md_path}\\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
