import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
@dataclass(frozen=True)
class IDSchema:
    study_re: re.Pattern
    effect_re: re.Pattern
    taxon_re: re.Pattern

    def check(self, kind: str, value: str) -> bool:
        v = (value or "").strip()
        if kind == "study":
            return bool(self.study_re.fullmatch(v))
        if kind == "effect":
            return bool(self.effect_re.fullmatch(v))
        if kind == "taxon":
            return bool(self.taxon_re.fullmatch(v))
        raise ValueError(f"unknown id kind: {kind}")

def canonical_schema() -> IDSchema:
    # Canonical ID formats (example schema):
    # - study_id: STU-0001
    # - effect_id: EFF-0001
    # - taxonomy_id: TAX-001
    return IDSchema(
        study_re=re.compile(r"STU-[0-9]{4}$"),
        effect_re=re.compile(r"EFF-[0-9]{4}$"),
        taxon_re=re.compile(r"TAX-[0-9]{3}$"),
    )
def write_demo_dataset(base_dir: Path) -> Tuple[Path, Path, Path]:
    data_dir = base_dir / "data" / "demo_generated"
    data_dir.mkdir(parents=True, exist_ok=True)

    extraction_csv = data_dir / "extraction.csv"
    taxonomy_jsonl = data_dir / "taxonomy.jsonl"
    prereg_json = data_dir / "prereg.json"

    # Intentionally failing dataset:
    # 1) malformed study_id (underscore)
    # 2) duplicate effect_id
    # 3) taxonomy_id referenced but missing from taxonomy file
    extraction_csv.write_text(
        "study_id,effect_id,taxonomy_id,estimate
"
        "STU-0001,EFF-0001,TAX-001,0.12
"
        "STU_0002,EFF-0001,TAX-999,0.34
",
        encoding="utf-8",
    )

    # Taxonomy intentionally does not include TAX-999.
    taxonomy_jsonl.write_text(
        json.dumps({"taxonomy_id": "TAX-001", "label": "Default"}) + "
" +
        json.dumps({"taxonomy_id": "TAX-002", "label": "Other", "parent_id": "TAX-001"}) + "
",
        encoding="utf-8",
    )

    # Prereg intentionally contains an extra, and also the correct STU-0002 that won't match extraction due to malformed ID there.
    prereg_json.write_text(
        json.dumps({"study_ids": ["STU-0001", "STU-0002", "STU-9999"]}, indent=2) + "
",
        encoding="utf-8",
    )

    return extraction_csv, taxonomy_jsonl, prereg_json
def load_extraction_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]

def load_taxonomy_jsonl(path: Path) -> List[Dict[str, str]]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            try:
                items.append(json.loads(s))
            except json.JSONDecodeError as e:
                raise ValueError(f"invalid JSONL at {path}:{i}: {e}") from e
    return items

def load_prereg(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
def check_ids(extraction_rows: List[Dict[str, str]],
              taxonomy_items: List[Dict[str, str]],
              prereg: Dict[str, object],
              schema: IDSchema) -> List[str]:
    errors: List[str] = []

    study_ids = [r.get("study_id", "") for r in extraction_rows]
    effect_ids = [r.get("effect_id", "") for r in extraction_rows]
    taxon_refs = [r.get("taxonomy_id", "") for r in extraction_rows]

    # Schema conformance
    for idx, sid in enumerate(study_ids, 1):
        if not schema.check("study", sid):
            errors.append(f"extraction.csv row {idx}: invalid study_id '{sid}' (expected STU-0001 format)")
    for idx, eid in enumerate(effect_ids, 1):
        if not schema.check("effect", eid):
            errors.append(f"extraction.csv row {idx}: invalid effect_id '{eid}' (expected EFF-0001 format)")
    for idx, tid in enumerate(taxon_refs, 1):
        if tid and not schema.check("taxon", tid):
            errors.append(f"extraction.csv row {idx}: invalid taxonomy_id '{tid}' (expected TAX-001 format)")

    taxon_ids = []
    for i, it in enumerate(taxonomy_items, 1):
        tid = (it.get("taxonomy_id") or "").strip()
        if not tid:
            errors.append(f"taxonomy.jsonl line {i}: missing taxonomy_id")
            continue
        if not schema.check("taxon", tid):
            errors.append(f"taxonomy.jsonl line {i}: invalid taxonomy_id '{tid}' (expected TAX-001 format)")
        taxon_ids.append(tid)
        pid = (it.get("parent_id") or "").strip()
        if pid and not schema.check("taxon", pid):
            errors.append(f"taxonomy.jsonl line {i}: invalid parent_id '{pid}' (expected TAX-001 format)")

    # Uniqueness constraints
    seen = set()
    for idx, eid in enumerate(effect_ids, 1):
        if eid in seen:
            errors.append(f"extraction.csv row {idx}: duplicate effect_id '{eid}' (must be unique)")
        seen.add(eid)

    # Cross-file referential integrity: extraction taxonomy_id must exist in taxonomy.
    taxon_set = set(taxon_ids)
    for idx, tid in enumerate(taxon_refs, 1):
        if tid and tid not in taxon_set:
            errors.append(f"extraction.csv row {idx}: taxonomy_id '{tid}' not found in taxonomy.jsonl")

    # Prereg checks
    prereg_studies = prereg.get("study_ids")
    if not isinstance(prereg_studies, list) or not all(isinstance(x, str) for x in prereg_studies):
        errors.append("prereg.json: 'study_ids' must be a list of strings")
        prereg_studies = []
    else:
        for sid in prereg_studies:
            if not schema.check("study", sid):
                errors.append(f"prereg.json: invalid study_id '{sid}' (expected STU-0001 format)")

    extraction_study_set = set(study_ids)
    prereg_study_set = set(prereg_studies)

    # Prereg should not reference studies absent from extraction.
    for sid in sorted(prereg_study_set - extraction_study_set):
        errors.append(f"prereg.json: study_id '{sid}' not present in extraction.csv")

    # Extraction should not contain studies absent from prereg (common integrity requirement).
    for sid in sorted(extraction_study_set - prereg_study_set):
        errors.append(f"extraction.csv: study_id '{sid}' not present in prereg.json")

    return errors
def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description="Demo: ID schema + mismatch checker (intentional failure).")
    p.add_argument("--base-dir", default=str(Path(__file__).resolve().parents[1]),
                   help="Project base dir where demo data will be written (default: repo root).")
    p.add_argument("--no-write", action="store_true", help="Do not write demo dataset; expect files already exist.")
    args = p.parse_args(argv)

    base_dir = Path(args.base_dir).resolve()
    schema = canonical_schema()

    if args.no_write:
        data_dir = base_dir / "data" / "demo_generated"
        extraction_csv = data_dir / "extraction.csv"
        taxonomy_jsonl = data_dir / "taxonomy.jsonl"
        prereg_json = data_dir / "prereg.json"
    else:
        extraction_csv, taxonomy_jsonl, prereg_json = write_demo_dataset(base_dir)

    rows = load_extraction_csv(extraction_csv)
    tax = load_taxonomy_jsonl(taxonomy_jsonl)
    prereg = load_prereg(prereg_json)

    errors = check_ids(rows, tax, prereg, schema)
    if errors:
        print("ID_MISMATCH_CHECK_FAILED")
        for e in errors:
            print(" - " + e)
        return 2

    print("ID_MISMATCH_CHECK_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
