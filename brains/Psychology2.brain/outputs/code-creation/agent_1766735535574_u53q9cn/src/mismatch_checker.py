from __future__ import annotations
import argparse, csv, json, re, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

Pair = Tuple[str, str]

def _load_id_convention():
    try:
        from . import id_convention as ic  # type: ignore
        return {
            "study_pat": getattr(ic, "STUDY_ID_PATTERN", None),
            "effect_pat": getattr(ic, "EFFECT_ID_PATTERN", None),
            "validate_study": getattr(ic, "validate_study_id", None),
            "validate_effect": getattr(ic, "validate_effect_id", None),
            "validate_pair": getattr(ic, "validate_pair", None),
        }
    except Exception:
        return {"study_pat": None, "effect_pat": None, "validate_study": None, "validate_effect": None, "validate_pair": None}

_IC = _load_id_convention()
_STUDY_RE = re.compile(_IC["study_pat"] or r"^study-[a-z0-9]+(?:-[a-z0-9]+)*$")
_EFFECT_RE = re.compile(_IC["effect_pat"] or r"^eff-[a-z0-9]+(?:-[a-z0-9]+)*$")

def _is_valid_study(study_id: str) -> bool:
    f = _IC.get("validate_study")
    if callable(f):
        try: return bool(f(study_id))
        except Exception: return False
    return bool(_STUDY_RE.match(study_id or ""))

def _is_valid_effect(effect_id: str) -> bool:
    f = _IC.get("validate_effect")
    if callable(f):
        try: return bool(f(effect_id))
        except Exception: return False
    return bool(_EFFECT_RE.match(effect_id or ""))

def _is_valid_pair(study_id: str, effect_id: str) -> bool:
    f = _IC.get("validate_pair")
    if callable(f):
        try: return bool(f(study_id, effect_id))
        except Exception: return False
    return _is_valid_study(study_id) and _is_valid_effect(effect_id)

@dataclass
class RecordIssue:
    kind: str
    file: str
    loc: str
    msg: str

def _read_csv_pairs(path: Path) -> Tuple[Set[Pair], List[RecordIssue]]:
    issues: List[RecordIssue] = []
    pairs: Set[Pair] = set()
    seen: Dict[Pair, int] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        cols = set(r.fieldnames or [])
        need = {"study_id", "effect_id"}
        missing = sorted(need - cols)
        if missing:
            issues.append(RecordIssue("schema", str(path), "header", f"Missing required columns: {', '.join(missing)}. Found: {', '.join(sorted(cols)) or '(none)'}"))
            return set(), issues
        for i, row in enumerate(r, start=2):
            sid = (row.get("study_id") or "").strip()
            eid = (row.get("effect_id") or "").strip()
            if not sid or not eid:
                issues.append(RecordIssue("format", str(path), f"row {i}", f"Blank study_id/effect_id (study_id={sid!r}, effect_id={eid!r})."))
                continue
            if not _is_valid_pair(sid, eid):
                issues.append(RecordIssue("format", str(path), f"row {i}", f"Invalid IDs under convention (study_id={sid!r}, effect_id={eid!r})."))
                continue
            p = (sid, eid)
            if p in seen:
                issues.append(RecordIssue("dup", str(path), f"row {i}", f"Duplicate pair {p} (first seen at row {seen[p]})."))
            else:
                seen[p] = i
                pairs.add(p)
    return pairs, issues

def _read_jsonl_pairs(path: Path) -> Tuple[Set[Pair], List[RecordIssue]]:
    issues: List[RecordIssue] = []
    pairs: Set[Pair] = set()
    seen: Dict[Pair, int] = {}
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except Exception as e:
                issues.append(RecordIssue("schema", str(path), f"line {i}", f"Invalid JSON: {e}"))
                continue
            sid = (obj.get("study_id") or "").strip() if isinstance(obj, dict) else ""
            eid = (obj.get("effect_id") or "").strip() if isinstance(obj, dict) else ""
            if not sid or not eid:
                issues.append(RecordIssue("schema", str(path), f"line {i}", "Missing required fields 'study_id' and/or 'effect_id'."))
                continue
            if not _is_valid_pair(sid, eid):
                issues.append(RecordIssue("format", str(path), f"line {i}", f"Invalid IDs under convention (study_id={sid!r}, effect_id={eid!r})."))
                continue
            p = (sid, eid)
            if p in seen:
                issues.append(RecordIssue("dup", str(path), f"line {i}", f"Duplicate pair {p} (first seen at line {seen[p]})."))
            else:
                seen[p] = i
                pairs.add(p)
    return pairs, issues

def _emit_issues(issues: Iterable[RecordIssue]) -> None:
    for it in issues:
        sys.stderr.write(f"[{it.kind.upper()}] {it.file}:{it.loc}: {it.msg}\n")

def _exit_code(issues: List[RecordIssue], csv_only: Set[Pair], jsonl_only: Set[Pair]) -> int:
    if any(i.kind == "schema" for i in issues): return 2
    if any(i.kind == "format" for i in issues): return 2
    if any(i.kind == "dup" for i in issues): return 3
    if csv_only: return 4
    if jsonl_only: return 5
    return 0

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="mismatch_checker", description="Validate ID convention and cross-file (study_id,effect_id) alignment between CSV and JSONL.")
    ap.add_argument("--csv", required=True, help="Path to effects.csv (must include study_id and effect_id columns).")
    ap.add_argument("--jsonl", required=True, help="Path to effects.jsonl (each object must include study_id and effect_id).")
    ap.add_argument("--max-list", type=int, default=25, help="Max mismatching pairs to list per category.")
    args = ap.parse_args(argv)

    csv_path, jsonl_path = Path(args.csv), Path(args.jsonl)
    issues: List[RecordIssue] = []
    if not csv_path.exists():
        issues.append(RecordIssue("schema", str(csv_path), "path", "CSV file not found."))
    if not jsonl_path.exists():
        issues.append(RecordIssue("schema", str(jsonl_path), "path", "JSONL file not found."))
    if issues:
        _emit_issues(issues)
        return 2

    csv_pairs, csv_issues = _read_csv_pairs(csv_path)
    jsonl_pairs, jsonl_issues = _read_jsonl_pairs(jsonl_path)
    issues.extend(csv_issues); issues.extend(jsonl_issues)

    csv_only = csv_pairs - jsonl_pairs
    jsonl_only = jsonl_pairs - csv_pairs

    _emit_issues(issues)

    def _list_pairs(label: str, s: Set[Pair]) -> None:
        if not s: return
        sys.stderr.write(f"[MISMATCH] {label}: {len(s)} pair(s)\n")
        for p in sorted(s)[: max(0, int(args.max_list))]:
            sys.stderr.write(f"  - study_id={p[0]!r} effect_id={p[1]!r}\n")
        if len(s) > args.max_list:
            sys.stderr.write(f"  ... and {len(s) - args.max_list} more\n")

    _list_pairs("Present in CSV but missing in JSONL", csv_only)
    _list_pairs("Present in JSONL but missing in CSV", jsonl_only)

    code = _exit_code(issues, csv_only, jsonl_only)
    if code == 0:
        sys.stdout.write("OK: CSV and JSONL pairs match and IDs conform to the convention.\n")
    else:
        sys.stderr.write(f"FAILED: exit_code={code}. Fix schema/format/duplicates, then resolve mismatching pairs.\n")
    return code

if __name__ == "__main__":
    raise SystemExit(main())
