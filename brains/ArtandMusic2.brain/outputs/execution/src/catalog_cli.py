#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')
SCHEMAS = ROOT / 'schemas'
OUT_CATALOG = ROOT / 'outputs' / 'catalog'
INDEX_PATH = OUT_CATALOG / 'index.json'
CASE_SCHEMA_PATH = SCHEMAS / 'case-study.schema.json'
CAT_SCHEMA_PATH = SCHEMAS / 'catalog.schema.json'
TEMPLATE_PATH = ROOT / 'src' / 'templates' / 'case_study.stub.json'


def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def slugify(s: str) -> str:
    s = (s or '').strip().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s or 'case-study'


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_schema(path: Path):
    if not path.exists():
        raise SystemExit(f'MISSING_SCHEMA:{path}')
    return load_json(path)


def validate_json(instance, schema, name='document'):
    try:
        import jsonschema
        jsonschema.Draft202012Validator(schema).validate(instance)
    except ModuleNotFoundError as e:
        raise SystemExit('MISSING_DEP:jsonschema (pip install jsonschema)') from e
    except Exception as e:
        raise SystemExit(f'INVALID_{name.upper()}:{e}') from e


def new_case_study_base():
    if TEMPLATE_PATH.exists():
        base = load_json(TEMPLATE_PATH)
        if isinstance(base, dict):
            return base
    return {
        "id": "",
        "title": "",
        "summary": "",
        "date_published": "",
        "tags": [],
        "citations": [],
        "rights": {"license": "", "holder": "", "notes": ""},
        "links": [],
        "created_at": "",
        "updated_at": ""
    }


def parse_tags(s):
    if not s:
        return []
    return [t.strip() for t in s.split(',') if t.strip()]


def ensure_unique_id(desired_id: str) -> str:
    OUT_CATALOG.mkdir(parents=True, exist_ok=True)
    existing = {p.stem for p in OUT_CATALOG.glob('*.json') if p.name != INDEX_PATH.name}
    cid = desired_id
    i = 2
    while cid in existing:
        cid = f"{desired_id}-{i}"
        i += 1
    return cid


def load_index():
    if INDEX_PATH.exists():
        idx = load_json(INDEX_PATH)
        if isinstance(idx, dict):
            return idx
    return {"version": 1, "generated_at": _utc_now(), "entries": []}


def upsert_index_entry(index, case_obj, rel_path):
    entries = index.get("entries") or []
    index["entries"] = entries
    found = None
    for e in entries:
        if isinstance(e, dict) and e.get("id") == case_obj.get("id"):
            found = e
            break
    rec = {
        "id": case_obj.get("id"),
        "title": case_obj.get("title"),
        "path": str(rel_path).replace('\\', '/'),
        "tags": case_obj.get("tags", []),
        "updated_at": case_obj.get("updated_at") or _utc_now(),
    }
    if found is None:
        entries.append(rec)
    else:
        found.update(rec)
    index["generated_at"] = _utc_now()
    return index


def cmd_create(args):
    title = args.title.strip()
    base_id = args.id.strip() if args.id else slugify(title)
    cid = ensure_unique_id(base_id)

    obj = new_case_study_base()
    obj["id"] = cid
    obj["title"] = title
    if args.summary is not None:
        obj["summary"] = args.summary
    if args.date_published:
        obj["date_published"] = args.date_published
    if args.tags:
        obj["tags"] = parse_tags(args.tags)
    if args.license or args.rights_holder or args.rights_notes:
        rights = obj.get("rights") if isinstance(obj.get("rights"), dict) else {}
        rights.update({
            "license": args.license or rights.get("license", ""),
            "holder": args.rights_holder or rights.get("holder", ""),
            "notes": args.rights_notes or rights.get("notes", ""),
        })
        obj["rights"] = rights

    now = _utc_now()
    obj["created_at"] = obj.get("created_at") or now
    obj["updated_at"] = now

    case_schema = load_schema(CASE_SCHEMA_PATH)
    validate_json(obj, case_schema, name="case_study")

    OUT_CATALOG.mkdir(parents=True, exist_ok=True)
    case_path = OUT_CATALOG / f"{cid}.json"
    dump_json(case_path, obj)

    index = load_index()
    rel = case_path.relative_to(ROOT)
    index = upsert_index_entry(index, obj, rel)

    cat_schema = load_schema(CAT_SCHEMA_PATH)
    validate_json(index, cat_schema, name="catalog")
    dump_json(INDEX_PATH, index)

    print(f"CREATED:{rel}")


def cmd_validate(_args):
    case_schema = load_schema(CASE_SCHEMA_PATH)
    cat_schema = load_schema(CAT_SCHEMA_PATH)

    OUT_CATALOG.mkdir(parents=True, exist_ok=True)
    validated = 0
    for p in sorted(OUT_CATALOG.glob("*.json")):
        if p.name == INDEX_PATH.name:
            continue
        obj = load_json(p)
        validate_json(obj, case_schema, name=f"case_study:{p.name}")
        validated += 1

    idx = load_index()
    validate_json(idx, cat_schema, name="catalog")
    print(f"VALID_OK:cases={validated};index={'present' if INDEX_PATH.exists() else 'created_in_memory'}")


def build_parser():
    ap = argparse.ArgumentParser(prog="catalog_cli", description="Case-study catalog CLI (create + validate).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="Create/add a new case study entry and update the catalog index.")
    c.add_argument("--title", required=True)
    c.add_argument("--id", default=None, help="Optional explicit id/slug; defaults to slugified title.")
    c.add_argument("--summary", default=None)
    c.add_argument("--date-published", default="")
    c.add_argument("--tags", default="", help="Comma-separated tags.")
    c.add_argument("--license", default="", help="Rights/license identifier or URL.")
    c.add_argument("--rights-holder", default="", help="Rights holder/owner.")
    c.add_argument("--rights-notes", default="", help="Rights notes.")
    c.set_defaults(func=cmd_create)

    v = sub.add_parser("validate", help="Validate all case studies and the catalog index against schemas.")
    v.set_defaults(func=cmd_validate)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
