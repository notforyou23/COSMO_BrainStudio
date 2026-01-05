from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = BASE_DIR / "outputs"
LOGS_DIR = OUTPUTS_DIR / "logs"
ARTIFACT_DIR_CANDIDATES = [
    OUTPUTS_DIR / "artifacts",
    BASE_DIR / "artifacts",
    BASE_DIR / "outputs" / "artifacts",
]

ID_KEYS = ("id", "ID", "Id", "record_id", "recordId", "uuid", "UUID")


def _ensure_logs_dir() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR


def _write_gate_log(gate: str, passed: bool, metrics: Dict[str, int], details: Optional[Dict] = None) -> None:
    _ensure_logs_dir()
    payload = {
        "gate": gate,
        "status": "pass" if passed else "fail",
        "metrics": metrics,
    }
    if details:
        payload["details"] = details
    (LOGS_DIR / f"{gate}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iter_artifact_files() -> List[Path]:
    files: List[Path] = []
    for d in ARTIFACT_DIR_CANDIDATES:
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.suffix.lower() in (".csv", ".tsv", ".json", ".jsonl"):
                    files.append(p)
    return files


def _normalize_id(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (int, float)) and v != v:  # NaN
        return None
    s = str(v).strip()
    if not s or s.lower() in ("null", "none", "nan"):
        return None
    return s


def _read_ids_csv(path: Path) -> Tuple[str, List[Optional[str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
        reader = csv.DictReader(f, dialect=dialect)
        if reader.fieldnames is None:
            return "", []
        id_col = next((c for c in reader.fieldnames if c in ID_KEYS), reader.fieldnames[0])
        vals: List[Optional[str]] = []
        for row in reader:
            vals.append(_normalize_id(row.get(id_col)))
        return id_col, vals


def _read_ids_jsonl(path: Path) -> Tuple[str, List[Optional[str]]]:
    vals: List[Optional[str]] = []
    id_col = ""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                continue
            if not id_col:
                id_col = next((k for k in obj.keys() if k in ID_KEYS), "")
            v = obj.get(id_col) if id_col else next((obj.get(k) for k in ID_KEYS if k in obj), None)
            vals.append(_normalize_id(v))
    return id_col, vals


def _read_ids_json(path: Path) -> Tuple[str, List[Optional[str]]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    rows: Iterable = obj if isinstance(obj, list) else obj.get("data", []) if isinstance(obj, dict) else []
    vals: List[Optional[str]] = []
    id_col = ""
    for r in rows:
        if not isinstance(r, dict):
            continue
        if not id_col:
            id_col = next((k for k in r.keys() if k in ID_KEYS), "")
        v = r.get(id_col) if id_col else next((r.get(k) for k in ID_KEYS if k in r), None)
        vals.append(_normalize_id(v))
    return id_col, vals


def _load_artifact_ids(path: Path) -> Tuple[str, List[Optional[str]]]:
    suf = path.suffix.lower()
    if suf in (".csv", ".tsv"):
        return _read_ids_csv(path)
    if suf == ".jsonl":
        return _read_ids_jsonl(path)
    if suf == ".json":
        return _read_ids_json(path)
    return "", []


@dataclass
class ArtifactIDStats:
    path: Path
    id_col: str
    total_rows: int
    missing_ids: int
    duplicate_ids: int
    unique_ids: Set[str]


def _compute_stats(path: Path) -> ArtifactIDStats:
    id_col, vals = _load_artifact_ids(path)
    total = len(vals)
    missing = sum(1 for v in vals if v is None)
    seen: Set[str] = set()
    dup = 0
    uniq: Set[str] = set()
    for v in vals:
        if v is None:
            continue
        if v in seen:
            dup += 1
        else:
            seen.add(v)
            uniq.add(v)
    return ArtifactIDStats(path=path, id_col=id_col, total_rows=total, missing_ids=missing, duplicate_ids=dup, unique_ids=uniq)


def run_id_integrity_gate(artifact_files: Optional[List[Path]] = None) -> Tuple[bool, Dict[str, int], Dict]:
    files = artifact_files if artifact_files is not None else _iter_artifact_files()
    if not files:
        metrics = {"artifact_files": 0, "missing_ids": 0, "duplicate_ids": 0, "non_joinable_ids": 0}
        details = {"artifacts": []}
        _write_gate_log("id_integrity", True, metrics, details)
        return True, metrics, details

    stats = [_compute_stats(p) for p in files]
    union_all: Set[str] = set().union(*(s.unique_ids for s in stats)) if stats else set()
    metrics = {
        "artifact_files": len(stats),
        "missing_ids": sum(s.missing_ids for s in stats),
        "duplicate_ids": sum(s.duplicate_ids for s in stats),
        "non_joinable_ids": 0,
    }
    per_artifact = []
    total_non_joinable = 0
    for s in stats:
        others_union = union_all - s.unique_ids
        joinable = s.unique_ids.intersection(others_union) if len(stats) > 1 else set()
        non_joinable = len(s.unique_ids - joinable) if len(stats) > 1 else 0
        total_non_joinable += non_joinable
        per_artifact.append(
            {
                "path": str(s.path),
                "id_col": s.id_col,
                "total_rows": s.total_rows,
                "missing_ids": s.missing_ids,
                "duplicate_ids": s.duplicate_ids,
                "unique_ids": len(s.unique_ids),
                "non_joinable_ids": non_joinable,
            }
        )
    metrics["non_joinable_ids"] = total_non_joinable
    passed = metrics["missing_ids"] == 0 and metrics["duplicate_ids"] == 0 and metrics["non_joinable_ids"] == 0
    details = {"artifacts": per_artifact}
    _write_gate_log("id_integrity", passed, metrics, details)
    return passed, metrics, details


def main(argv: Optional[List[str]] = None) -> int:
    passed, metrics, _details = run_id_integrity_gate()
    if not passed:
        sys.stderr.write(
            "ID integrity gate failed: "
            + ", ".join(f"{k}={v}" for k, v in metrics.items() if k != "artifact_files")
            + "\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
