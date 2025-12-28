from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv, json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SAFE_SEP = ":"

def _norm_part(x: Any) -> str:
    s = "" if x is None else str(x).strip()
    return s.replace("\\", "\\\\").replace(SAFE_SEP, "_")

def build_id(namespace: str, *parts: Any) -> str:
    ns = _norm_part(namespace) or "id"
    ps = [_norm_part(p) for p in parts if _norm_part(p)]
    return SAFE_SEP.join([ns] + ps) if ps else ns

def guess_tab_dialect(path: Path) -> str:
    return "tsv" if path.suffix.lower() in {".tsv", ".tab"} else "csv"

def load_table_rows(path: Path) -> List[Dict[str, str]]:
    dialect = guess_tab_dialect(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t" if dialect == "tsv" else ",")
        return [{k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in (row or {}).items()} for row in reader]

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                raise ValueError(f"Invalid JSONL at {path}:{i}: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL record must be object at {path}:{i}")
            out.append(obj)
    return out

def load_prereg(path: Path) -> Any:
    suf = path.suffix.lower()
    if suf in {".json"}:
        return json.loads(path.read_text(encoding="utf-8"))
    if suf in {".csv", ".tsv", ".tab"}:
        return load_table_rows(path)
    raise ValueError(f"Unsupported prereg format: {path}")

def normalize_extractions(rows: Sequence[Dict[str, Any]], *, namespace: str = "ext",
                          id_fields: Sequence[str] = ("doc_id", "row_id")) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(rows):
        rr = dict(r)
        eid = rr.get("extraction_id") or rr.get("id")
        if not eid:
            parts = [rr.get(f) for f in id_fields if rr.get(f)]
            eid = build_id(namespace, *parts) if parts else build_id(namespace, i + 1)
        rr["extraction_id"] = str(eid)
        out.append(rr)
    return out

def normalize_annotations(recs: Sequence[Dict[str, Any]], *, id_key_candidates: Sequence[str] = ("extraction_id","target_id","row_id")) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for a in recs:
        aa = dict(a)
        for k in id_key_candidates:
            if aa.get(k):
                aa["extraction_id"] = str(aa.get(k))
                break
        out.append(aa)
    return out

def normalize_prereg(prereg: Any, *, namespace: str = "prereg") -> Dict[str, Any]:
    if isinstance(prereg, dict):
        obj = dict(prereg)
    else:
        obj = {"_records": prereg}
    obj.setdefault("prereg_id", build_id(namespace, obj.get("study_id") or obj.get("doc_id") or "default"))
    return obj

@dataclass
class Finding:
    kind: str
    where: str
    ref_id: str
    detail: str

def check_integrity(extractions: Sequence[Dict[str, Any]],
                    annotations: Sequence[Dict[str, Any]],
                    prereg: Optional[Dict[str, Any]] = None) -> List[Finding]:
    findings: List[Finding] = []
    ext_ids: List[str] = [str(r.get("extraction_id","")) for r in extractions]
    ext_set = {x for x in ext_ids if x}
    for eid in [x for x in ext_ids if x]:
        if ext_ids.count(eid) > 1:
            findings.append(Finding("DUPLICATE_EXTRACTION_ID", "extraction", eid, "Duplicate extraction_id in extraction rows"))
            break

    for i, a in enumerate(annotations):
        rid = str(a.get("extraction_id") or "")
        if not rid:
            findings.append(Finding("MISSING_ANNOTATION_REF", f"annotation[{i}]", "", "Annotation missing extraction_id/target_id/row_id"))
        elif rid not in ext_set:
            findings.append(Finding("UNKNOWN_EXTRACTION_REF", f"annotation[{i}]", rid, "Annotation references non-existent extraction_id"))

    if prereg is not None:
        pid = str(prereg.get("prereg_id") or "")
        if not pid:
            findings.append(Finding("MISSING_PREREG_ID", "prereg", "", "Prereg object missing prereg_id"))
        links = prereg.get("links") or prereg.get("extraction_ids") or []
        if isinstance(links, str):
            links = [links]
        if isinstance(links, dict):
            links = list(links.values())
        if isinstance(links, list):
            for j, rid in enumerate([str(x) for x in links if str(x)]):
                if rid not in ext_set:
                    findings.append(Finding("UNKNOWN_EXTRACTION_REF", f"prereg.link[{j}]", rid, "Prereg references non-existent extraction_id"))
    return findings

def findings_to_dicts(findings: Sequence[Finding]) -> List[Dict[str, str]]:
    return [{"kind": f.kind, "where": f.where, "ref_id": f.ref_id, "detail": f.detail} for f in findings]

def render_report(findings: Sequence[Finding], *, title: str = "ID Linkage Integrity Report") -> str:
    lines = [title, "=" * len(title), f"Findings: {len(findings)}", ""]
    if not findings:
        lines.append("No mismatches detected.")
        return "\n".join(lines).rstrip() + "\n"
    by_kind: Dict[str, List[Finding]] = {}
    for f in findings:
        by_kind.setdefault(f.kind, []).append(f)
    for kind in sorted(by_kind):
        lines += [f"[{kind}] ({len(by_kind[kind])})"]
        for f in by_kind[kind]:
            rid = f.ref_id if f.ref_id else "<missing>"
            lines.append(f"- {f.where}: {rid} — {f.detail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def load_and_check(extraction_path: Path, taxonomy_jsonl_path: Path, prereg_path: Optional[Path] = None) -> Tuple[List[Finding], Dict[str, Any]]:
    ex = normalize_extractions(load_table_rows(extraction_path))
    ann = normalize_annotations(load_jsonl(taxonomy_jsonl_path))
    prereg_obj = normalize_prereg(load_prereg(prereg_path)) if prereg_path else None
    findings = check_integrity(ex, ann, prereg_obj)
    bundle = {"extractions": ex, "annotations": ann, "prereg": prereg_obj, "findings": findings_to_dicts(findings)}
    return findings, bundle
