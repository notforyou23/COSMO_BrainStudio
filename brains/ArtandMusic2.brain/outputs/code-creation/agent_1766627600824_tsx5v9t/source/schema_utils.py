from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union
import json

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    from jsonschema import Draft202012Validator
except Exception as e:  # pragma: no cover
    raise ImportError("jsonschema is required for validation utilities") from e


Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    message: str
    hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"code": self.code, "path": self.path, "message": self.message}
        if self.hint:
            d["hint"] = self.hint
        return d


def _path_str(path_parts: Sequence[Any]) -> str:
    if not path_parts:
        return "$"
    out = "$"
    for p in path_parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            s = str(p)
            out += f".{s}" if s and s.isidentifier() else f"['{s}']"
    return out


def load_text(path: Union[str, Path], encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)


def load_json_or_yaml(path: Union[str, Path]) -> Json:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML not installed; cannot parse YAML")
        return yaml.safe_load(text)
    if suffix == ".json":
        return json.loads(text)
    # best-effort: try json then yaml
    try:
        return json.loads(text)
    except Exception:
        if yaml is None:
            raise ValueError(f"Unknown/unsupported file type: {p.name}")
        return yaml.safe_load(text)


def load_schema(schema_path: Union[str, Path]) -> Dict[str, Any]:
    obj = load_json_or_yaml(schema_path)
    if not isinstance(obj, dict):
        raise ValueError("Schema must be a JSON object")
    return obj
def iter_schema_errors(instance: Any, schema: Dict[str, Any]) -> List[Issue]:
    v = Draft202012Validator(schema)
    issues: List[Issue] = []
    for e in sorted(v.iter_errors(instance), key=lambda x: list(x.path)):
        loc = _path_str(list(e.path))
        msg = e.message
        hint = None
        if e.validator in {"required", "dependentRequired"} and isinstance(e.validator_value, (list, dict)):
            hint = "Add the missing required field(s) at this location."
        elif e.validator == "anyOf":
            hint = "Provide one of the acceptable alternative field sets (see schema anyOf)."
        elif e.validator == "oneOf":
            hint = "Provide exactly one of the acceptable alternative field sets (see schema oneOf)."
        issues.append(Issue(code=f"schema.{e.validator}", path=loc, message=msg, hint=hint))
    return issues


def format_issues(issues: Sequence[Issue], max_issues: int = 50) -> str:
    if not issues:
        return "OK"
    lines = []
    for i, iss in enumerate(issues[:max_issues], start=1):
        line = f"{i}. [{iss.code}] {iss.path}: {iss.message}"
        if iss.hint:
            line += f" Hint: {iss.hint}"
        lines.append(line)
    if len(issues) > max_issues:
        lines.append(f"... and {len(issues) - max_issues} more issue(s).")
    return "\n".join(lines)
def _get(d: Any, *keys: str) -> Any:
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _nonempty_list(x: Any) -> bool:
    return isinstance(x, list) and any((isinstance(i, str) and i.strip()) or isinstance(i, dict) for i in x)


def check_anchor_rules(claim_card: Dict[str, Any]) -> List[Issue]:
    issues: List[Issue] = []

    # (a) verbatim claim text
    claim_text = _get(claim_card, "claim", "text")
    if not _nonempty_str(claim_text):
        issues.append(Issue(
            code="anchor.missing_claim_text",
            path="$.claim.text",
            message="Missing required verbatim claim text.",
            hint="Provide the exact claim wording as it appears in the source (verbatim).",
        ))

    # (c) context metadata (who/when/where)
    ctx = _get(claim_card, "context")
    for k in ("who", "when", "where"):
        if not _nonempty_str(_get(ctx, k)):
            issues.append(Issue(
                code="anchor.missing_context",
                path=f"$.context.{k}",
                message=f"Missing required context field: {k}.",
                hint="Provide who made the claim, when it was made/published, and where (venue/platform/document).",
            ))

    # (b) dataset name + DOI/link OR fallback research area + >=2 seed papers/authors
    ds = _get(claim_card, "dataset")
    ds_name = _get(ds, "name")
    ds_doi = _get(ds, "doi")
    ds_link = _get(ds, "link") or _get(ds, "url")
    has_dataset_anchor = _nonempty_str(ds_name) and (_nonempty_str(ds_doi) or _nonempty_str(ds_link))

    fb = _get(claim_card, "fallback") or {}
    area = _get(fb, "research_area")
    seeds = _get(fb, "seed_papers") or _get(fb, "seed_authors")
    has_fallback = _nonempty_str(area) and isinstance(seeds, list) and len([s for s in seeds if (isinstance(s, str) and s.strip()) or isinstance(s, dict)]) >= 2

    if not has_dataset_anchor and not has_fallback:
        issues.append(Issue(
            code="anchor.missing_dataset_or_fallback",
            path="$",
            message="Missing dataset/provenance anchor: require dataset.name + (dataset.doi or dataset.link), OR fallback.research_area + >=2 seed papers/authors.",
            hint="Add dataset metadata with a DOI/link, or provide a research area and at least two seed papers/authors.",
        ))

    # dataset name present but no DOI/link should hard-fail
    if _nonempty_str(ds_name) and not (_nonempty_str(ds_doi) or _nonempty_str(ds_link)):
        issues.append(Issue(
            code="anchor.dataset_missing_doi_or_link",
            path="$.dataset",
            message="Dataset name provided but missing DOI/link.",
            hint="Provide dataset.doi or dataset.link (URL) for provenance anchoring.",
        ))

    # fallback present but insufficient seeds
    if _nonempty_str(area) and not has_fallback:
        issues.append(Issue(
            code="anchor.fallback_insufficient_seeds",
            path="$.fallback",
            message="Fallback research area provided but missing >=2 seed papers/authors.",
            hint="Provide at least two seed papers (citations/DOIs/links) or author names to bootstrap dataset discovery.",
        ))

    return issues


def validate_claim_card(
    claim_card: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
    *,
    enforce_anchor_rules: bool = True,
) -> List[Issue]:
    issues: List[Issue] = []
    if schema is not None:
        issues.extend(iter_schema_errors(claim_card, schema))
    if enforce_anchor_rules:
        issues.extend(check_anchor_rules(claim_card))
    return issues
