from __future__ import annotations
from pathlib import Path
import json, sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "METADATA_SCHEMA.json"
OUT_DIR = ROOT / "outputs" / "qa"
OUT_JSON = OUT_DIR / "schema_validation.json"
OUT_MD = OUT_DIR / "schema_validation.md"

REQUIRED_CHECKLIST = {
  "claim_verbatim": {"any": ["claim_verbatim"]},
  "claimant_or_source": {"any": ["claimant", "source", "claimant_or_source"]},
  "date": {"any": ["date", "claim_date", "observed_date"]},
  "link_or_screenshot_ref": {"any": ["link", "url", "screenshot", "screenshot_reference", "screenshot_ref", "evidence_ref", "reference"]},
  "provenance_anchor": {"any": ["doi", "dataset_link", "dataset_url", "dataset_doi", "provenance", "source_doi", "source_dataset_link"]},
}

def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"__read_error__": str(e)}

def _iter_schema_property_names(node):
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            for k, v in props.items():
                yield k
                yield from _iter_schema_property_names(v)
        for k, v in node.items():
            if k != "properties":
                yield from _iter_schema_property_names(v)
    elif isinstance(node, list):
        for it in node:
            yield from _iter_schema_property_names(it)

def _schema_has_any(schema, names):
    s = {n.lower() for n in _iter_schema_property_names(schema)}
    return any(n.lower() in s for n in names)

def _find_metadata_files():
    excluded = {str((ROOT / "schemas").resolve()), str((ROOT / "outputs").resolve()), str((ROOT / "scripts").resolve())}
    cands = []
    for p in ROOT.rglob("*.json"):
        rp = str(p.resolve())
        if any(rp.startswith(e + str(Path("/"))) or rp == e for e in excluded):
            continue
        nm = p.name.lower()
        if "metadata" in nm or nm in {"meta.json"}:
            cands.append(p)
    # de-dup and stable sort
    seen = set()
    out = []
    for p in sorted(cands, key=lambda x: str(x)):
        if p.resolve() in seen:
            continue
        seen.add(p.resolve())
        out.append(p)
    return out

def _validate_with_jsonschema(instance, schema):
    try:
        import jsonschema
        from jsonschema import Draft7Validator
    except Exception as e:
        return [{"path": "", "message": f"jsonschema_unavailable: {e.__class__.__name__}: {e}"}]
    try:
        v = Draft7Validator(schema)
        errs = []
        for e in sorted(v.iter_errors(instance), key=lambda x: (list(x.path), x.message)):
            pth = "/".join(str(x) for x in e.absolute_path)
            errs.append({"path": pth, "message": e.message})
        return errs
    except Exception as e:
        return [{"path": "", "message": f"jsonschema_validation_failed: {e.__class__.__name__}: {e}"}]

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    schema_doc = _read_json(SCHEMA_PATH)
    schema_ok = isinstance(schema_doc, dict) and "__read_error__" not in schema_doc

    checklist_presence = {}
    if schema_ok:
        for k, spec in REQUIRED_CHECKLIST.items():
            checklist_presence[k] = _schema_has_any(schema_doc, spec["any"])
    else:
        checklist_presence = {k: False for k in REQUIRED_CHECKLIST}

    schema_check_ok = all(checklist_presence.values())
    schema_check_missing = [k for k, v in checklist_presence.items() if not v]

    files = _find_metadata_files()
    results = []
    for p in files:
        rel = str(p.relative_to(ROOT))
        doc = _read_json(p)
        if isinstance(doc, dict) and "__read_error__" in doc:
            results.append({"file": rel, "ok": False, "errors": [{"path": "", "message": f"read_failed: {doc['__read_error__']}"}]})
            continue
        if not schema_ok:
            results.append({"file": rel, "ok": False, "errors": [{"path": "", "message": "schema_unreadable_or_invalid"}]})
            continue
        errs = _validate_with_jsonschema(doc, schema_doc)
        results.append({"file": rel, "ok": len(errs) == 0, "errors": errs})

    total = len(results)
    ok = sum(1 for r in results if r["ok"])
    fail = total - ok

    out = {
        "generated_at_utc": now,
        "schema_path": str(SCHEMA_PATH.relative_to(ROOT)) if SCHEMA_PATH.exists() else str(SCHEMA_PATH),
        "schema_loaded_ok": schema_ok,
        "schema_intake_checklist_presence": checklist_presence,
        "schema_intake_checklist_ok": schema_check_ok,
        "schema_intake_checklist_missing": schema_check_missing,
        "discovered_metadata_files": total,
        "validated_ok": ok,
        "validated_failed": fail,
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = []
    lines.append("# Schema validation report")
    lines.append("")
    lines.append(f"- Generated: `{now}`")
    lines.append(f"- Schema: `{out['schema_path']}` (loaded_ok={schema_ok})")
    lines.append(f"- Intake checklist encoded in schema: `{schema_check_ok}`")
    if schema_check_missing:
        lines.append(f"  - Missing checklist fields (by presence scan): {', '.join(schema_check_missing)}")
    lines.append(f"- Metadata files discovered: `{total}`")
    lines.append(f"- Valid: `{ok}`  Invalid: `{fail}`")
    if fail:
        lines.append("")
        lines.append("## Failures (first 20)")
        shown = 0
        for r in results:
            if r["ok"]:
                continue
            shown += 1
            if shown > 20:
                break
            msg = r["errors"][0]["message"] if r.get("errors") else "unknown_error"
            lines.append(f"- `{r['file']}`: {msg}")
    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return 0 if (schema_ok and schema_check_ok and fail == 0) else 2

if __name__ == "__main__":
    raise SystemExit(main())
