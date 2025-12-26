"""Project taxonomy and helpers for rubric tagging rules.

This module defines approved categories/tags and provides normalization and
validation utilities so generated rubric tagging rules align with the taxonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
import re
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")


def slugify(text: str) -> str:
    """Return a lowercase, hyphenated slug for consistent tag IDs."""
    if text is None:
        return ""
    s = str(text).strip().lower()
    s = _WHITESPACE_RE.sub(" ", s)
    s = _SLUG_RE.sub("-", s).strip("-")
    return s
@dataclass(frozen=True)
class Tag:
    category: str
    id: str
    label: str

    def as_ref(self) -> str:
        return f"{self.category}:{self.id}"


def _mk(category: str, label: str) -> Tag:
    return Tag(category=category, id=slugify(label), label=label)
# Canonical taxonomy: keep stable names to ensure deterministic tagging.
TAXONOMY: Dict[str, Tuple[Tag, ...]] = {
    "theme": (
        _mk("theme", "Equity & Access"),
        _mk("theme", "Measurement & Evaluation"),
        _mk("theme", "Selection & Gatekeeping"),
        _mk("theme", "Governance & Accountability"),
        _mk("theme", "Technology & Data"),
        _mk("theme", "Workforce & Professionalization"),
        _mk("theme", "Community Power & Participation"),
        _mk("theme", "Policy & Regulation"),
    ),
    "sector": (
        _mk("sector", "Education"),
        _mk("sector", "Healthcare"),
        _mk("sector", "Public Sector"),
        _mk("sector", "Nonprofit"),
        _mk("sector", "Private Sector"),
        _mk("sector", "Philanthropy"),
    ),
    "actor": (
        _mk("actor", "Government"),
        _mk("actor", "School / University"),
        _mk("actor", "Hospital / Clinic"),
        _mk("actor", "Employer"),
        _mk("actor", "Community Organization"),
        _mk("actor", "Funders"),
        _mk("actor", "Researchers"),
        _mk("actor", "Vendors / Platforms"),
    ),
    "mechanism": (
        _mk("mechanism", "Incentives"),
        _mk("mechanism", "Information / Transparency"),
        _mk("mechanism", "Standards / Requirements"),
        _mk("mechanism", "Capacity Building"),
        _mk("mechanism", "Resource Allocation"),
        _mk("mechanism", "Feedback Loops"),
        _mk("mechanism", "Selection Loop"),
    ),
    "evidence": (
        _mk("evidence", "Peer-reviewed Research"),
        _mk("evidence", "Official Report / Audit"),
        _mk("evidence", "Policy / Statute"),
        _mk("evidence", "Dataset / Dashboard"),
        _mk("evidence", "Investigative Journalism"),
        _mk("evidence", "Primary Media (Official)"),
    ),
    "rights": (
        _mk("rights", "Public Domain / Government Work"),
        _mk("rights", "Creative Commons"),
        _mk("rights", "Licensed / Permission Granted"),
        _mk("rights", "Unknown / Needs Review"),
    ),
}
# Aliases map common freeform values to canonical tag IDs per category.
ALIASES: Dict[str, Dict[str, str]] = {
    "theme": {
        "equity": "equity-access",
        "access": "equity-access",
        "measurement": "measurement-evaluation",
        "evaluation": "measurement-evaluation",
        "assessment": "measurement-evaluation",
        "gatekeeping": "selection-gatekeeping",
        "selection": "selection-gatekeeping",
        "accountability": "governance-accountability",
        "governance": "governance-accountability",
        "tech": "technology-data",
        "data": "technology-data",
        "workforce": "workforce-professionalization",
        "community": "community-power-participation",
        "policy": "policy-regulation",
        "regulation": "policy-regulation",
    },
    "rights": {
        "pd": "public-domain-government-work",
        "public-domain": "public-domain-government-work",
        "cc": "creative-commons",
        "creative commons": "creative-commons",
        "unknown": "unknown-needs-review",
        "needs review": "unknown-needs-review",
    },
}
def categories() -> Tuple[str, ...]:
    return tuple(TAXONOMY.keys())


def tags_for(category: str) -> Tuple[Tag, ...]:
    if category not in TAXONOMY:
        raise KeyError(f"Unknown category: {category}")
    return TAXONOMY[category]


def tag_ids(category: str) -> Set[str]:
    return {t.id for t in tags_for(category)}


def tag_labels(category: str) -> Set[str]:
    return {t.label for t in tags_for(category)}
def canonical_tag_id(category: str, value: str) -> Optional[str]:
    """Return canonical tag id for a freeform value (id/label/alias), else None."""
    if not value:
        return None
    cat = category
    raw = str(value).strip()
    sid = slugify(raw)
    if sid in tag_ids(cat):
        return sid
    # match by label
    for t in tags_for(cat):
        if slugify(t.label) == sid:
            return t.id
    # alias lookup
    a = ALIASES.get(cat, {})
    if sid in a:
        return a[sid]
    if raw.lower().strip() in a:
        return a[raw.lower().strip()]
    return None


def validate_tag(category: str, value: str) -> Tag:
    """Validate and return a Tag; raises ValueError if not in taxonomy."""
    tid = canonical_tag_id(category, value)
    if not tid:
        raise ValueError(f"Unrecognized tag for {category}: {value!r}")
    for t in tags_for(category):
        if t.id == tid:
            return t
    raise ValueError(f"Canonical tag id missing for {category}: {tid}")
def normalize_tags(category: str, values: Sequence[str]) -> List[Tag]:
    """Normalize a list of freeform values into canonical Tags (deduped, stable)."""
    seen: Set[str] = set()
    out: List[Tag] = []
    for v in values or ():
        if v is None:
            continue
        t = validate_tag(category, str(v))
        if t.id not in seen:
            seen.add(t.id)
            out.append(t)
    out.sort(key=lambda x: x.id)
    return out


def normalize_tag_refs(tags: Mapping[str, Sequence[str]]) -> Dict[str, List[str]]:
    """Normalize tags mapping into {category: [category:id,...]} for rubric rules."""
    out: Dict[str, List[str]] = {}
    for cat, vals in (tags or {}).items():
        cat = str(cat).strip()
        if cat not in TAXONOMY:
            raise KeyError(f"Unknown category: {cat}")
        out[cat] = [t.as_ref() for t in normalize_tags(cat, list(vals or ()))]
    return out


def allowed_tag_refs() -> Dict[str, List[str]]:
    """Return {category: [category:id,...]} for UI/help text."""
    return {c: [t.as_ref() for t in tags_for(c)] for c in categories()}
def rubric_tagging_rules() -> Dict[str, str]:
    """Human-readable rules designed to be embedded into CASE_STUDY_RUBRIC.md."""
    return {
        "format": "Use canonical refs 'category:tag-id' (lowercase, hyphenated).",
        "multi": "You may apply multiple tags per category; avoid duplicates.",
        "required": "Always provide at least one 'theme' tag; add 'rights' when media is included.",
        "alignment": "Only use tags from the approved taxonomy; map synonyms via aliases when needed.",
        "validation": "Before writing, run normalize_tag_refs() to ensure tags are canonical.",
    }
