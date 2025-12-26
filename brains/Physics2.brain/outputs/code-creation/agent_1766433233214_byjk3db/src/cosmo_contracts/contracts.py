# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


BENCHMARK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*(?:\.[a-z0-9][a-z0-9\-]*)*$")
REQUIRED_METADATA: Tuple[str, ...] = (
    "title",
    "version",
    "summary",
    "inputs",
    "outputs",
)
def normalize_benchmark_id(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"^benchmark\s*[:/]\s*", "", s)
    s = s.replace("_", "-")
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\.\-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-.")
    if not s or not BENCHMARK_ID_RE.match(s):
        raise ValueError(f"Invalid benchmark_id after normalization: {raw!r} -> {s!r}")
    return s


def _jsonable(x: Any) -> Any:
    try:
        json.dumps(x, sort_keys=True, ensure_ascii=False)
        return x
    except TypeError:
        if hasattr(x, "__dict__"):
            return _jsonable(vars(x))
        if isinstance(x, (set, tuple)):
            return [_jsonable(v) for v in x]
        raise
def normalize_metadata(meta: Mapping[str, Any]) -> Dict[str, Any]:
    m = {str(k).strip(): _jsonable(v) for k, v in dict(meta or {}).items()}
    missing = [k for k in REQUIRED_METADATA if not m.get(k)]
    if missing:
        raise ValueError(f"Missing required metadata keys: {missing}")
    m["version"] = str(m["version"]).strip()
    m["title"] = str(m["title"]).strip()
    m["summary"] = str(m["summary"]).strip()
    for k in ("inputs", "outputs"):
        if not isinstance(m[k], (dict, list, str)):
            raise ValueError(f"metadata[{k!r}] must be a dict/list/str, got {type(m[k]).__name__}")
    return m


def default_tolerance_policy() -> Dict[str, Any]:
    # Conservative default: exact match unless benchmark overrides.
    return {"mode": "exact", "rtol": 0.0, "atol": 0.0, "nan_policy": "error"}


def normalize_tolerance_policy(tp: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    t = dict(default_tolerance_policy())
    if tp:
        t.update({str(k): _jsonable(v) for k, v in dict(tp).items()})
    mode = str(t.get("mode", "exact")).strip().lower()
    if mode not in {"exact", "numeric"}:
        raise ValueError("tolerance.mode must be 'exact' or 'numeric'")
    t["mode"] = mode
    t["rtol"] = float(t.get("rtol", 0.0))
    t["atol"] = float(t.get("atol", 0.0))
    nanp = str(t.get("nan_policy", "error")).strip().lower()
    if nanp not in {"error", "allow", "propagate"}:
        raise ValueError("tolerance.nan_policy must be 'error', 'allow', or 'propagate'")
    t["nan_policy"] = nanp
    return t
def normalize_invariants(invariants: Optional[Iterable[str]]) -> List[str]:
    inv: List[str] = []
    for x in invariants or []:
        s = str(x).strip()
        if s:
            inv.append(s)
    # de-dup while preserving order
    seen = set()
    out: List[str] = []
    for s in inv:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out


def normalize_reference(reference: Mapping[str, Any]) -> Dict[str, Any]:
    r = {str(k).strip(): _jsonable(v) for k, v in dict(reference or {}).items()}
    if not r.get("pseudocode"):
        raise ValueError("reference.pseudocode is required")
    r["pseudocode"] = str(r["pseudocode"]).strip()
    if r.get("notes") is not None:
        r["notes"] = str(r["notes"]).strip()
    return r
def normalize_test_vector(tv: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(tv, Mapping):
        raise ValueError("test_vector must be a mapping")
    out = {str(k).strip(): _jsonable(v) for k, v in dict(tv).items()}
    if "inputs" not in out or "expected" not in out:
        raise ValueError("test_vector must contain 'inputs' and 'expected'")
    return out


@dataclass(frozen=True)
class Contract:
    benchmark_id: str
    metadata: Dict[str, Any]
    reference: Dict[str, Any]
    invariants: List[str]
    tolerance: Dict[str, Any]
    canonical_test_vector: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "metadata": self.metadata,
            "reference": self.reference,
            "invariants": self.invariants,
            "tolerance": self.tolerance,
            "canonical_test_vector": self.canonical_test_vector,
        }
def build_contract(
    benchmark_id: str,
    *,
    metadata: Mapping[str, Any],
    reference: Mapping[str, Any],
    invariants: Optional[Iterable[str]] = None,
    tolerance: Optional[Mapping[str, Any]] = None,
    canonical_test_vector: Mapping[str, Any],
) -> Contract:
    return Contract(
        benchmark_id=normalize_benchmark_id(benchmark_id),
        metadata=normalize_metadata(metadata),
        reference=normalize_reference(reference),
        invariants=normalize_invariants(invariants),
        tolerance=normalize_tolerance_policy(tolerance),
        canonical_test_vector=normalize_test_vector(canonical_test_vector),
    )


def render_contract_markdown(contract: Contract) -> str:
    c = contract.as_dict()
    meta = json.dumps(c["metadata"], indent=2, sort_keys=True, ensure_ascii=False)
    ref = c["reference"].get("pseudocode", "")
    inv = "\n".join(f"- {s}" for s in c["invariants"]) or "- (none)"
    tol = json.dumps(c["tolerance"], indent=2, sort_keys=True, ensure_ascii=False)
    tv = json.dumps(c["canonical_test_vector"], indent=2, sort_keys=True, ensure_ascii=False)
    return (
        "## Contract\n\n"
        "### Required metadata\n\n```json\n" + meta + "\n```\n\n"
        "### Reference algorithm / pseudocode\n\n```text\n" + ref + "\n```\n\n"
        "### Output invariants\n\n" + inv + "\n\n"
        "### Tolerance policy\n\n```json\n" + tol + "\n```\n\n"
        "### Canonical test vector\n\n```json\n" + tv + "\n```\n"
    )
