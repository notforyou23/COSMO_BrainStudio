from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json


@dataclass(frozen=True)
class Candidate:
    path: Path
    kind: str  # "qa_runner" | "schema" | other
    meta: Dict[str, Any] = field(default_factory=dict)


def _safe_stat(p: Path):
    try:
        return p.stat()
    except Exception:
        return None


def _read_text(p: Path, limit: int = 200_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def _is_probably_python_runner(p: Path, txt: str) -> bool:
    n = p.name.lower()
    if p.suffix.lower() == ".py":
        if any(k in n for k in ("qa", "test", "validate", "runner", "check")):
            return True
        if "def main" in txt or "if __name__" in txt:
            return True
    return False


def _is_probably_shell_runner(p: Path, txt: str) -> bool:
    if p.suffix.lower() not in (".sh", ".bash"):
        return False
    return ("python" in txt) or ("pytest" in txt) or ("validate" in txt) or ("qa" in p.name.lower())


def _json_load(p: Path) -> Optional[Any]:
    try:
        return json.loads(_read_text(p))
    except Exception:
        return None


def _looks_like_json_schema(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    if any(k in obj for k in ("$schema", "properties", "required", "type", "definitions", "$defs")):
        return True
    return False


def _name_score(name_lower: str, kind: str) -> float:
    good = 0.0
    bad = 0.0
    if kind == "qa_runner":
        for k in ("qa", "validate", "runner", "check", "tests", "pytest", "smoke"):
            if k in name_lower:
                good += 2.0
        for k in ("draft", "old", "backup", "copy", "tmp", "scratch", "wip", "attempt"):
            if k in name_lower:
                bad += 2.0
    elif kind == "schema":
        for k in ("schema", "output", "artifact", "manifest", "index"):
            if k in name_lower:
                good += 2.0
        for k in ("draft", "old", "backup", "copy", "tmp", "scratch", "wip", "attempt"):
            if k in name_lower:
                bad += 2.0
    return good - bad


def _recency_score(p: Path) -> float:
    st = _safe_stat(p)
    if not st:
        return -1e6
    return float(st.st_mtime)


def _size_score(p: Path) -> float:
    st = _safe_stat(p)
    if not st:
        return -1e6
    # Prefer "not tiny" but cap influence.
    sz = float(st.st_size)
    if sz <= 0:
        return -1e6
    return min(10.0, (sz ** 0.5) / 50.0)


def score_candidate(c: Candidate) -> Tuple[float, Dict[str, float]]:
    p = c.path
    kind = c.kind
    name = p.name.lower()
    txt = _read_text(p, limit=120_000) if p.is_file() else ""
    parts: Dict[str, float] = {}
    parts["name"] = _name_score(name, kind)
    parts["recency"] = _recency_score(p) / 1e7  # scale down
    parts["size"] = _size_score(p)

    valid_bonus = 0.0
    completeness = 0.0

    if kind == "qa_runner":
        if _is_probably_python_runner(p, txt):
            valid_bonus += 4.0
        if _is_probably_shell_runner(p, txt):
            valid_bonus += 3.0
        if "argparse" in txt or "click" in txt:
            completeness += 1.0
        if "json" in txt and ("ARTIFACT_INDEX" in txt or "artifact" in txt.lower()):
            completeness += 1.0
        if c.meta.get("validation_passed") is True:
            valid_bonus += 6.0
        if c.meta.get("can_execute") is False:
            valid_bonus -= 6.0

    elif kind == "schema":
        obj = _json_load(p) if p.suffix.lower() in (".json", ".schema") else None
        if obj is not None:
            valid_bonus += 4.0
            if _looks_like_json_schema(obj):
                completeness += 4.0
            if isinstance(obj, dict) and "properties" in obj and isinstance(obj["properties"], dict):
                completeness += min(4.0, len(obj["properties"]) / 5.0)
        if c.meta.get("validation_passed") is True:
            valid_bonus += 6.0

    parts["valid"] = valid_bonus
    parts["complete"] = completeness

    total = parts["name"] + parts["recency"] + parts["size"] + parts["valid"] + parts["complete"]

    # Penalize paths that look like per-agent scratch outputs to encourage canonical naming.
    pstr = str(p).lower()
    if any(k in pstr for k in ("agent_", "attempt", "stage", "scratch", "tmp", "runtime/outputs")):
        total -= 0.5

    return total, parts


def rank_candidates(candidates: Iterable[Candidate]) -> List[Tuple[Candidate, float, Dict[str, float]]]:
    ranked: List[Tuple[Candidate, float, Dict[str, float]]] = []
    for c in candidates:
        score, parts = score_candidate(c)
        ranked.append((c, score, parts))
    ranked.sort(key=lambda t: (-t[1], str(t[0].path).lower()))
    return ranked


def select_authoritative(candidates: Iterable[Candidate], kind: str) -> Optional[Candidate]:
    ranked = rank_candidates([c for c in candidates if c.kind == kind])
    return ranked[0][0] if ranked else None


def select_authoritative_pair(candidates: Iterable[Candidate]) -> Tuple[Optional[Candidate], Optional[Candidate]]:
    qa = select_authoritative(candidates, "qa_runner")
    schema = select_authoritative(candidates, "schema")
    return qa, schema
