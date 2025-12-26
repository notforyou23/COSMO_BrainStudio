from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


WORKSTREAM_TYPES = ("product", "research", "policy", "operations", "enablement", "other")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "case"


def _default_cases_root(cwd: Optional[Path] = None) -> Path:
    cwd = cwd or Path.cwd()
    for p in [cwd, *cwd.parents]:
        candidate = p / "case-studies"
        if candidate.exists() and candidate.is_dir():
            return candidate
    return cwd / "case-studies"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _try_external_validate(metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
    try:
        from .schema_v1 import validate_metadata as v  # type: ignore
        ok, errors = v(metadata)  # expected: (bool, [str]) or raises
        if isinstance(ok, bool) and isinstance(errors, list):
            return ok, [str(e) for e in errors]
        return False, ["schema_v1.validate_metadata returned an unexpected value"]
    except Exception as e:
        return False, [f"schema_v1 unavailable or errored: {e}"]


def _validate_v1_fallback(metadata: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    def req_str(k: str) -> None:
        v = metadata.get(k)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{k}: required non-empty string")
    req_str("id")
    req_str("title")
    req_str("summary")
    w = metadata.get("workstream_type")
    if w not in WORKSTREAM_TYPES:
        errors.append(f"workstream_type: must be one of {list(WORKSTREAM_TYPES)}")
    for k in ("created_at", "updated_at"):
        v = metadata.get(k)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{k}: required ISO-8601 string")
            continue
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            errors.append(f"{k}: invalid ISO-8601 datetime")
    owners = metadata.get("owners", [])
    if not isinstance(owners, list) or any(not isinstance(o, str) or not o.strip() for o in owners):
        errors.append("owners: must be a list of strings")
    tags = metadata.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(t, str) or not t.strip() for t in tags):
        errors.append("tags: must be a list of strings")
    links = metadata.get("links", [])
    if links is not None:
        if not isinstance(links, list):
            errors.append("links: must be a list")
        else:
            for i, ln in enumerate(links):
                if not isinstance(ln, dict):
                    errors.append(f"links[{i}]: must be an object")
                    continue
                if "label" in ln and (not isinstance(ln["label"], str) or not ln["label"].strip()):
                    errors.append(f"links[{i}].label: must be a non-empty string")
                if "url" in ln and (not isinstance(ln["url"], str) or not ln["url"].strip()):
                    errors.append(f"links[{i}].url: must be a non-empty string")
    return errors


def validate_v1(metadata: Dict[str, Any], *, allow_fallback: bool = True) -> List[str]:
    ok, ext_errors = _try_external_validate(metadata)
    if ok:
        return []
    if allow_fallback:
        fb = _validate_v1_fallback(metadata)
        if not fb:
            return []
    return ext_errors


@dataclass
class Plan:
    cases_root: Path
    case_dir: Path
    metadata_path: Path


def _plan(slug: str, root: Optional[str]) -> Plan:
    cases_root = Path(root).resolve() if root else _default_cases_root().resolve()
    case_dir = cases_root / slug
    metadata_path = case_dir / "metadata.json"
    return Plan(cases_root=cases_root, case_dir=case_dir, metadata_path=metadata_path)


def _scaffold_metadata(slug: str, title: Optional[str], workstream_type: str, summary: Optional[str],
                       owners: List[str], tags: List[str]) -> Dict[str, Any]:
    now = _utc_now_iso()
    return {
        "schema_version": 1,
        "id": slug,
        "title": title or slug.replace("-", " ").title(),
        "workstream_type": workstream_type,
        "summary": summary or "TODO: Add a short summary.",
        "created_at": now,
        "updated_at": now,
        "owners": owners or [],
        "tags": tags or [],
        "links": [],
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m case_studies.add", description="Scaffold a new case study folder and metadata.json.")
    p.add_argument("name", help="Case folder name or title (will be slugified).")
    p.add_argument("--root", help="Case-studies root directory (defaults to ./case-studies or nearest ancestor).")
    p.add_argument("--slug", help="Explicit slug to use as folder name/id.")
    p.add_argument("--title", help="Case title (defaults derived from slug).")
    p.add_argument("--summary", help="Case summary (defaults to a TODO line).")
    p.add_argument("--workstream-type", default="other", choices=list(WORKSTREAM_TYPES))
    p.add_argument("--owner", action="append", default=[], help="Owner (repeatable).")
    p.add_argument("--tag", action="append", default=[], help="Tag (repeatable).")
    p.add_argument("--force", action="store_true", help="Overwrite existing metadata.json if present.")
    p.add_argument("--no-external-schema", action="store_true", help="Do not attempt importing schema_v1; use fallback validator only.")
    args = p.parse_args(argv)

    slug = _slugify(args.slug or args.name)
    plan = _plan(slug, args.root)
    plan.cases_root.mkdir(parents=True, exist_ok=True)
    plan.case_dir.mkdir(parents=True, exist_ok=True)

    if plan.metadata_path.exists() and not args.force:
        print(f"ERROR: {plan.metadata_path} already exists (use --force to overwrite).", file=sys.stderr)
        return 2

    metadata = _scaffold_metadata(slug, args.title, args.workstream_type, args.summary, args.owner, args.tag)
    _write_json(plan.metadata_path, metadata)

    if args.no_external_schema:
        errors = _validate_v1_fallback(metadata)
    else:
        errors = validate_v1(metadata, allow_fallback=True)

    if errors:
        print("ERROR: metadata validation failed:", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        try:
            plan.metadata_path.unlink(missing_ok=True)  # type: ignore[arg-type]
            if not any(plan.case_dir.iterdir()):
                plan.case_dir.rmdir()
        except Exception:
            pass
        return 2

    print(str(plan.case_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
