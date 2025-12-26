from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json
import re
from datetime import date


_SLUG_RE = re.compile(r"[^a-z0-9]+")
_WS_RE = re.compile(r"\s+")


def slugify(text: str) -> str:
    s = (text or "").strip().lower()
    s = _WS_RE.sub(" ", s)
    s = _SLUG_RE.sub("-", s).strip("-")
    return s or "case-study"


def _yaml_dumps(data: Dict[str, Any]) -> str:
    try:
        import yaml  # type: ignore
    except Exception:
        return ""
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip() + "\n"


def _json_dumps(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2).strip() + "\n"


def normalize_case_study_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(meta, dict):
        raise TypeError("metadata must be a dict")
    out = dict(meta)
    out.setdefault("type", "case_study")
    if "id" not in out or not str(out["id"]).strip():
        basis = out.get("slug") or out.get("title") or "case-study"
        out["id"] = slugify(str(basis))
    out["id"] = slugify(str(out["id"]))
    out.setdefault("title", out["id"].replace("-", " ").title())
    out.setdefault("created", str(date.today()))
    if "slug" not in out or not str(out["slug"]).strip():
        out["slug"] = out["id"]
    out["slug"] = slugify(str(out["slug"]))
    return out


@dataclass(frozen=True)
class CaseStudyScaffold:
    outputs_root: Path

    def case_studies_dir(self) -> Path:
        return self.outputs_root / "outputs" / "case_studies"

    def paths_for(self, case_id_or_slug: str, fmt: str = "yaml") -> Tuple[Path, Path]:
        slug = slugify(case_id_or_slug)
        ext = "yaml" if fmt.lower() in ("yaml", "yml") else "json"
        base = self.case_studies_dir() / slug
        return base.with_suffix(f".{ext}"), base.with_suffix(".md")

    def render_markdown_stub(
        self,
        meta: Dict[str, Any],
        metadata_rel_path: Optional[str] = None,
        include_front_matter: bool = True,
    ) -> str:
        m = normalize_case_study_metadata(meta)
        title = str(m.get("title") or m["id"])
        fm = ""
        if include_front_matter:
            fm_obj = {
                "artifact_type": "case_study",
                "id": m["id"],
                "title": title,
            }
            if metadata_rel_path:
                fm_obj["metadata"] = metadata_rel_path
            y = _yaml_dumps(fm_obj)
            if y:
                fm = f"---\n{y}---\n\n"
        return (
            f"{fm}# {title}\n\n"
            "## Summary\n\n"
            "## Context\n\n"
            "## Approach\n\n"
            "## Outcomes\n\n"
            "## Artifacts\n\n"
            "## Notes\n"
        )

    def write_case_study(
        self,
        meta: Dict[str, Any],
        fmt: str = "yaml",
        body_markdown: Optional[str] = None,
        include_front_matter: bool = True,
        overwrite: bool = False,
    ) -> Tuple[Path, Path]:
        m = normalize_case_study_metadata(meta)
        md_path, doc_path = self.paths_for(m["slug"], fmt=fmt)[1], self.paths_for(m["slug"], fmt=fmt)[0]
        out_dir = self.case_studies_dir()
        out_dir.mkdir(parents=True, exist_ok=True)

        if not overwrite and (doc_path.exists() or md_path.exists()):
            raise FileExistsError(f"case study already exists: {doc_path.name} and/or {md_path.name}")

        if fmt.lower() in ("yaml", "yml"):
            text = _yaml_dumps(m)
            if not text:
                text = _json_dumps(m)
                doc_path = doc_path.with_suffix(".json")
        else:
            text = _json_dumps(m)

        doc_path.write_text(text, encoding="utf-8")

        rel = str(doc_path.relative_to(self.outputs_root)).replace("\\", "/") if self.outputs_root in doc_path.parents else doc_path.name
        md_text = body_markdown if (body_markdown is not None) else self.render_markdown_stub(m, metadata_rel_path=rel, include_front_matter=include_front_matter)
        md_path.write_text(md_text.rstrip() + "\n", encoding="utf-8")
        return doc_path, md_path
