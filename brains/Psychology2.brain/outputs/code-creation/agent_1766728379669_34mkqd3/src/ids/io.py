from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union
import csv
import json
import re

try:
    from . import convention as _conv  # type: ignore
except Exception:  # pragma: no cover
    _conv = None

STUDY_ID_KEYS = ("StudyID", "study_id", "studyid", "studyID", "STUDYID")
EFFECT_ID_KEYS = ("EffectID", "effect_id", "effectid", "effectID", "EFFECTID")

_FALLBACK_STUDY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
_FALLBACK_EFFECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")


@dataclass(frozen=True)
class ParsedIDs:
    study_id: Optional[str]
    effect_id: Optional[str]
    source: str


def _get_first_key(d: Mapping[str, Any], keys: Sequence[str]) -> Tuple[Optional[str], Optional[Any]]:
    for k in keys:
        if k in d:
            return k, d[k]
    return None, None


def extract_ids_from_record(rec: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    _, sid = _get_first_key(rec, STUDY_ID_KEYS)
    _, eid = _get_first_key(rec, EFFECT_ID_KEYS)
    sid = None if sid is None else str(sid).strip()
    eid = None if eid is None else str(eid).strip()
    sid = sid or None
    eid = eid or None
    if _conv:
        try:
            sid = _conv.normalize_study_id(sid) if sid is not None else None
        except Exception:
            pass
        try:
            eid = _conv.normalize_effect_id(eid) if eid is not None else None
        except Exception:
            pass
    return sid, eid


def ensure_id_fields(rec: Dict[str, Any], *, prefer_canonical: bool = True) -> Dict[str, Any]:
    sid, eid = extract_ids_from_record(rec)
    if prefer_canonical:
        if sid is not None:
            rec["StudyID"] = sid
        if eid is not None:
            rec["EffectID"] = eid
    else:
        k, _ = _get_first_key(rec, STUDY_ID_KEYS)
        if sid is not None and not k:
            rec["StudyID"] = sid
        k, _ = _get_first_key(rec, EFFECT_ID_KEYS)
        if eid is not None and not k:
            rec["EffectID"] = eid
    return rec


def validate_ids(study_id: Optional[str], effect_id: Optional[str]) -> List[str]:
    errs: List[str] = []
    if _conv:
        try:
            if study_id is not None and not _conv.is_valid_study_id(study_id):
                errs.append(f"Invalid StudyID: {study_id!r}")
        except Exception:
            pass
        try:
            if effect_id is not None and not _conv.is_valid_effect_id(effect_id):
                errs.append(f"Invalid EffectID: {effect_id!r}")
        except Exception:
            pass
        return errs
    if study_id is not None and not _FALLBACK_STUDY_RE.match(study_id):
        errs.append(f"Invalid StudyID: {study_id!r}")
    if effect_id is not None and not _FALLBACK_EFFECT_RE.match(effect_id):
        errs.append(f"Invalid EffectID: {effect_id!r}")
    return errs
def read_csv_records(path: Union[str, Path], *, ensure_ids: bool = True) -> List[Dict[str, Any]]:
    p = Path(path)
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, Any]] = [dict(r) for r in reader]
    if ensure_ids:
        for r in rows:
            ensure_id_fields(r, prefer_canonical=True)
    return rows


def write_csv_records(
    path: Union[str, Path],
    records: Sequence[Mapping[str, Any]],
    *,
    fieldnames: Optional[Sequence[str]] = None,
    ensure_ids: bool = True,
) -> None:
    p = Path(path)
    rows: List[Dict[str, Any]] = [dict(r) for r in records]
    if ensure_ids:
        for r in rows:
            ensure_id_fields(r, prefer_canonical=True)

    if fieldnames is None:
        fn: List[str] = []
        seen = set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    seen.add(k)
                    fn.append(k)
        if "StudyID" in seen:
            fn = ["StudyID"] + [k for k in fn if k != "StudyID"]
        if "EffectID" in seen:
            if "StudyID" in fn:
                i = fn.index("StudyID") + 1
                fn = fn[:i] + ["EffectID"] + [k for k in fn[i:] if k != "EffectID"]
            else:
                fn = ["EffectID"] + [k for k in fn if k != "EffectID"]
        fieldnames = fn

    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames})
def iter_jsonl(path: Union[str, Path], *, ensure_ids: bool = True) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {i} of {p}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL line {i} of {p} must be an object/dict")
            if ensure_ids:
                ensure_id_fields(obj, prefer_canonical=True)
            yield obj


def read_jsonl_records(path: Union[str, Path], *, ensure_ids: bool = True) -> List[Dict[str, Any]]:
    return list(iter_jsonl(path, ensure_ids=ensure_ids))


def write_jsonl_records(path: Union[str, Path], records: Iterable[Mapping[str, Any]], *, ensure_ids: bool = True) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r0 in records:
            r = dict(r0)
            if ensure_ids:
                ensure_id_fields(r, prefer_canonical=True)
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True))
            f.write("\n")
_PREREG_PATTERNS = [
    ("StudyID", re.compile(r"(?im)^\s*StudyID\s*[:=]\s*(?P<v>[^\r\n#]+)")),
    ("StudyID", re.compile(r"(?im)^\s*study_id\s*[:=]\s*(?P<v>[^\r\n#]+)")),
    ("EffectID", re.compile(r"(?im)^\s*EffectID\s*[:=]\s*(?P<v>[^\r\n#]+)")),
    ("EffectID", re.compile(r"(?im)^\s*effect_id\s*[:=]\s*(?P<v>[^\r\n#]+)")),
]


def parse_prereg_template(text_or_path: Union[str, Path]) -> ParsedIDs:
    if isinstance(text_or_path, Path) or (isinstance(text_or_path, str) and Path(text_or_path).exists()):
        p = Path(text_or_path)
        text = p.read_text(encoding="utf-8")
        source = str(p)
    else:
        text = str(text_or_path)
        source = "<string>"

    found: Dict[str, Optional[str]] = {"StudyID": None, "EffectID": None}
    for key, pat in _PREREG_PATTERNS:
        m = pat.search(text)
        if m and found[key] is None:
            v = m.group("v").strip().strip('"').strip("'")
            if v and not re.fullmatch(r"\{\{.*\}\}", v):
                found[key] = v

    sid, eid = found["StudyID"], found["EffectID"]
    if _conv:
        try:
            sid = _conv.normalize_study_id(sid) if sid is not None else None
        except Exception:
            pass
        try:
            eid = _conv.normalize_effect_id(eid) if eid is not None else None
        except Exception:
            pass
    return ParsedIDs(study_id=sid, effect_id=eid, source=source)
