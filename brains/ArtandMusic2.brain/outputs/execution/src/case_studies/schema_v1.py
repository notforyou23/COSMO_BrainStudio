"""V1 case-study metadata schema + dependency-free validator.

This module intentionally avoids third-party dependencies for use in CI/hooks.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCHEMA_VERSION = "v1"

WORKSTREAM_TYPES = (
    "research",
    "product",
    "engineering",
    "data_science",
    "design",
    "operations",
    "policy",
    "other",
)

STATUS_VALUES = ("draft", "active", "archived")

# Field spec: name -> (required, kind)
# kind is a lightweight tag used by the validator.
FIELDS = {
    "schema_version": (True, "literal:v1"),
    "case_id": (True, "slug"),
    "title": (True, "str"),
    "summary": (True, "str"),
    "workstream_type": (True, "enum:workstream_type"),
    "status": (False, "enum:status"),
    "owners": (False, "list[str]"),
    "tags": (False, "list[str]"),
    "created_date": (False, "date"),
    "updated_date": (False, "date"),
    "links": (False, "list[link]"),
}
def default_metadata(case_id: str, title: str, *, workstream_type: str = "research") -> Dict[str, Any]:
    today = date.today().isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "title": title,
        "summary": "",
        "workstream_type": workstream_type,
        "status": "draft",
        "owners": [],
        "tags": [],
        "created_date": today,
        "updated_date": today,
        "links": [],
    }


def validate_metadata(data: Any, *, allow_extra_keys: bool = False) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    if not isinstance(data, dict):
        return False, ["metadata must be an object (dict)"]

    if not allow_extra_keys:
        extra = sorted(k for k in data.keys() if k not in FIELDS)
        if extra:
            errs.append(f"unexpected field(s): {', '.join(extra)}")

    for field, (required, kind) in FIELDS.items():
        if required and field not in data:
            errs.append(f"missing required field: {field}")

        if field not in data:
            continue
        v = data[field]

        if kind == "literal:v1":
            if v != SCHEMA_VERSION:
                errs.append(f"{field} must be {SCHEMA_VERSION!r}")
        elif kind == "str":
            if not isinstance(v, str) or not v.strip():
                errs.append(f"{field} must be a non-empty string")
        elif kind == "slug":
            if not isinstance(v, str) or not v or any(c.isspace() for c in v) or "/" in v or "\" in v:
                errs.append(f"{field} must be a URL/path-safe slug (no spaces or slashes)")
        elif kind == "enum:workstream_type":
            if v not in WORKSTREAM_TYPES:
                errs.append(f"{field} must be one of: {', '.join(WORKSTREAM_TYPES)}")
        elif kind == "enum:status":
            if v not in STATUS_VALUES:
                errs.append(f"{field} must be one of: {', '.join(STATUS_VALUES)}")
        elif kind == "list[str]":
            if not _is_list_of_str(v):
                errs.append(f"{field} must be a list of strings")
        elif kind == "date":
            if v is not None and not _is_iso_date(v):
                errs.append(f"{field} must be an ISO date string YYYY-MM-DD")
        elif kind == "list[link]":
            if not isinstance(v, list):
                errs.append(f"{field} must be a list of link objects")
            else:
                for i, item in enumerate(v):
                    _validate_link(item, f"{field}[{i}]", errs)
        else:
            errs.append(f"internal schema error: unknown kind {kind!r} for {field}")
    return (len(errs) == 0), errs


def validate_or_raise(data: Any, *, allow_extra_keys: bool = False) -> None:
    ok, errs = validate_metadata(data, allow_extra_keys=allow_extra_keys)
    if not ok:
        raise ValueError("metadata validation failed:\n- " + "\n- ".join(errs))


def _is_list_of_str(v: Any) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _is_iso_date(v: Any) -> bool:
    if not isinstance(v, str):
        return False
    try:
        date.fromisoformat(v)
        return True
    except Exception:
        return False


def _validate_link(item: Any, path: str, errs: List[str]) -> None:
    if not isinstance(item, dict):
        errs.append(f"{path} must be an object with keys 'label' and 'url'")
        return
    label = item.get("label")
    url = item.get("url")
    if not isinstance(label, str) or not label.strip():
        errs.append(f"{path}.label must be a non-empty string")
    if not isinstance(url, str) or not url.strip():
        errs.append(f"{path}.url must be a non-empty string")
    elif not (url.startswith("http://") or url.startswith("https://")):
        errs.append(f"{path}.url must start with http:// or https://")
