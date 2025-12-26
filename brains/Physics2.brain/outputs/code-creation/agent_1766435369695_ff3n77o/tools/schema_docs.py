#!/usr/bin/env python3
"""schema_docs.py

CLI to:
1) Generate Markdown documentation from a JSON Schema file.
2) Optionally infer a schema *stub* from JSON examples embedded in a Markdown doc.

Designed to keep schema and docs in sync without external dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
def _json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _type_str(schema: Dict[str, Any]) -> str:
    t = schema.get("type")
    if isinstance(t, list):
        return " | ".join(map(str, t))
    if isinstance(t, str):
        return t
    if "enum" in schema:
        return "enum"
    if "$ref" in schema:
        return f"ref({schema['$ref']})"
    return "any"


def _md_escape(s: str) -> str:
    return s.replace("|", r"\|").replace("\n", " ").strip()
def _collect_props(schema: Dict[str, Any], prefix: str = "") -> List[Tuple[str, Dict[str, Any], bool]]:
    out: List[Tuple[str, Dict[str, Any], bool]] = []
    if schema.get("type") != "object":
        return out
    props = schema.get("properties", {}) or {}
    req = set(schema.get("required", []) or [])
    for k, v in sorted(props.items()):
        path = f"{prefix}.{k}" if prefix else k
        out.append((path, v, k in req))
        out.extend(_collect_props(v, path))
    return out


def schema_to_markdown(schema: Dict[str, Any], schema_path: Path) -> str:
    title = schema.get("title") or schema_path.stem
    desc = schema.get("description", "")
    lines = [f"# {title}", ""]
    if desc:
        lines += [desc.strip(), ""]
    lines += ["## Overview", ""]
    lines += [f"- **$schema**: `{schema.get('$schema','')}`" if schema.get("$schema") else "- **$schema**: (not set)"]
    if "$id" in schema:
        lines += [f"- **$id**: `{schema['$id']}`"]
    lines += [f"- **Root type**: `{_type_str(schema)}`", ""]
    if schema.get("type") == "object":
        lines += ["## Fields", ""]
        lines += ["| Field | Type | Required | Description |", "|---|---|:---:|---|"]
        for path, subs, is_req in _collect_props(schema):
            d = subs.get("description", "")
            lines.append(f"| `{path}` | `{_type_str(subs)}` | {'yes' if is_req else 'no'} | {_md_escape(d)} |")
        lines.append("")
    examples = schema.get("examples") or []
    if examples:
        lines += ["## Examples", ""]
        for ex in examples:
            lines += ["```json", json.dumps(ex, indent=2, sort_keys=True), "```", ""]
    lines += ["## Notes", "", "This document is generated from JSON Schema. To keep docs and schema aligned, prefer adding examples and descriptions in the schema itself.", ""]
    return "\n".join(lines).rstrip() + "\n"
_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL | re.IGNORECASE)


def extract_json_examples_from_markdown(md_text: str) -> List[Any]:
    out: List[Any] = []
    for m in _JSON_BLOCK_RE.finditer(md_text):
        block = m.group(1).strip()
        out.append(json.loads(block))
    return out


def _merge_types(a: Any, b: Any) -> Any:
    if a == b:
        return a
    ta = a if isinstance(a, list) else [a]
    tb = b if isinstance(b, list) else [b]
    merged = []
    for t in ta + tb:
        if t not in merged:
            merged.append(t)
    return merged if len(merged) > 1 else merged[0]
def infer_schema_stub(value: Any) -> Dict[str, Any]:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}}
        item = infer_schema_stub(value[0])
        for v in value[1:]:
            item_t = item.get("type", "any")
            vt = infer_schema_stub(v).get("type", "any")
            item["type"] = _merge_types(item_t, vt)
        return {"type": "array", "items": item}
    if isinstance(value, dict):
        props: Dict[str, Any] = {}
        req: List[str] = []
        for k, v in value.items():
            props[k] = infer_schema_stub(v)
            req.append(k)
        return {"type": "object", "properties": props, "required": sorted(req), "additionalProperties": True}
    return {}
def examples_to_schema_stub(examples: List[Any], title: str = "Inferred Schema Stub") -> Dict[str, Any]:
    if not examples:
        raise SystemExit("No JSON examples found to infer a schema stub.")
    root = infer_schema_stub(examples[0])
    for ex in examples[1:]:
        t = root.get("type", "any")
        et = infer_schema_stub(ex).get("type", "any")
        root["type"] = _merge_types(t, et)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": title, **root, "examples": examples}


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate Markdown docs from JSON Schema; optionally infer schema stubs from JSON examples in Markdown.")
    ap.add_argument("--schema", type=Path, help="Path to schema.json (for docs generation).")
    ap.add_argument("--out", type=Path, help="Output Markdown path (for docs generation). Use '-' for stdout.")
    ap.add_argument("--from-markdown", type=Path, help="Path to Markdown doc to extract ```json``` examples from.")
    ap.add_argument("--stub-out", type=Path, help="Write inferred schema stub JSON to this path (or '-' for stdout).")
    ap.add_argument("--title", default="Inferred Schema Stub", help="Title used when writing inferred schema stubs.")
    args = ap.parse_args(argv)

    did = False
    if args.schema and args.out:
        schema = _json_load(args.schema)
        md = schema_to_markdown(schema, args.schema)
        if str(args.out) == "-":
            print(md, end="")
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(md, encoding="utf-8")
        did = True

    if args.from_markdown and args.stub_out:
        md_text = args.from_markdown.read_text(encoding="utf-8")
        examples = extract_json_examples_from_markdown(md_text)
        stub = examples_to_schema_stub(examples, title=args.title)
        text = json.dumps(stub, indent=2, sort_keys=True) + "\n"
        if str(args.stub_out) == "-":
            print(text, end="")
        else:
            args.stub_out.parent.mkdir(parents=True, exist_ok=True)
            args.stub_out.write_text(text, encoding="utf-8")
        did = True

    if not did:
        ap.error("Nothing to do. Provide --schema/--out and/or --from-markdown/--stub-out.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
