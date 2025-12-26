#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]

def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _iter_json_paths(obj: Any, prefix: str = "$") -> List[Tuple[str, Any]]:
    out = [(prefix, obj)]
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(_iter_json_paths(v, prefix + "." + str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(_iter_json_paths(v, prefix + f"[{i}]"))
    return out

def _extract_citations(doc: Any) -> List[Tuple[str, Any]]:
    hits = []
    keys = {"citation","citations","reference","references","bibliography","works_cited"}
    for p, v in _iter_json_paths(doc):
        if isinstance(v, dict):
            for k in list(v.keys()):
                if str(k).lower() in keys:
                    hits.append((p + "." + str(k), v[k]))
        elif isinstance(v, list) and p.split(".")[-1].lower() in keys:
            hits.append((p, v))
    return hits

_CIT_STR_OK = re.compile(r"(https?://|doi\s*:\s*\S+|\b10\.\d{4,9}/\S+|\b(19|20)\d{2}\b)", re.I)

def _citation_ok(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        s = val.strip()
        return (not s) or bool(_CIT_STR_OK.search(s))
    if isinstance(val, dict):
        if any(str(k).lower() in {"url","doi"} and str(val.get(k,"")).strip() for k in val.keys()):
            return True
        yr = val.get("year")
        if isinstance(yr, int) and 1900 <= yr <= 2100:
            if any(str(k).lower() in {"author","authors"} and val.get(k) for k in val.keys()):
                return True
        t = str(val.get("title","")).strip()
        return bool(t) and bool(_CIT_STR_OK.search(t))
    if isinstance(val, list):
        return all(_citation_ok(x) for x in val)
    return True

@dataclass
class VError:
    category: str
    message: str
    json_path: str

def _validate_with_jsonschema(schema: Dict[str, Any], doc: Any) -> List[VError]:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator, Draft7Validator
        Validator = Draft202012Validator if str(schema.get("$schema","")).endswith("2020-12/schema") else Draft7Validator
        v = Validator(schema)
        errs = []
        for e in sorted(v.iter_errors(doc), key=lambda x: x.path):
            jp = "$"
            for part in list(e.absolute_path):
                jp += f"[{part}]" if isinstance(part, int) else "." + str(part)
            cat = "schema_violation"
            if e.validator == "required":
                cat = "missing_required_fields"
            elif e.validator == "enum":
                cat = "invalid_enums"
            errs.append(VError(cat, e.message, jp))
        return errs
    except Exception:
        return []

def _fallback_validate(schema: Dict[str, Any], doc: Any) -> List[VError]:
    errs: List[VError] = []
    def walk(s: Dict[str, Any], o: Any, p: str):
        if not isinstance(s, dict):
            return
        if s.get("type") == "object" and isinstance(o, dict):
            req = s.get("required") or []
            for r in req:
                if r not in o:
                    errs.append(VError("missing_required_fields", f"'{r}' is a required property", p))
            props = s.get("properties") or {}
            for k, ss in props.items():
                if k in o:
                    walk(ss, o[k], p + "." + str(k))
        if "enum" in s:
            if o not in s["enum"]:
                errs.append(VError("invalid_enums", f"value {o!r} not in enum {s['enum']!r}", p))
        if s.get("type") == "array" and isinstance(o, list):
            it = s.get("items")
            if isinstance(it, dict):
                for i, v in enumerate(o):
                    walk(it, v, p + f"[{i}]")
    walk(schema, doc, "$")
    return errs

def _find_inputs(root: Path) -> List[Path]:
    pats = ["**/*metadata*.json", "**/metadata.json"]
    outs = set()
    for pat in pats:
        for p in root.glob(pat):
            if p.name == "METADATA_SCHEMA.json":
                continue
            rel = str(p.relative_to(root)).lower()
            if rel.startswith("outputs/qa/") or rel.endswith("schema_validation.json"):
                continue
            outs.add(p)
    return sorted(outs)

def _failure_log_path(root: Path) -> Path:
    cands = [
        root/"outputs/qa/pilot_failure_modes.jsonl",
        root/"outputs/qa/pilot_failure_modes_log.jsonl",
        root/"outputs/qa/failure_modes.jsonl",
    ]
    for c in cands:
        if c.exists():
            return c
    return cands[0]

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Validate pilot artifact metadata against METADATA_SCHEMA.json")
    ap.add_argument("--schema", default=str(ROOT/"METADATA_SCHEMA.json"))
    ap.add_argument("--inputs", nargs="*", help="Metadata JSON files to validate; if omitted, auto-discover")
    ap.add_argument("--out_json", default=str(ROOT/"outputs/qa/schema_validation.json"))
    ap.add_argument("--out_md", default=str(ROOT/"outputs/qa/schema_validation_summary.md"))
    ap.add_argument("--failure_log", default=str(_failure_log_path(ROOT)))
    args = ap.parse_args(argv)

    schema_p = Path(args.schema)
    if not schema_p.exists():
        print(f"ERROR: schema not found: {schema_p}", file=sys.stderr)
        return 2
    schema = _read_json(schema_p)

    inputs = [Path(p) for p in (args.inputs or [])] or _find_inputs(ROOT)
    inputs = [p for p in inputs if p.exists()]
    out_json = Path(args.out_json); out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    results = []
    counts = {"total": 0, "valid": 0, "invalid": 0}
    cat_totals: Dict[str, int] = {"missing_required_fields": 0, "invalid_enums": 0, "citation_formatting": 0, "schema_violation": 0, "read_error": 0}
    ts = _now_iso()

    for p in inputs:
        rel = str(p.relative_to(ROOT)) if p.is_absolute() and str(p).startswith(str(ROOT)) else str(p)
        rec = {"path": rel, "valid": True, "errors": []}
        counts["total"] += 1
        try:
            doc = _read_json(p)
        except Exception as e:
            rec["valid"] = False
            rec["errors"].append({"category":"read_error","message":str(e),"json_path":"$"})
            cat_totals["read_error"] += 1
            results.append(rec)
            continue

        verrs = _validate_with_jsonschema(schema, doc)
        if not verrs:
            verrs = _fallback_validate(schema, doc)

        for jp, cval in _extract_citations(doc):
            if not _citation_ok(cval):
                verrs.append(VError("citation_formatting", "citation/reference appears unparseable or missing URL/DOI/year", jp))

        if verrs:
            rec["valid"] = False
            for e in verrs:
                rec["errors"].append({"category": e.category, "message": e.message, "json_path": e.json_path})
                cat_totals[e.category] = cat_totals.get(e.category, 0) + 1
        results.append(rec)
        counts["valid" if rec["valid"] else "invalid"] += 1

    payload = {
        "timestamp_utc": ts,
        "schema_path": str(schema_p.relative_to(ROOT)) if str(schema_p).startswith(str(ROOT)) else str(schema_p),
        "inputs_discovered": len(inputs),
        "counts": counts,
        "category_totals": cat_totals,
        "results": results,
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    bad = [r for r in results if not r["valid"]]
    lines = []
    lines.append(f"# Schema validation summary\n")
    lines.append(f"- Timestamp (UTC): `{ts}`\n")
    lines.append(f"- Total files: **{counts['total']}** | Valid: **{counts['valid']}** | Invalid: **{counts['invalid']}**\n")
    lines.append("## Failure categories\n")
    for k in ["missing_required_fields","invalid_enums","citation_formatting","schema_violation","read_error"]:
        if cat_totals.get(k, 0):
            lines.append(f"- `{k}`: **{cat_totals[k]}**\n")
    if bad:
        lines.append("\n## Invalid files\n")
        for r in bad[:50]:
            cats = {}
            for e in r["errors"]:
                cats[e["category"]] = cats.get(e["category"], 0) + 1
            cat_str = ", ".join([f"{k}:{v}" for k, v in sorted(cats.items())])
            lines.append(f"- `{r['path']}` ({cat_str})\n")
        if len(bad) > 50:
            lines.append(f"- ... and {len(bad)-50} more\n")
    out_md.write_text("".join(lines), encoding="utf-8")

    flog = Path(args.failure_log)
    flog.parent.mkdir(parents=True, exist_ok=True)
    cats_of_interest = {"missing_required_fields","invalid_enums","citation_formatting"}
    with flog.open("a", encoding="utf-8") as f:
        for r in bad:
            cats = [e["category"] for e in r["errors"] if e["category"] in cats_of_interest]
            if not cats:
                continue
            counts_by = {}
            for c in cats:
                counts_by[c] = counts_by.get(c, 0) + 1
            f.write(json.dumps({
                "timestamp_utc": ts,
                "source": "schema_validation",
                "file": r["path"],
                "categories": sorted(counts_by.keys()),
                "category_counts": counts_by,
            }, ensure_ascii=False) + "\n")

    print(f"STATUS: wrote {out_json} and {out_md}; appended failure modes to {flog}; invalid={counts['invalid']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
