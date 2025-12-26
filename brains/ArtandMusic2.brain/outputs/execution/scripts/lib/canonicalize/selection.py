from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union


@dataclass(frozen=True)
class ScoredCandidate:
    path: Path
    score: Tuple[int, int, int, int, int, str]
    meta: Dict[str, Any]


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "ok", "pass", "passed", "success", "successful"}


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _stat_meta(p: Path) -> Dict[str, Any]:
    try:
        st = p.stat()
        return {"mtime": int(st.st_mtime), "size": int(st.st_size)}
    except Exception:
        return {"mtime": 0, "size": 0}


def _name_score(name: str, kind: str) -> int:
    n = name.lower()
    good = 0
    bad = 0

    prefer = {"canonical": 12, "authoritative": 10, "final": 7, "latest": 6, "stable": 5, "release": 4, "gold": 4}
    avoid = {"tmp": 8, "temp": 8, "draft": 6, "wip": 6, "old": 5, "backup": 6, "bak": 6, "copy": 4, "test": 4, "experimental": 5}

    for k, w in prefer.items():
        if k in n:
            good += w
    for k, w in avoid.items():
        if k in n:
            bad += w

    if kind == "qa_runner":
        if "qa" in n:
            good += 3
        if "runner" in n or "run_qa" in n or "qa_run" in n:
            good += 4
        if n.endswith(".py"):
            good += 3
        if n.endswith(".sh"):
            good += 2
        if "validate" in n or "validation" in n:
            good += 1
    elif kind == "schema":
        if "schema" in n:
            good += 5
        if n.endswith(".json"):
            good += 3
        if n.endswith(".yaml") or n.endswith(".yml"):
            good += 2
        if "output" in n or "artifact" in n:
            good += 1

    if "/" in n or "\\" in n:
        n = n.replace("\\", "/").split("/")[-1]
    if n.startswith((".", "_")):
        bad += 2
    return max(-50, min(50, good - bad))


def _ext_ok(p: Path, kind: str) -> int:
    ext = p.suffix.lower()
    if kind == "qa_runner":
        return 3 if ext in {".py", ".sh"} else (1 if ext in {".ps1"} else -2)
    if kind == "schema":
        return 3 if ext in {".json", ".yaml", ".yml"} else -2
    return 0


def _score(path: Path, kind: str, meta: Dict[str, Any]) -> Tuple[int, int, int, int, int, str]:
    m = dict(_stat_meta(path))
    m.update({k: v for k, v in (meta or {}).items() if v is not None})

    validated = _as_bool(m.get("validated")) or _as_bool(m.get("validation_success"))
    errors = _safe_int(m.get("validation_errors") or m.get("errors") or 0, 0)
    val_score = 100 if validated and errors == 0 else (30 if validated else (-50 if errors > 0 else 0))

    name = str(m.get("name") or path.name)
    naming = _name_score(name, kind)
    ext = _ext_ok(path, kind)
    completeness = min(1000000, _safe_int(m.get("size"), 0))
    recency = _safe_int(m.get("mtime"), 0)

    # Deterministic: sort by score tuple then path string.
    # Order of precedence: validation, naming, ext, completeness, recency, path.
    return (val_score, naming, ext, completeness, recency, str(path).replace("\\", "/"))


def score_candidates(
    candidates: Sequence[Union[Path, str, Dict[str, Any]]],
    kind: str,
) -> List[ScoredCandidate]:
    out: List[ScoredCandidate] = []
    for c in candidates or []:
        meta: Dict[str, Any] = {}
        if isinstance(c, dict):
            p = Path(c.get("path") or c.get("file") or c.get("filepath") or c.get("full_path") or "")
            meta = dict(c)
        else:
            p = Path(c)
        if not str(p):
            continue
        s = _score(p, kind, meta)
        out.append(ScoredCandidate(path=p, score=s, meta=meta))
    out.sort(key=lambda x: x.score, reverse=True)
    return out


def select_authoritative(
    candidates: Sequence[Union[Path, str, Dict[str, Any]]],
    kind: str,
) -> Optional[Path]:
    scored = score_candidates(candidates, kind)
    return scored[0].path if scored else None


def select_authoritative_qa_runner(candidates: Sequence[Union[Path, str, Dict[str, Any]]]) -> Optional[Path]:
    return select_authoritative(candidates, "qa_runner")


def select_authoritative_schema(candidates: Sequence[Union[Path, str, Dict[str, Any]]]) -> Optional[Path]:
    return select_authoritative(candidates, "schema")


def ranked_debug_table(
    candidates: Sequence[Union[Path, str, Dict[str, Any]]],
    kind: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    scored = score_candidates(candidates, kind)[: max(0, int(limit))]
    rows: List[Dict[str, Any]] = []
    for sc in scored:
        val, naming, ext, size, mtime, p = sc.score
        rows.append(
            {
                "path": p,
                "val_score": val,
                "naming_score": naming,
                "ext_score": ext,
                "size": size,
                "mtime": mtime,
                "validated": _as_bool(sc.meta.get("validated") or sc.meta.get("validation_success")),
                "validation_errors": _safe_int(sc.meta.get("validation_errors") or sc.meta.get("errors") or 0, 0),
            }
        )
    return rows
