#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

try:
    import jsonschema
except Exception:  # pragma: no cover
    jsonschema = None

DEFAULT_SCHEMA = Path("outputs/annotation_schema_v0.1.json")

def eprint(msg: str) -> None:
    sys.stderr.write(msg.rstrip() + "\n")

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as ex:
        raise SystemExit(f"Failed to read JSON: {path}: {ex}")

def iter_annotations(path: Path):
    suf = path.suffix.lower()
    if suf == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                s = line.strip()
                if not s:
                    continue
                try:
                    yield i, json.loads(s)
                except Exception as ex:
                    yield i, {"__parse_error__": f"JSON decode error: {ex}", "__raw__": s}
    elif suf == ".json":
        obj = load_json(path)
        if isinstance(obj, list):
            for i, item in enumerate(obj, start=1):
                yield i, item
        else:
            yield 1, obj
    else:
        raise SystemExit(f"Unsupported annotation file type: {path}")

def validate_with_schema(ann, validator):
    if validator is None:
        return []
    errs = []
    for err in sorted(validator.iter_errors(ann), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(x) for x in err.absolute_path) or "<root>"
        errs.append(f"{loc}: {err.message}")
    return errs

def _get(obj, path, default=None):
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

def validate_logical_constraints(ann):
    errs = []
    if not isinstance(ann, dict):
        return ["<root>: annotation must be an object"]
    if "__parse_error__" in ann:
        return [f"<parse>: {ann['__parse_error__']}"]

    # Common, schema-hard-to-express checks (only enforced when fields exist)
    text = ann.get("text")
    if text is not None and not isinstance(text, str):
        errs.append("text: must be a string")
    spans = ann.get("spans")
    if spans is not None:
        if not isinstance(spans, list):
            errs.append("spans: must be a list")
        else:
            for idx, sp in enumerate(spans):
                if not isinstance(sp, dict):
                    errs.append(f"spans[{idx}]: must be an object")
                    continue
                start = sp.get("start"); end = sp.get("end")
                if not isinstance(start, int) or not isinstance(end, int):
                    errs.append(f"spans[{idx}]: start/end must be integers")
                    continue
                if start < 0 or end < 0 or end < start:
                    errs.append(f"spans[{idx}]: invalid range start={start} end={end}")
                if isinstance(text, str) and end > len(text):
                    errs.append(f"spans[{idx}]: end {end} exceeds text length {len(text)}")
                label = sp.get("label")
                if label is not None and not isinstance(label, str):
                    errs.append(f"spans[{idx}].label: must be a string")

    # If a single-label field exists, ensure it's consistent with optional choices
    label = ann.get("label")
    if label is not None and not isinstance(label, str):
        errs.append("label: must be a string")
    choices = ann.get("choices")
    if choices is not None:
        if not (isinstance(choices, list) and all(isinstance(c, str) for c in choices)):
            errs.append("choices: must be a list of strings")
        elif isinstance(label, str) and label not in choices:
            errs.append("label: must be one of choices")

    # Difficulty bounds if present
    diff = ann.get("difficulty")
    if diff is not None:
        if not isinstance(diff, int) or not (1 <= diff <= 5):
            errs.append("difficulty: must be integer in [1,5]")

    # Taxonomy/task identifiers (soft but useful)
    tax_ver = ann.get("taxonomy_version")
    if tax_ver is not None and not isinstance(tax_ver, str):
        errs.append("taxonomy_version: must be a string")
    task_id = _get(ann, ["task", "id"])
    if task_id is not None and not isinstance(task_id, str):
        errs.append("task.id: must be a string")
    task_path = _get(ann, ["task", "path"])
    if task_path is not None:
        if not (isinstance(task_path, list) and all(isinstance(x, str) for x in task_path)):
            errs.append("task.path: must be a list of strings")

    return errs

def build_validator(schema):
    if jsonschema is None:
        return None
    try:
        cls = jsonschema.validators.validator_for(schema)
        cls.check_schema(schema)
        return cls(schema)
    except Exception as ex:
        raise SystemExit(f"Invalid JSON Schema: {ex}")

def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate task annotations against JSON Schema plus logical constraints.")
    ap.add_argument("annotations", nargs="+", help="Path(s) to .json or .jsonl annotation files.")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="Path to JSON Schema.")
    ap.add_argument("--fail-fast", action="store_true", help="Stop at first error.")
    args = ap.parse_args(argv)

    schema_path = Path(args.schema)
    schema = load_json(schema_path)
    validator = build_validator(schema)

    total = 0
    bad = 0
    for p in [Path(x) for x in args.annotations]:
        if not p.exists():
            raise SystemExit(f"Missing annotation file: {p}")
        for line_no, ann in iter_annotations(p):
            total += 1
            errs = []
            errs += validate_with_schema(ann, validator)
            errs += validate_logical_constraints(ann)
            if errs:
                bad += 1
                for msg in errs:
                    eprint(f"{p}:{line_no}: {msg}")
                if args.fail_fast:
                    return 2
    if bad:
        eprint(f"Validation failed: {bad}/{total} annotations had errors.")
        return 2
    print(f"OK: validated {total} annotations.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
