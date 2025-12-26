from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_DATE_RANGE = {"start": "2019-01-01", "end": "2025-12-31"}


@dataclass(frozen=True)
class BlockingIssue:
    code: str
    path: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _is_blank(s: Any) -> bool:
    return s is None or (isinstance(s, str) and not s.strip())


def _get_in(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def normalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(task, dict):
        raise TypeError("task must be a JSON object")
    out = json.loads(json.dumps(task))  # deep copy, JSON-compatible

    if isinstance(out.get("claim"), str):
        out["claim"] = out["claim"].strip()

    doi = out.get("doi")
    if _is_blank(doi):
        if not isinstance(out.get("date_range"), dict):
            out["date_range"] = dict(DEFAULT_DATE_RANGE)
        else:
            out["date_range"].setdefault("start", DEFAULT_DATE_RANGE["start"])
            out["date_range"].setdefault("end", DEFAULT_DATE_RANGE["end"])

        q = out.get("query")
        if not isinstance(q, dict):
            q = {}
            out["query"] = q

        if isinstance(q.get("keywords"), str):
            q["keywords"] = [k.strip() for k in q["keywords"].split(",") if k.strip()]
        if isinstance(q.get("authors"), str):
            q["authors"] = [a.strip() for a in q["authors"].split(",") if a.strip()]

    return out


def _validate_checklist(task: Dict[str, Any]) -> List[BlockingIssue]:
    issues: List[BlockingIssue] = []

    if _is_blank(task.get("claim")):
        issues.append(BlockingIssue("MISSING_CLAIM", "claim", "Missing verbatim claim (exact text to verify)."))

    src_ctx = task.get("source_context")
    if src_ctx is None or (isinstance(src_ctx, str) and not src_ctx.strip()) or (isinstance(src_ctx, dict) and not src_ctx):
        issues.append(BlockingIssue("MISSING_SOURCE_CONTEXT", "source_context", "Missing source context (who/when/where + excerpt/link)."))

    prov = task.get("provenance_anchor")
    if prov is None or (isinstance(prov, str) and not prov.strip()) or (isinstance(prov, dict) and not prov):
        issues.append(BlockingIssue("MISSING_PROVENANCE_ANCHOR", "provenance_anchor", "Missing provenance anchor (stable ID, URL, or citation anchor)."))

    doi = task.get("doi")
    if _is_blank(doi):
        dr = task.get("date_range")
        start = dr.get("start") if isinstance(dr, dict) else None
        end = dr.get("end") if isinstance(dr, dict) else None
        if _is_blank(start) or _is_blank(end):
            issues.append(BlockingIssue("MISSING_DATE_RANGE", "date_range", "Missing date_range; default is 2019–2025 when DOI is absent."))
        q = task.get("query")
        kw = _get_in(task, "query.keywords")
        au = _get_in(task, "query.authors")
        if not isinstance(q, dict):
            issues.append(BlockingIssue("MISSING_QUERY", "query", "Missing query object; required when DOI is absent."))
        if not (isinstance(kw, list) and any(isinstance(x, str) and x.strip() for x in kw)):
            issues.append(BlockingIssue("MISSING_QUERY_KEYWORDS", "query.keywords", "Missing query.keywords; required when DOI is absent."))
        if not (isinstance(au, list) and any(isinstance(x, str) and x.strip() for x in au)):
            issues.append(BlockingIssue("MISSING_QUERY_AUTHORS", "query.authors", "Missing query.authors; required when DOI is absent."))

    return issues


def validate_task(task: Dict[str, Any], *, use_schema: bool = True) -> Tuple[Dict[str, Any], List[BlockingIssue]]:
    normalized = normalize_task(task)
    issues = _validate_checklist(normalized)

    if use_schema:
        schema = normalized.get("$schema_task_intake")
        if isinstance(schema, dict):
            try:
                import jsonschema  # type: ignore

                jsonschema.Draft202012Validator(schema).validate(normalized)
            except Exception as e:
                issues.append(BlockingIssue("SCHEMA_VALIDATION_FAILED", "$", f"Schema validation failed: {e}"))

    return normalized, issues


def _read_input_json(path: Optional[str]) -> Any:
    if path and path != "-":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(sys.stdin)


def _main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="validate_task", description="Normalize then validate an intake task (blocking checklist + optional schema).")
    ap.add_argument("infile", nargs="?", default="-", help="Input JSON file path, or '-' for stdin.")
    ap.add_argument("--no-schema", action="store_true", help="Skip optional embedded schema validation.")
    ap.add_argument("--print-normalized", action="store_true", help="Print normalized task JSON on success.")
    args = ap.parse_args(argv)

    try:
        payload = _read_input_json(args.infile)
        if not isinstance(payload, dict):
            raise TypeError("input must be a JSON object")
        normalized, issues = validate_task(payload, use_schema=not args.no_schema)
    except Exception as e:
        err = {"ok": False, "issues": [BlockingIssue("INVALID_INPUT", "$", str(e)).to_dict()]}
        print(json.dumps(err, ensure_ascii=False, indent=2))
        return 2

    if issues:
        out = {"ok": False, "issues": [i.to_dict() for i in issues]}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1

    if args.print_normalized:
        print(json.dumps({"ok": True, "task": normalized}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"ok": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
