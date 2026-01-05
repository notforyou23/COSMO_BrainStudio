from __future__ import annotations
import argparse, csv, json, re, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

STUDY_ID_RE = re.compile(r"^STUDY-\d{4}$", re.IGNORECASE)
EFFECT_ID_RE = re.compile(r"^EFFECT-\d{4}$", re.IGNORECASE)
_ID_KEYS = ("StudyID", "EffectID")

def norm_id(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    return v.upper()

def _get_ci(d: Dict[str, object], key: str) -> Optional[object]:
    for k, v in d.items():
        if str(k).strip().lower() == key.lower():
            return v
    return None

@dataclass(frozen=True)
class Rec:
    source: str
    path: str
    where: str
    study_id: Optional[str]
    effect_id: Optional[str]

def _extract_ids_from_mapping(m: Dict[str, object]) -> Tuple[Optional[str], Optional[str]]:
    s = norm_id(_get_ci(m, "StudyID"))
    e = norm_id(_get_ci(m, "EffectID"))
    return s, e

def load_csv(path: Path) -> List[Rec]:
    out: List[Rec] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # header is line 1
            s, e = _extract_ids_from_mapping(row)
            out.append(Rec("csv", str(path), f"line {i}", s, e))
    return out

def load_jsonl(path: Path) -> List[Rec]:
    out: List[Rec] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                out.append(Rec("jsonl", str(path), f"line {i}", None, None))
                continue
            if isinstance(obj, dict):
                s, e = _extract_ids_from_mapping(obj)
            else:
                s, e = None, None
            out.append(Rec("jsonl", str(path), f"line {i}", s, e))
    return out

def load_prereg(path: Path) -> List[Rec]:
    txt = path.read_text(encoding="utf-8", errors="replace")
    s = e = None
    for line in txt.splitlines():
        m = re.match(r"^\s*(StudyID|EffectID)\s*[:=]\s*(.+?)\s*$", line, re.IGNORECASE)
        if not m:
            continue
        k = m.group(1).lower()
        v = norm_id(m.group(2))
        if k == "studyid":
            s = v
        elif k == "effectid":
            e = v
    if (s is None or e is None) and txt.lstrip().startswith("{"):
        try:
            obj = json.loads(txt)
            if isinstance(obj, dict):
                s2, e2 = _extract_ids_from_mapping(obj)
                s = s or s2
                e = e or e2
        except Exception:
            pass
    return [Rec("prereg", str(path), "document", s, e)]
def _is_valid(study_id: Optional[str], effect_id: Optional[str]) -> Tuple[bool, bool]:
    vs = bool(study_id and STUDY_ID_RE.match(study_id))
    ve = bool(effect_id and EFFECT_ID_RE.match(effect_id))
    return vs, ve

def check(recs: List[Rec], require_all_sources: bool = True) -> Dict[str, object]:
    issues: List[Dict[str, str]] = []
    sources = sorted({r.source for r in recs})
    by_source: Dict[str, List[Rec]] = {s: [] for s in sources}
    for r in recs:
        by_source[r.source].append(r)

    for r in recs:
        if r.study_id is None:
            issues.append({"type": "missing", "field": "StudyID", "source": r.source, "path": r.path, "where": r.where,
                           "message": "Missing StudyID; add StudyID column/field with format STUDY-0001."})
        if r.effect_id is None:
            issues.append({"type": "missing", "field": "EffectID", "source": r.source, "path": r.path, "where": r.where,
                           "message": "Missing EffectID; add EffectID column/field with format EFFECT-0001."})
        vs, ve = _is_valid(r.study_id, r.effect_id)
        if r.study_id is not None and not vs:
            issues.append({"type": "invalid", "field": "StudyID", "source": r.source, "path": r.path, "where": r.where,
                           "message": f"Invalid StudyID='{r.study_id}'; expected STUDY-0001 style."})
        if r.effect_id is not None and not ve:
            issues.append({"type": "invalid", "field": "EffectID", "source": r.source, "path": r.path, "where": r.where,
                           "message": f"Invalid EffectID='{r.effect_id}'; expected EFFECT-0001 style."})

    # duplicates within each source
    for src, lst in by_source.items():
        seen_eff: Dict[str, Rec] = {}
        seen_pair: Dict[Tuple[str, str], Rec] = {}
        for r in lst:
            if r.effect_id:
                if r.effect_id in seen_eff:
                    prev = seen_eff[r.effect_id]
                    issues.append({"type": "duplicate", "field": "EffectID", "source": src, "path": r.path, "where": r.where,
                                   "message": f"Duplicate EffectID '{r.effect_id}' also in {prev.where}; keep unique per effect."})
                else:
                    seen_eff[r.effect_id] = r
            if r.study_id and r.effect_id:
                k = (r.study_id, r.effect_id)
                if k in seen_pair:
                    prev = seen_pair[k]
                    issues.append({"type": "duplicate", "field": "StudyID+EffectID", "source": src, "path": r.path, "where": r.where,
                                   "message": f"Duplicate pair ({r.study_id},{r.effect_id}) also in {prev.where}; remove duplicates."})
                else:
                    seen_pair[k] = r

    # mismatches across sources: same EffectID maps to multiple StudyIDs
    eff_to_studies: Dict[str, Dict[str, List[Rec]]] = {}
    for r in recs:
        if not r.effect_id or not r.study_id:
            continue
        eff_to_studies.setdefault(r.effect_id, {}).setdefault(r.study_id, []).append(r)
    for eff, by_study in eff_to_studies.items():
        if len(by_study) > 1:
            parts = []
            for st, rs in sorted(by_study.items()):
                loc = "; ".join(sorted({f"{Path(x.path).name}:{x.where}" for x in rs}))
                parts.append(f"{st} @ {loc}")
            issues.append({"type": "mismatch", "field": "StudyID", "source": "cross-file", "path": "-", "where": "-",
                           "message": f"EffectID '{eff}' is linked to multiple StudyIDs: " + " | ".join(parts) + ". Align StudyID across all files."})

    # missing effects in sources (only if multiple sources provided)
    if require_all_sources and len(sources) > 1:
        eff_by_src: Dict[str, set] = {s: set() for s in sources}
        for r in recs:
            if r.effect_id:
                eff_by_src[r.source].add(r.effect_id)
        all_eff = set().union(*eff_by_src.values()) if eff_by_src else set()
        for eff in sorted(all_eff):
            missing_in = [s for s in sources if eff not in eff_by_src[s]]
            if missing_in:
                issues.append({"type": "missing_in_source", "field": "EffectID", "source": "cross-file", "path": "-", "where": "-",
                               "message": f"EffectID '{eff}' missing in sources: {', '.join(missing_in)}. Add matching records or remove the effect from other files."})

    ok = not issues
    return {"ok": ok, "sources": sources, "counts": {s: len(by_source[s]) for s in sources}, "issues": issues}

def _render_human(result: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("ID CHECK RESULT: " + ("OK" if result["ok"] else "FAIL"))
    lines.append("Sources: " + ", ".join(result["sources"]))
    lines.append("Record counts: " + ", ".join(f"{k}={v}" for k, v in result["counts"].items()))
    issues = result["issues"]
    if not issues:
        return "\n".join(lines) + "\n"
    lines.append(f"Issues ({len(issues)}):")
    for it in issues:
        lines.append(f"- [{it['type']}] {it['field']} {it['source']} {Path(it['path']).name}:{it['where']} :: {it['message']}")
    return "\n".join(lines) + "\n"

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="ids-check", description="Check StudyID/EffectID integrity across CSV, JSONL, and prereg templates.")
    p.add_argument("--csv", dest="csv_path", type=str, help="Path to CSV file with StudyID/EffectID columns.")
    p.add_argument("--jsonl", dest="jsonl_path", type=str, help="Path to JSONL file with StudyID/EffectID fields.")
    p.add_argument("--prereg", dest="prereg_path", type=str, help="Path to prereg template containing StudyID/EffectID.")
    p.add_argument("--no-require-all-sources", action="store_true", help="Do not require each EffectID to appear in every provided source.")
    p.add_argument("--json", dest="json_out", action="store_true", help="Emit machine-readable JSON to stdout.")
    args = p.parse_args(argv)

    recs: List[Rec] = []
    if args.csv_path:
        recs += load_csv(Path(args.csv_path))
    if args.jsonl_path:
        recs += load_jsonl(Path(args.jsonl_path))
    if args.prereg_path:
        recs += load_prereg(Path(args.prereg_path))
    if not recs:
        sys.stderr.write("No input provided; pass --csv and/or --jsonl and/or --prereg.\n")
        return 2

    result = check(recs, require_all_sources=not args.no_require_all_sources)
    if args.json_out:
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(_render_human(result))
    return 0 if result["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
