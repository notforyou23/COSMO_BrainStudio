"""Sampling-frame builders for psyprim.

Provides:
- Frame builders for journals, archives, and researcher populations.
- Lightweight stratification and reproducible selection (seeded RNG).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import random
@dataclass(frozen=True)
class FrameItem:
    """A single sampling unit with stable id and attributes."""
    uid: str
    attrs: Dict[str, Any]


def _dedupe_keep_first(items: Iterable[FrameItem]) -> List[FrameItem]:
    seen = set()
    out: List[FrameItem] = []
    for it in items:
        if it.uid in seen:
            continue
        seen.add(it.uid)
        out.append(it)
    return out


def _as_items(records: Iterable[Mapping[str, Any]], uid_key: str) -> List[FrameItem]:
    out: List[FrameItem] = []
    for r in records:
        if uid_key not in r or r[uid_key] is None or str(r[uid_key]).strip() == "":
            raise ValueError(f"Record missing uid_key='{uid_key}': {dict(r)}")
        uid = str(r[uid_key])
        attrs = {k: v for k, v in dict(r).items() if k != uid_key}
        out.append(FrameItem(uid=uid, attrs=attrs))
    return _dedupe_keep_first(out)
def build_journal_frame(
    records: Iterable[Mapping[str, Any]],
    uid_key: str = "issn",
    required: Sequence[str] = ("title",),
) -> List[FrameItem]:
    """Build a journal frame; expects fields like issn/title/publisher/discipline/tier."""
    items = _as_items(records, uid_key=uid_key)
    for it in items:
        for k in required:
            if k not in it.attrs:
                raise ValueError(f"Journal {it.uid} missing required field '{k}'")
    return items


def build_archive_frame(
    records: Iterable[Mapping[str, Any]],
    uid_key: str = "archive_id",
    required: Sequence[str] = ("name",),
) -> List[FrameItem]:
    """Build an archive/repository frame; expects name/type/region/access_policy/etc."""
    items = _as_items(records, uid_key=uid_key)
    for it in items:
        for k in required:
            if k not in it.attrs:
                raise ValueError(f"Archive {it.uid} missing required field '{k}'")
    return items


def build_researcher_frame(
    records: Iterable[Mapping[str, Any]],
    uid_key: str = "orcid",
    required: Sequence[str] = ("role",),
) -> List[FrameItem]:
    """Build a researcher frame; expects orcid/role/career_stage/subfield/region/etc."""
    items = _as_items(records, uid_key=uid_key)
    for it in items:
        for k in required:
            if k not in it.attrs:
                raise ValueError(f"Researcher {it.uid} missing required field '{k}'")
    return items
def stratify(items: Sequence[FrameItem], keys: Sequence[str]) -> Dict[Tuple[Any, ...], List[FrameItem]]:
    """Group items into strata by attribute keys (missing -> None)."""
    strata: Dict[Tuple[Any, ...], List[FrameItem]] = {}
    for it in items:
        label = tuple(it.attrs.get(k, None) for k in keys)
        strata.setdefault(label, []).append(it)
    return strata


def _alloc_proportional(n: int, sizes: List[int], rng: random.Random) -> List[int]:
    if n < 0:
        raise ValueError("n must be >= 0")
    tot = sum(sizes)
    if tot == 0:
        return [0 for _ in sizes]
    raw = [n * (s / tot) for s in sizes]
    base = [int(x) for x in raw]
    rem = n - sum(base)
    frac = [(raw[i] - base[i], i) for i in range(len(sizes))]
    rng.shuffle(frac)
    frac.sort(reverse=True)
    for _, i in frac[:rem]:
        base[i] += 1
    return base


def select_sample(
    items: Sequence[FrameItem],
    n: int,
    strata_keys: Optional[Sequence[str]] = None,
    seed: int = 0,
    within_stratum: str = "shuffle",
) -> List[FrameItem]:
    """Reproducibly select n items; if strata_keys provided, sample proportionally within strata."""
    rng = random.Random(seed)
    if n >= len(items):
        return list(items)
    if not strata_keys:
        pool = list(items)
        rng.shuffle(pool)
        return pool[:n]
    grouped = stratify(items, list(strata_keys))
    labels = sorted(grouped.keys(), key=lambda t: tuple(str(x) for x in t))
    groups = [grouped[l] for l in labels]
    alloc = _alloc_proportional(n, [len(g) for g in groups], rng)
    out: List[FrameItem] = []
    for g, k in zip(groups, alloc):
        gg = list(g)
        if within_stratum == "shuffle":
            rng.shuffle(gg)
            out.extend(gg[:k])
        else:
            raise ValueError("within_stratum must be 'shuffle'")
    rng.shuffle(out)
    return out[:n]


def to_dict(items: Sequence[FrameItem]) -> List[Dict[str, Any]]:
    return [{"uid": it.uid, **it.attrs} for it in items]
