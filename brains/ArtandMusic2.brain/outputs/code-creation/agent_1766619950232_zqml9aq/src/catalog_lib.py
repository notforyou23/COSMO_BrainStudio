from __future__ import annotations
from pathlib import Path
import json, re, unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None

ROOT_ENV_VAR = "CASE_CATALOG_ROOT"
DEFAULT_CASES_SUBDIR = Path("outputs/catalog/case-studies")
DEFAULT_INDEX_PATH = Path("outputs/catalog/catalog.json")
DEFAULT_CASE_SCHEMA = Path("schemas/case-study.schema.json")
DEFAULT_CATALOG_SCHEMA = Path("schemas/catalog.schema.json")

class CatalogError(RuntimeError): ...
class ValidationError(CatalogError): ...
def project_root(root: Optional[Path] = None) -> Path:
    if root:
        return Path(root).resolve()
    env = __import__("os").environ.get(ROOT_ENV_VAR)
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]

def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "
", encoding="utf-8")
    tmp.replace(path)

def _load_schema(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise CatalogError(f"Schema not found: {path}")
    sch = _read_json(path)
    if not isinstance(sch, dict):
        raise CatalogError(f"Invalid schema JSON (must be object): {path}")
    return sch
_slug_re = re.compile(r"[^a-z0-9]+")
def slugify(text: str, max_len: int = 64) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = _slug_re.sub("-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return (s[:max_len].rstrip("-")) or "case-study"

def generate_case_id(title: str, created: Optional[str] = None) -> str:
    if created:
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    ds = dt.strftime("%Y%m%d")
    return f"{ds}-{slugify(title, 48)}"

def validate(instance: Any, schema_path: Path, root: Optional[Path] = None) -> None:
    r = project_root(root)
    schema = _load_schema(r / schema_path)
    if jsonschema is None:
        raise ValidationError("jsonschema package not available; cannot validate")
    try:
        jsonschema.validate(instance=instance, schema=schema)
    except Exception as e:
        raise ValidationError(str(e)) from e
def paths(root: Optional[Path] = None) -> Tuple[Path, Path, Path, Path]:
    r = project_root(root)
    cases_dir = r / DEFAULT_CASES_SUBDIR
    index_path = r / DEFAULT_INDEX_PATH
    case_schema = r / DEFAULT_CASE_SCHEMA
    catalog_schema = r / DEFAULT_CATALOG_SCHEMA
    return cases_dir, index_path, case_schema, catalog_schema

def load_catalog_index(root: Optional[Path] = None) -> Dict[str, Any]:
    _, index_path, _, _ = paths(root)
    if index_path.exists():
        data = _read_json(index_path)
        if not isinstance(data, dict):
            raise CatalogError("Catalog index JSON must be an object")
        return data
    return {"version": 1, "generated_at": None, "case_studies": []}

def save_catalog_index(index: Dict[str, Any], root: Optional[Path] = None) -> None:
    _, index_path, _, catalog_schema = paths(root)
    index["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    validate(index, catalog_schema.relative_to(project_root(root)))
    _write_json(index_path, index)
def add_case_study(case: Dict[str, Any], root: Optional[Path] = None, overwrite: bool = False) -> Path:
    cases_dir, _, case_schema, _ = paths(root)
    r = project_root(root)
    if not isinstance(case, dict):
        raise CatalogError("Case study must be a JSON object")
    meta = case.get("metadata") or {}
    title = (meta.get("title") or case.get("title") or "").strip()
    if not title:
        raise CatalogError("Case study title is required (metadata.title)")
    created = meta.get("created") or case.get("created")
    cid = (case.get("id") or meta.get("id") or "").strip() or generate_case_id(title, created)
    case["id"] = cid
    case.setdefault("metadata", meta)
    case["metadata"]["title"] = title
    case["metadata"].setdefault("created", created or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    validate(case, case_schema.relative_to(r))
    out_path = cases_dir / f"{cid}.json"
    if out_path.exists() and not overwrite:
        raise CatalogError(f"Case study already exists: {out_path}")
    _write_json(out_path, case)
    index = load_catalog_index(r)
    items = index.setdefault("case_studies", [])
    items = items if isinstance(items, list) else []
    index["case_studies"] = items
    rel = str(out_path.relative_to(r)).replace("\\", "/")
    entry = {"id": cid, "title": title, "path": rel, "tags": case.get("tags", [])}
    items = [e for e in items if isinstance(e, dict) and e.get("id") != cid]
    items.append(entry)
    items.sort(key=lambda e: (e.get("id") or ""))
    index["case_studies"] = items
    save_catalog_index(index, r)
    return out_path

def load_case_study(path: Path) -> Dict[str, Any]:
    data = _read_json(path)
    if not isinstance(data, dict):
        raise CatalogError("Case study JSON must be an object")
    return data
