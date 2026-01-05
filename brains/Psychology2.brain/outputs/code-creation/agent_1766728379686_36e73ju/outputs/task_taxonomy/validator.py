#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REQUIRED = [
    "record_id","task_type","domain","input_modality","output_modality",
    "language","difficulty","prompt","expected_output","output_format"
]

ALLOWED = {
    "task_type": {"generation","transformation","classification","extraction","retrieval","reasoning","planning","coding","qa","summarization"},
    "domain": {"general","science","math","medicine","law","finance","software","education","creative","support","business","data"},
    "input_modality": {"text","image","audio","video","table","code","mixed"},
    "output_modality": {"text","image","audio","video","table","code","mixed"},
    "language": {"en","es","fr","de","pt","it","nl","sv","no","da","fi","pl","cs","tr","ru","uk","ar","he","hi","bn","ur","id","ms","th","vi","zh","ja","ko","multi"},
    "difficulty": {"easy","medium","hard"},
    "output_format": {"free_text","json","csv","xml","yaml","label","labels","code","number","boolean"}
}

OPTIONAL_ENUMS = {
    "sensitivity": {"none","low","medium","high"},
    "contains_pii": {True, False},
    "contains_secrets": {True, False},
}

def _is_blank(v: Any) -> bool:
    if v is None: return True
    if isinstance(v, str) and v.strip() == "": return True
    if isinstance(v, list) and len(v) == 0: return True
    if isinstance(v, dict) and len(v) == 0: return True
    return False

def _as_bool(v: Any) -> Any:
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)) and v in (0, 1): return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true","t","yes","y","1"): return True
        if s in ("false","f","no","n","0",""): return False
    return v

def load_records(path: Path) -> List[Dict[str, Any]]:
    suf = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suf == ".csv":
        rows = []
        for r in csv.DictReader(text.splitlines()):
            d = dict(r)
            for k in ("contains_pii","contains_secrets"):
                if k in d: d[k] = _as_bool(d[k])
            rows.append(d)
        return rows
    if suf == ".jsonl":
        out = []
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line: continue
            try:
                obj = json.loads(line)
            except Exception as e:
                raise ValueError(f"{path.name}:{i}: invalid JSONL line: {e}")
            if not isinstance(obj, dict):
                raise ValueError(f"{path.name}:{i}: expected object per line")
            out.append(obj)
        return out
    if suf == ".json":
        obj = json.loads(text)
        if isinstance(obj, dict): return [obj]
        if isinstance(obj, list):
            if not all(isinstance(x, dict) for x in obj):
                raise ValueError(f"{path.name}: JSON array must contain objects")
            return obj
        raise ValueError(f"{path.name}: expected JSON object or array")
    raise ValueError(f"Unsupported input type: {path} (use .json/.jsonl/.csv)")

def validate_record(rec: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    for f in REQUIRED:
        if f not in rec or _is_blank(rec.get(f)):
            errs.append(f"missing_required:{f}")
    for f, allowed in ALLOWED.items():
        if f in rec and not _is_blank(rec.get(f)):
            v = rec.get(f)
            if isinstance(v, str): v = v.strip()
            if v not in allowed:
                errs.append(f"invalid_value:{f}={v!r}")
    for f, allowed in OPTIONAL_ENUMS.items():
        if f in rec and not _is_blank(rec.get(f)):
            v = _as_bool(rec.get(f))
            if v not in allowed:
                errs.append(f"invalid_value:{f}={rec.get(f)!r}")
            rec[f] = v
    # Cross-field constraints
    task_type = (rec.get("task_type") or "").strip() if isinstance(rec.get("task_type"), str) else rec.get("task_type")
    out_fmt = (rec.get("output_format") or "").strip() if isinstance(rec.get("output_format"), str) else rec.get("output_format")
    in_mod = (rec.get("input_modality") or "").strip() if isinstance(rec.get("input_modality"), str) else rec.get("input_modality")
    out_mod = (rec.get("output_modality") or "").strip() if isinstance(rec.get("output_modality"), str) else rec.get("output_modality")
    if task_type == "classification" and out_fmt not in {"label","labels","json"}:
        errs.append("cross:classification_requires_output_format_label_labels_or_json")
    if task_type == "coding" and out_mod not in {"code","mixed"}:
        errs.append("cross:coding_requires_output_modality_code_or_mixed")
    if out_fmt == "code" and _is_blank(rec.get("programming_language")):
        errs.append("cross:output_format_code_requires_programming_language")
    if _as_bool(rec.get("contains_pii")) is True:
        sens = rec.get("sensitivity")
        if sens is None: errs.append("cross:contains_pii_requires_sensitivity")
        elif sens not in {"medium","high"}: errs.append("cross:contains_pii_requires_sensitivity_medium_or_high")
    if in_mod in {"image","audio","video","table","code"} and _is_blank(rec.get("input_description")) and _is_blank(rec.get("input_uri")):
        errs.append("cross:non_text_input_requires_input_description_or_input_uri")
    if out_fmt in {"json","csv","xml","yaml"} and _is_blank(rec.get("output_schema")):
        errs.append("cross:structured_output_requires_output_schema")
    return errs

def format_errors(path: Path, idx: int, rec: Dict[str, Any], errs: List[str]) -> str:
    rid = rec.get("record_id", "")
    rid = rid if isinstance(rid, str) else str(rid)
    loc = f"{path.name}:{idx}"
    if rid.strip(): loc += f" record_id={rid.strip()}"
    return loc + " -> " + "; ".join(errs)

def validate_file(path: Path, fail_fast: bool=False) -> Tuple[int, List[str]]:
    records = load_records(path)
    errors: List[str] = []
    bad = 0
    for i, rec in enumerate(records, 1):
        if not isinstance(rec, dict):
            bad += 1
            errors.append(f"{path.name}:{i} -> not_an_object")
            if fail_fast: break
            continue
        errs = validate_record(rec)
        if errs:
            bad += 1
            errors.append(format_errors(path, i, rec, errs))
            if fail_fast: break
    return bad, errors

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Validate task taxonomy records (.json/.jsonl/.csv).")
    ap.add_argument("inputs", nargs="+", help="Input file(s): .json/.jsonl/.csv")
    ap.add_argument("--fail-fast", action="store_true", help="Stop on first error per file.")
    ap.add_argument("--quiet", action="store_true", help="Only print summary; still exits nonzero on errors.")
    args = ap.parse_args(argv)

    total_bad = 0
    total = 0
    all_errors: List[str] = []
    for p in [Path(x) for x in args.inputs]:
        bad, errs = validate_file(p, fail_fast=args.fail_fast)
        total_bad += bad
        total += len(load_records(p))
        all_errors.extend(errs)
    if (not args.quiet) and all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
    if total_bad:
        print(f"INVALID: {total_bad} of {total} record(s) failed validation", file=sys.stderr)
        return 1
    print(f"VALID: {total} record(s) passed validation")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
