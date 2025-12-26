from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json
import re
import urllib.request
import urllib.error
import socket


@dataclass
class CheckResult:
    ok: bool
    code: str
    message: str
    details: Dict[str, Any] | None = None


def check_expected_files(base_dir: Path, expected_relpaths: Iterable[str]) -> List[CheckResult]:
    res: List[CheckResult] = []
    for rel in expected_relpaths:
        p = (base_dir / rel).resolve()
        if p.exists():
            res.append(CheckResult(True, "file_present", f"Found: {rel}", {"path": str(p)}))
        else:
            res.append(CheckResult(False, "file_missing", f"Missing: {rel}", {"path": str(p)}))
    return res


def read_text_file(path: Path, encoding: str = "utf-8") -> Tuple[Optional[str], List[CheckResult]]:
    try:
        return path.read_text(encoding=encoding), [CheckResult(True, "read_ok", f"Read: {path.name}", {"path": str(path)})]
    except Exception as e:
        return None, [CheckResult(False, "read_failed", f"Failed to read {path.name}: {e}", {"path": str(path)})]


def parse_json_file(path: Path) -> Tuple[Optional[Any], List[CheckResult]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, [CheckResult(True, "json_parse_ok", f"JSON parsed: {path.name}", {"path": str(path)})]
    except Exception as e:
        return None, [CheckResult(False, "json_parse_failed", f"Invalid JSON in {path.name}: {e}", {"path": str(path)})]


def _type_name(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int) and not isinstance(v, bool):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def validate_json_schema(instance: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    errs: List[str] = []
    if not isinstance(schema, dict):
        return [f"{path}: schema is not an object"]
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: value not in enum")
        return errs
    t = schema.get("type")
    if t is not None:
        allowed = [t] if isinstance(t, str) else list(t) if isinstance(t, list) else []
        if allowed:
            inst_t = _type_name(instance)
            ok = inst_t in allowed or (inst_t == "integer" and "number" in allowed)
            if not ok:
                errs.append(f"{path}: expected type {allowed}, got {inst_t}")
                return errs
    if isinstance(instance, dict):
        req = schema.get("required") or []
        if isinstance(req, list):
            for k in req:
                if k not in instance:
                    errs.append(f"{path}: missing required property '{k}'")
        props = schema.get("properties") or {}
        if isinstance(props, dict):
            for k, subs in props.items():
                if k in instance and isinstance(subs, dict):
                    errs.extend(validate_json_schema(instance[k], subs, f"{path}.{k}"))
        addl = schema.get("additionalProperties", True)
        if addl is False and isinstance(props, dict):
            for k in instance.keys():
                if k not in props:
                    errs.append(f"{path}: additional property '{k}' not allowed")
        if isinstance(addl, dict):
            for k, v in instance.items():
                if not (isinstance(props, dict) and k in props):
                    errs.extend(validate_json_schema(v, addl, f"{path}.{k}"))
    if isinstance(instance, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, v in enumerate(instance):
                errs.extend(validate_json_schema(v, items, f"{path}[{i}]"))
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(instance) < min_items:
            errs.append(f"{path}: expected at least {min_items} items")
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(instance) > max_items:
            errs.append(f"{path}: expected at most {max_items} items")
    if isinstance(instance, str):
        min_len = schema.get("minLength")
        if isinstance(min_len, int) and len(instance) < min_len:
            errs.append(f"{path}: expected minLength {min_len}")
        max_len = schema.get("maxLength")
        if isinstance(max_len, int) and len(instance) > max_len:
            errs.append(f"{path}: expected maxLength {max_len}")
        pat = schema.get("pattern")
        if isinstance(pat, str):
            try:
                if re.search(pat, instance) is None:
                    errs.append(f"{path}: string does not match pattern")
            except re.error:
                errs.append(f"{path}: invalid schema pattern")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        mn = schema.get("minimum")
        if isinstance(mn, (int, float)) and instance < mn:
            errs.append(f"{path}: expected >= {mn}")
        mx = schema.get("maximum")
        if isinstance(mx, (int, float)) and instance > mx:
            errs.append(f"{path}: expected <= {mx}")
    return errs


def validate_json_file_against_schema(json_path: Path, schema: Dict[str, Any]) -> List[CheckResult]:
    data, r = parse_json_file(json_path)
    if data is None:
        return r
    errs = validate_json_schema(data, schema, "$")
    if errs:
        return r + [CheckResult(False, "schema_invalid", f"Schema validation failed: {json_path.name}", {"errors": errs, "path": str(json_path)})]
    return r + [CheckResult(True, "schema_valid", f"Schema valid: {json_path.name}", {"path": str(json_path)})]


_LINK_RE = re.compile(r"\bhttps?://[^\s\])>\"']+", re.IGNORECASE)


def extract_links_from_text(text: str) -> List[str]:
    return sorted(set(_LINK_RE.findall(text or "")))


def linkcheck_urls(urls: Iterable[str], timeout_s: float = 5.0, max_urls: int = 50, enabled: bool = True) -> List[CheckResult]:
    if not enabled:
        return [CheckResult(True, "linkcheck_skipped", "Linkcheck disabled", {"count": 0})]
    out: List[CheckResult] = []
    socket.setdefaulttimeout(timeout_s)
    for i, url in enumerate(list(urls)[: max_urls]):
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "qa-linkcheck"})
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                ok = 200 <= int(status) < 400
                out.append(CheckResult(ok, "link_ok" if ok else "link_bad_status", f"{url} -> {status}", {"url": url, "status": int(status)}))
        except Exception as e:
            out.append(CheckResult(False, "link_failed", f"{url} -> {type(e).__name__}", {"url": url, "error": str(e)}))
    if len(list(urls)) > max_urls:
        out.append(CheckResult(True, "linkcheck_limited", f"Linkcheck limited to {max_urls} URLs", {"max_urls": max_urls}))
    return out


def summarize_results(results: Iterable[CheckResult]) -> Dict[str, Any]:
    results = list(results)
    return {
        "ok": all(r.ok for r in results),
        "counts": {"total": len(results), "ok": sum(1 for r in results if r.ok), "fail": sum(1 for r in results if not r.ok)},
        "results": [r.__dict__ for r in results],
    }
