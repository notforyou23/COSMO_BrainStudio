from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv, json, re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ID_SCHEMAS = {
    "study_id": {"re": re.compile(r"^STU\d{4}$"), "normalize": lambda s: s.strip().upper()},
    "doc_id": {"re": re.compile(r"^DOC-[A-Z0-9]{6}$"), "normalize": lambda s: s.strip().upper()},
    "taxon_id": {"re": re.compile(r"^TAX:\d{3}$"), "normalize": lambda s: s.strip().upper()},
    "prereg_id": {"re": re.compile(r"^PRG-\d{5}$"), "normalize": lambda s: s.strip().upper()},
}

@dataclass(frozen=True)
class Issue:
    code: str
    where: str
    message: str
    value: Optional[str] = None

def _norm(field: str, v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = str(v)
    if s.strip() == "":
        return None
    return ID_SCHEMAS[field]["normalize"](s)

def _schema_ok(field: str, v: Optional[str]) -> bool:
    if v is None:
        return True
    return bool(ID_SCHEMAS[field]["re"].match(v))

def read_extraction_csv(path: Path) -> List[Dict[str, Optional[str]]]:
    rows: List[Dict[str, Optional[str]]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f)
        for i, r in enumerate(rdr, start=2):
            rows.append({
                "_row": i,
                "study_id": _norm("study_id", r.get("study_id")),
                "doc_id": _norm("doc_id", r.get("doc_id")),
                "taxon_id": _norm("taxon_id", r.get("taxon_id")),
                "prereg_id": _norm("prereg_id", r.get("prereg_id")),
            })
    return rows

def read_taxonomy_jsonl(path: Path) -> List[Dict[str, Optional[str]]]:
    out: List[Dict[str, Optional[str]]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out.append({"_line": i, "taxon_id": _norm("taxon_id", obj.get("taxon_id")), "label": obj.get("label")})
    return out

def read_prereg(path: Path) -> List[Dict[str, Optional[str]]]:
    if path.suffix.lower() == ".json":
        obj = json.loads(path.read_text(encoding="utf-8"))
        items = obj.get("items", obj if isinstance(obj, list) else [])
        return [{"_idx": i, "prereg_id": _norm("prereg_id", it.get("prereg_id")), "study_id": _norm("study_id", it.get("study_id"))} for i, it in enumerate(items)]
    if path.suffix.lower() == ".csv":
        out: List[Dict[str, Optional[str]]] = []
        with path.open("r", encoding="utf-8", newline="") as f:
            rdr = csv.DictReader(f)
            for i, r in enumerate(rdr, start=2):
                out.append({"_row": i, "prereg_id": _norm("prereg_id", r.get("prereg_id")), "study_id": _norm("study_id", r.get("study_id"))})
        return out
    raise ValueError(f"Unsupported prereg format: {path}")

def _dupes(values: Iterable[Tuple[str, str]]) -> Dict[str, List[str]]:
    seen: Dict[str, List[str]] = {}
    for where, v in values:
        if v is None:
            continue
        seen.setdefault(v, []).append(where)
    return {k: w for k, w in seen.items() if len(w) > 1}

def check_ids(extraction_rows: Sequence[Dict[str, Optional[str]]],
              taxonomy_rows: Sequence[Dict[str, Optional[str]]],
              prereg_rows: Sequence[Dict[str, Optional[str]]]) -> List[Issue]:
    issues: List[Issue] = []

    for r in extraction_rows:
        where = f"extraction.csv:row{r.get('_row')}"
        for fld in ("study_id", "doc_id", "taxon_id", "prereg_id"):
            v = r.get(fld)
            if v is not None and not _schema_ok(fld, v):
                issues.append(Issue("SCHEMA_VIOLATION", where, f"{fld} does not conform to {ID_SCHEMAS[fld]['re'].pattern}", v))

    for r in taxonomy_rows:
        where = f"taxonomy.jsonl:line{r.get('_line')}"
        v = r.get("taxon_id")
        if v is None:
            issues.append(Issue("MISSING_REQUIRED", where, "taxon_id is required", None))
        elif not _schema_ok("taxon_id", v):
            issues.append(Issue("SCHEMA_VIOLATION", where, f"taxon_id does not conform to {ID_SCHEMAS['taxon_id']['re'].pattern}", v))

    for r in prereg_rows:
        idx = r.get("_row") if "_row" in r else r.get("_idx")
        where = f"prereg:{'row' if '_row' in r else 'idx'}{idx}"
        v = r.get("prereg_id")
        if v is None:
            issues.append(Issue("MISSING_REQUIRED", where, "prereg_id is required", None))
        elif not _schema_ok("prereg_id", v):
            issues.append(Issue("SCHEMA_VIOLATION", where, f"prereg_id does not conform to {ID_SCHEMAS['prereg_id']['re'].pattern}", v))

    for fld in ("study_id", "doc_id"):
        d = _dupes([(f"extraction.csv:row{r.get('_row')}", r.get(fld)) for r in extraction_rows])
        for v, wheres in d.items():
            issues.append(Issue("DUPLICATE_ID", "extraction.csv", f"Duplicate {fld}={v} in " + ", ".join(wheres), v))

    d = _dupes([(f"taxonomy.jsonl:line{r.get('_line')}", r.get("taxon_id")) for r in taxonomy_rows])
    for v, wheres in d.items():
        issues.append(Issue("DUPLICATE_ID", "taxonomy.jsonl", f"Duplicate taxon_id={v} in " + ", ".join(wheres), v))

    d = _dupes([(f"prereg:{'row' if '_row' in r else 'idx'}{(r.get('_row') if '_row' in r else r.get('_idx'))}", r.get("prereg_id")) for r in prereg_rows])
    for v, wheres in d.items():
        issues.append(Issue("DUPLICATE_ID", "prereg", f"Duplicate prereg_id={v} in " + ", ".join(wheres), v))

    taxon_set = {r.get("taxon_id") for r in taxonomy_rows if r.get("taxon_id")}
    prereg_set = {r.get("prereg_id") for r in prereg_rows if r.get("prereg_id")}
    for r in extraction_rows:
        where = f"extraction.csv:row{r.get('_row')}"
        t = r.get("taxon_id")
        if t and t not in taxon_set:
            issues.append(Issue("MISSING_REFERENCE", where, "taxon_id not found in taxonomy.jsonl", t))
        p = r.get("prereg_id")
        if p and p not in prereg_set:
            issues.append(Issue("MISSING_REFERENCE", where, "prereg_id not found in prereg source", p))

    return issues

def check_paths(extraction_csv: Path, taxonomy_jsonl: Path, prereg_path: Path) -> List[Issue]:
    return check_ids(read_extraction_csv(extraction_csv), read_taxonomy_jsonl(taxonomy_jsonl), read_prereg(prereg_path))

def format_issues(issues: Sequence[Issue]) -> str:
    if not issues:
        return "OK: no issues found."
    lines = [f"FOUND {len(issues)} ISSUE(S):"]
    for i, iss in enumerate(issues, start=1):
        v = "" if iss.value is None else f" | value={iss.value}"
        lines.append(f"{i:02d}. {iss.code} @ {iss.where}: {iss.message}{v}")
    return "\n".join(lines)

def write_demo_dataset(base_dir: Path) -> Tuple[Path, Path, Path]:
    base_dir.mkdir(parents=True, exist_ok=True)
    ex = base_dir / "extraction.csv"
    tx = base_dir / "taxonomy.jsonl"
    pr = base_dir / "prereg.json"
    ex.write_text(
        "study_id,doc_id,taxon_id,prereg_id\n"
        "STU0001,DOC-ABC123,TAX:001,PRG-00001\n"
        "STU0001,DOC-ABC123,TAX:999,PRG-99999\n"
        "stu0002,DOC-ABC12X,TAX:002,PRG-00002\n"
        "BAD1,DOC-ABC123,TAX:003,\n",
        encoding="utf-8",
    )
    tx.write_text(
        json.dumps({"taxon_id": "TAX:001", "label": "nudge"}) + "\n" +
        json.dumps({"taxon_id": "TAX:002", "label": "default"}) + "\n" +
        json.dumps({"taxon_id": "TAX:002", "label": "duplicate"}) + "\n",
        encoding="utf-8",
    )
    pr.write_text(json.dumps({"items": [
        {"prereg_id": "PRG-00001", "study_id": "STU0001"},
        {"prereg_id": "PRG-00002", "study_id": "STU0002"},
        {"prereg_id": "PRG-00002", "study_id": "STU9999"},
    ]}), encoding="utf-8")
    return ex, tx, pr

if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1] / "data" / "demo"
    ex, tx, pr = write_demo_dataset(base)
    issues = check_paths(ex, tx, pr)
    print(format_issues(issues))
