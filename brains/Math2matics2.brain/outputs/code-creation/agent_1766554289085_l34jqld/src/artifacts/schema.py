from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import re

SCHEMA_VERSION = "1.0"

RESULTS_TOP_LEVEL_REQUIRED = ("schema_version", "metadata", "metrics", "artifacts")
RESULTS_TOP_LEVEL_OPTIONAL = ("notes",)

METADATA_REQUIRED = ("run_id", "created_utc", "start_utc", "end_utc", "seed", "git")
METADATA_OPTIONAL = ("command", "cwd", "python", "platform", "env", "tags")

GIT_REQUIRED = ("commit", "is_dirty")
GIT_OPTIONAL = ("branch", "repo_root")

ARTIFACTS_REQUIRED = ("figures", "files")
ARTIFACTS_OPTIONAL = ("tables",)

FIGURE_EXTENSIONS = ("png", "pdf", "svg", "jpg", "jpeg", "webp")

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_UTC_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class SchemaError(ValueError):
    pass


def _is_mapping(x: Any) -> bool:
    return isinstance(x, Mapping)


def _is_sequence(x: Any) -> bool:
    return isinstance(x, Sequence) and not isinstance(x, (str, bytes, bytearray))


def _require_keys(obj: Mapping[str, Any], keys: Iterable[str], path: str, errors: List[str]) -> None:
    for k in keys:
        if k not in obj:
            errors.append(f"{path}: missing key '{k}'")


def _type_check(cond: bool, msg: str, errors: List[str]) -> None:
    if not cond:
        errors.append(msg)


def is_utc_iso8601(s: Any) -> bool:
    return isinstance(s, str) and bool(_UTC_ISO_RE.match(s))
def slugify(text: str, max_len: int = 64) -> str:
    if not isinstance(text, str):
        text = str(text)
    t = text.strip().lower()
    t = _SLUG_RE.sub("-", t).strip("-")
    if not t:
        t = "item"
    return t[:max_len]


def make_figure_name(stem: str, index: int, ext: str = "png") -> str:
    """Deterministic figure name: fig_{index:03d}_{slug}.{ext}"""
    _type_err = []
    _type_check(isinstance(index, int) and index >= 0, "index must be a non-negative int", _type_err)
    _type_check(isinstance(ext, str) and ext.lower() in FIGURE_EXTENSIONS, "ext must be a supported image extension", _type_err)
    if _type_err:
        raise SchemaError("; ".join(_type_err))
    return f"fig_{index:03d}_{slugify(stem)}.{ext.lower()}"


def make_file_name(stem: str, ext: str, index: Optional[int] = None) -> str:
    """Deterministic file name: file_{index:03d}_{slug}.{ext} or file_{slug}.{ext}"""
    if not isinstance(ext, str) or not ext:
        raise SchemaError("ext must be a non-empty string")
    ext = ext.lstrip(".").lower()
    if index is None:
        return f"file_{slugify(stem)}.{ext}"
    if not isinstance(index, int) or index < 0:
        raise SchemaError("index must be a non-negative int")
    return f"file_{index:03d}_{slugify(stem)}.{ext}"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: Tuple[str, ...]

    def raise_for_errors(self) -> None:
        if not self.ok:
            raise SchemaError("Schema validation failed:\n- " + "\n- ".join(self.errors))


def validate_results_dict(d: Any) -> ValidationResult:
    """Validate a results.json-like object; returns errors without mutating input."""
    errors: List[str] = []
    _type_check(_is_mapping(d), "results must be an object/dict", errors)
    if errors:
        return ValidationResult(False, tuple(errors))
    assert isinstance(d, Mapping)

    _require_keys(d, RESULTS_TOP_LEVEL_REQUIRED, "results", errors)
    _type_check(d.get("schema_version") == SCHEMA_VERSION, f"results.schema_version must be '{SCHEMA_VERSION}'", errors)

    md = d.get("metadata")
    _type_check(_is_mapping(md), "results.metadata must be an object/dict", errors)
    if _is_mapping(md):
        _require_keys(md, METADATA_REQUIRED, "results.metadata", errors)
        git = md.get("git")
        _type_check(_is_mapping(git), "results.metadata.git must be an object/dict", errors)
        if _is_mapping(git):
            _require_keys(git, GIT_REQUIRED, "results.metadata.git", errors)
            if "commit" in git:
                _type_check(isinstance(git["commit"], str) and len(git["commit"]) >= 7, "results.metadata.git.commit must be a string (>=7 chars)", errors)
            if "is_dirty" in git:
                _type_check(isinstance(git["is_dirty"], bool), "results.metadata.git.is_dirty must be bool", errors)

        for k in ("created_utc", "start_utc", "end_utc"):
            if k in md:
                _type_check(is_utc_iso8601(md[k]), f"results.metadata.{k} must be UTC ISO8601 like 'YYYY-MM-DDTHH:MM:SS(.sss)Z'", errors)
        if "seed" in md:
            _type_check(isinstance(md["seed"], int) and md["seed"] >= 0, "results.metadata.seed must be a non-negative int", errors)
        if "run_id" in md:
            _type_check(isinstance(md["run_id"], str) and md["run_id"].strip() != "", "results.metadata.run_id must be a non-empty string", errors)

    metrics = d.get("metrics")
    _type_check(_is_mapping(metrics), "results.metrics must be an object/dict", errors)

    arts = d.get("artifacts")
    _type_check(_is_mapping(arts), "results.artifacts must be an object/dict", errors)
    if _is_mapping(arts):
        _require_keys(arts, ARTIFACTS_REQUIRED, "results.artifacts", errors)
        for k in ("figures", "files", "tables"):
            if k in arts:
                _type_check(isinstance(arts[k], list), f"results.artifacts.{k} must be a list", errors)
                if isinstance(arts[k], list):
                    for i, item in enumerate(arts[k]):
                        _type_check(_is_mapping(item), f"results.artifacts.{k}[{i}] must be an object/dict", errors)
                        if _is_mapping(item):
                            _type_check(isinstance(item.get("path"), str) and item.get("path", "").strip() != "", f"results.artifacts.{k}[{i}].path must be a non-empty string", errors)

    return ValidationResult(len(errors) == 0, tuple(errors))


def ensure_valid_results_dict(d: Any) -> Dict[str, Any]:
    vr = validate_results_dict(d)
    vr.raise_for_errors()
    return dict(d)  # type: ignore[arg-type]
