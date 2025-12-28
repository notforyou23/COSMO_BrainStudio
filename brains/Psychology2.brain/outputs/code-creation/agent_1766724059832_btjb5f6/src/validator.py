#!/usr/bin/env python3
import argparse, csv, json, sys
from pathlib import Path

def eprint(*a): print(*a, file=sys.stderr)

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def iter_records(input_path: Path):
    suf = input_path.suffix.lower()
    if suf == ".jsonl":
        with input_path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line: 
                    continue
                try:
                    yield i, json.loads(line)
                except Exception as ex:
                    yield i, {"__parse_error__": f"JSONL parse error: {ex}"}
    elif suf == ".json":
        try:
            obj = load_json(input_path)
        except Exception as ex:
            yield 1, {"__parse_error__": f"JSON parse error: {ex}"}
            return
        if isinstance(obj, list):
            for i, rec in enumerate(obj, 1):
                yield i, rec
        else:
            yield 1, obj
    elif suf == ".csv":
        with input_path.open("r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for i, row in enumerate(r, 2):
                yield i, row
    else:
        raise SystemExit(f"Unsupported input extension: {suf} (use .json, .jsonl, .csv)")

def _allowed_for_field(codebook: dict, field: str):
    for topk in ("fields", "categories", "taxonomy", "task_taxonomy"):
        m = codebook.get(topk)
        if isinstance(m, dict) and field in m and isinstance(m[field], dict):
            d = m[field]
            for k in ("allowed_values", "allowed", "values", "labels", "options"):
                v = d.get(k)
                if isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v):
                    return set(v)
    cats = codebook.get("categories")
    if isinstance(cats, list):
        for c in cats:
            if isinstance(c, dict) and c.get("field") == field:
                v = c.get("allowed_values") or c.get("labels") or c.get("values")
                if isinstance(v, list):
                    return set(v)
    return None

def build_constraints(schema: dict, codebook: dict):
    props = schema.get("properties") if isinstance(schema, dict) else {}
    props = props if isinstance(props, dict) else {}
    required = schema.get("required") if isinstance(schema, dict) else []
    required = required if isinstance(required, list) else []
    enums = {}
    types = {}
    for k, p in props.items():
        if not isinstance(p, dict): 
            continue
        if "enum" in p and isinstance(p["enum"], list):
            enums[k] = set(p["enum"])
        if "type" in p:
            types[k] = p["type"]
    allowed = {}
    for k in props.keys():
        a = _allowed_for_field(codebook, k)
        if a:
            allowed[k] = a
    return required, types, enums, allowed

def _type_ok(v, t):
    if t is None: 
        return True
    if isinstance(t, list):
        return any(_type_ok(v, x) for x in t)
    if t == "string":
        return isinstance(v, str)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "boolean":
        return isinstance(v, bool)
    if t == "array":
        return isinstance(v, list)
    if t == "object":
        return isinstance(v, dict)
    return True

def validate_record(rec, required, types, enums, allowed):
    errs = []
    if not isinstance(rec, dict):
        return ["record is not an object/dict"]
    if "__parse_error__" in rec:
        return [rec["__parse_error__"]]
    for k in required:
        if k not in rec or rec[k] is None or (isinstance(rec[k], str) and rec[k].strip() == ""):
            errs.append(f"missing required field: {k}")
    for k, t in types.items():
        if k in rec and rec[k] is not None:
            if isinstance(rec[k], str) and t in ("integer", "number", "boolean", "array", "object"):
                continue
            if not _type_ok(rec[k], t):
                errs.append(f"field {k} type violation: expected {t}, got {type(rec[k]).__name__}")
    for k, ev in enums.items():
        if k in rec and rec[k] is not None:
            v = rec[k]
            if isinstance(v, list):
                bad = [x for x in v if x not in ev]
                if bad:
                    errs.append(f"field {k} enum violation: {bad}")
            else:
                if v not in ev:
                    errs.append(f"field {k} enum violation: {v}")
    for k, av in allowed.items():
        if k in rec and rec[k] is not None:
            v = rec[k]
            if isinstance(v, list):
                bad = [x for x in v if x not in av]
                if bad:
                    errs.append(f"field {k} category violation: {bad}")
            else:
                if v not in av:
                    errs.append(f"field {k} category violation: {v}")
    return errs

def main():
    ap = argparse.ArgumentParser(description="Validate annotation files against schema and codebook.")
    ap.add_argument("input", help="Path to annotations (.json/.jsonl/.csv)")
    ap.add_argument("--schema", default="outputs/annotation_schema_v0.1.json", help="Path to JSON schema")
    ap.add_argument("--codebook", default="outputs/task_taxonomy_codebook_v0.1.json", help="Path to taxonomy codebook")
    ap.add_argument("--max-errors", type=int, default=200, help="Stop after this many errors")
    args = ap.parse_args()

    base = Path(__file__).resolve().parents[1]
    schema_path = (base / args.schema).resolve()
    codebook_path = (base / args.codebook).resolve()
    input_path = Path(args.input).resolve()

    schema = load_json(schema_path)
    codebook = load_json(codebook_path)
    required, types, enums, allowed = build_constraints(schema, codebook)

    total = 0
    err_count = 0
    for loc, rec in iter_records(input_path):
        total += 1
        errs = validate_record(rec, required, types, enums, allowed)
        if errs:
            rid = rec.get("id") if isinstance(rec, dict) else None
            prefix = f"{input_path.name}:{loc}" + (f" id={rid}" if rid else "")
            for msg in errs:
                err_count += 1
                eprint(f"ERROR {prefix}: {msg}")
                if err_count >= args.max_errors:
                    eprint(f"Stopped at --max-errors={args.max_errors}")
                    eprint(f"SUMMARY total={total} errors={err_count}")
                    return 1
    if err_count:
        eprint(f"SUMMARY total={total} errors={err_count}")
        return 1
    print(f"SUMMARY total={total} errors=0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
