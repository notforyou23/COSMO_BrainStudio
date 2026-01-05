from __future__ import annotations
from pathlib import Path
import csv, json, hashlib, datetime

ROOT = Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution")
FIXT = ROOT / "runtime" / "fixtures"
BUILD = ROOT / "runtime" / "outputs" / "_build"

def canon_id(study_id: str, table: str, row_key: str) -> str:
    raw = f"{study_id}|{table}|{row_key}".encode("utf-8")
    h = hashlib.sha1(raw).hexdigest()[:12]
    return f"{study_id}:{table}:{row_key}:{h}"

def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")

def write_demo_fixtures() -> dict[str, Path]:
    FIXT.mkdir(parents=True, exist_ok=True)
    study_id = "DEMO_STUDY_001"
    extraction_rows = [
        {"row_key": "R1", "outcome": "knowledge", "effect": "0.20"},
        {"row_key": "R2", "outcome": "behavior", "effect": "0.10"},
        {"row_key": "R3", "outcome": "attitude", "effect": "-0.05"},
    ]
    for r in extraction_rows:
        r["extraction_id"] = canon_id(study_id, "extraction", r["row_key"])
    extraction_path = FIXT / "demo_extraction.csv"
    with extraction_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["row_key", "extraction_id", "outcome", "effect"])
        w.writeheader()
        w.writerows(extraction_rows)

    taxonomy_path = FIXT / "demo_taxonomy.jsonl"
    good = {"annotation_id": canon_id(study_id, "taxonomy", "A1"), "extraction_id": extraction_rows[0]["extraction_id"], "labels": ["nudge", "default"]}
    bad_missing = {"annotation_id": canon_id(study_id, "taxonomy", "A2"), "extraction_id": canon_id(study_id, "extraction", "R99"), "labels": ["framing"]}
    with taxonomy_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(good, ensure_ascii=False) + "\n")
        f.write(json.dumps(bad_missing, ensure_ascii=False) + "\n")

    prereg = {
        "study_id": study_id,
        "registered_extraction_ids": [r["extraction_id"] for r in extraction_rows[:2]] + [canon_id(study_id, "extraction", "R3_WRONG")],
        "notes": "Includes one intentionally incorrect extraction_id to trigger mismatch detection."
    }
    prereg_path = FIXT / "demo_prereg.json"
    prereg_path.write_text(json.dumps(prereg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"extraction": extraction_path, "taxonomy": taxonomy_path, "prereg": prereg_path}

def load_extraction_ids(path: Path) -> set[str]:
    ids = set()
    with path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("extraction_id"):
                ids.add(row["extraction_id"].strip())
    return ids

def load_taxonomy_refs(path: Path) -> list[dict]:
    ann = []
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            obj["_line"] = ln
            ann.append(obj)
    return ann

def load_prereg_ids(path: Path) -> set[str]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return set(x.strip() for x in obj.get("registered_extraction_ids", []) if isinstance(x, str))

def check_mismatches(extraction_ids: set[str], taxonomy_ann: list[dict], prereg_ids: set[str]) -> dict:
    missing_for_taxonomy = []
    for a in taxonomy_ann:
        xid = (a.get("extraction_id") or "").strip()
        if xid and xid not in extraction_ids:
            missing_for_taxonomy.append({"line": a.get("_line"), "annotation_id": a.get("annotation_id"), "extraction_id": xid, "labels": a.get("labels", [])})
    missing_for_prereg = sorted([x for x in prereg_ids if x not in extraction_ids])
    return {
        "counts": {
            "extraction_ids": len(extraction_ids),
            "taxonomy_annotations": len(taxonomy_ann),
            "prereg_ids": len(prereg_ids),
            "taxonomy_bad_refs": len(missing_for_taxonomy),
            "prereg_bad_refs": len(missing_for_prereg),
        },
        "taxonomy_bad_refs": missing_for_taxonomy,
        "prereg_bad_refs": missing_for_prereg,
    }

def render_report(paths: dict[str, Path], findings: dict) -> str:
    c = findings["counts"]
    lines = []
    lines.append("ID LINKING MISMATCH REPORT")
    lines.append(f"Generated: {now_iso()}")
    lines.append("")
    lines.append("Inputs")
    lines.append(f"- extraction: {paths['extraction']}")
    lines.append(f"- taxonomy:   {paths['taxonomy']}")
    lines.append(f"- prereg:     {paths['prereg']}")
    lines.append("")
    lines.append("Summary")
    lines.append(f"- extraction_ids:       {c['extraction_ids']}")
    lines.append(f"- taxonomy_annotations: {c['taxonomy_annotations']}")
    lines.append(f"- prereg_ids:           {c['prereg_ids']}")
    lines.append(f"- taxonomy_bad_refs:    {c['taxonomy_bad_refs']}")
    lines.append(f"- prereg_bad_refs:      {c['prereg_bad_refs']}")
    lines.append("")
    if findings["taxonomy_bad_refs"]:
        lines.append("Taxonomy annotations referencing missing extraction IDs")
        for item in findings["taxonomy_bad_refs"]:
            lines.append(f"  - line {item['line']}: annotation_id={item.get('annotation_id')} extraction_id={item.get('extraction_id')} labels={item.get('labels')}")
        lines.append("")
    if findings["prereg_bad_refs"]:
        lines.append("Prereg registered_extraction_ids missing from extraction table")
        for xid in findings["prereg_bad_refs"]:
            lines.append(f"  - {xid}")
        lines.append("")
    if not findings["taxonomy_bad_refs"] and not findings["prereg_bad_refs"]:
        lines.append("No mismatches detected.")
        lines.append("")
    return "\n".join(lines)

def main() -> int:
    paths = write_demo_fixtures()
    extraction_ids = load_extraction_ids(paths["extraction"])
    taxonomy_ann = load_taxonomy_refs(paths["taxonomy"])
    prereg_ids = load_prereg_ids(paths["prereg"])
    findings = check_mismatches(extraction_ids, taxonomy_ann, prereg_ids)

    BUILD.mkdir(parents=True, exist_ok=True)
    report_path = BUILD / "id_mismatch_demo_report.txt"
    report_path.write_text(render_report(paths, findings), encoding="utf-8")

    findings_path = BUILD / "id_mismatch_demo_findings.json"
    findings_path.write_text(json.dumps(findings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"REPORT_WRITTEN:{report_path}")
    print(f"FINDINGS_WRITTEN:{findings_path}")
    return 2 if (findings["taxonomy_bad_refs"] or findings["prereg_bad_refs"]) else 0

if __name__ == "__main__":
    raise SystemExit(main())
