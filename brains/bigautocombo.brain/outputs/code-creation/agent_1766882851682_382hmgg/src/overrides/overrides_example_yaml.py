"""Generate a canonical example overrides YAML document from the overrides schema.

This module intentionally avoids requiring a YAML emitter that supports comments by
generating a readable YAML string directly.
"""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
from typing import Any, Mapping, Sequence
def _coerce_mapping(obj: Any) -> Mapping[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, Mapping):
        return obj
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return obj.dict()  # type: ignore[no-any-return]
        except TypeError:
            pass
    if hasattr(obj, "__dict__"):
        d = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        if isinstance(d, Mapping):
            return d
    raise TypeError(f"Unsupported schema object type: {type(obj)!r}")
def _quote_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if value == "":
            return "''"
        safe = (
            value.replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("\r", "\\r")
            .replace('"', '\"')
        )
        needs_quotes = any(
            c in value for c in [":", "#", "{", "}", "[", "]", ",", "&", "*", "!", "|", ">", "%", "@", "`"]
        ) or value.strip() != value or value.lower() in {"null", "true", "false", "yes", "no", "on", "off"} or value.startswith(("-", "?", ":", "!", "*", "&"))
        return f'"{safe}"' if needs_quotes else value
    return _quote_scalar(str(value))
def _schema_type(node: Mapping[str, Any]) -> str | None:
    t = node.get("type")
    if isinstance(t, str):
        return t
    if isinstance(t, (list, tuple)) and t:
        return str(t[0])
    return None


def _default_for_schema(node: Mapping[str, Any]) -> Any:
    if "default" in node:
        return node.get("default")
    t = _schema_type(node)
    if t == "object":
        return {}
    if t == "array":
        return []
    if t == "string":
        return ""
    if t == "integer":
        return 0
    if t == "number":
        return 0
    if t == "boolean":
        return False
    return None
def _iter_properties(node: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    props = node.get("properties") or node.get("fields") or node.get("items_by_key")
    if isinstance(props, Mapping):
        out = []
        for k, v in props.items():
            if isinstance(v, Mapping):
                out.append((str(k), v))
            else:
                try:
                    out.append((str(k), _coerce_mapping(v)))
                except Exception:
                    out.append((str(k), {"default": v}))
        out.sort(key=lambda kv: kv[0])
        return out
    return []


def _node_description(node: Mapping[str, Any]) -> str | None:
    for key in ("description", "title", "help", "doc"):
        v = node.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None
def _render_yaml_from_schema(
    node: Mapping[str, Any],
    *,
    indent: int = 0,
    key: str | None = None,
    include_comments: bool = True,
) -> list[str]:
    ind = "  " * indent
    desc = _node_description(node)
    required = node.get("required")
    t = _schema_type(node)

    lines: list[str] = []
    if include_comments and desc:
        for part in desc.splitlines():
            lines.append(f"{ind}# {part}".rstrip())
    if include_comments and required is True and key is not None:
        lines.append(f"{ind}# (required)")

    if key is not None:
        prefix = f"{ind}{key}:"
    else:
        prefix = ind.rstrip()

    if t == "object" or _iter_properties(node):
        props = _iter_properties(node)
        if key is not None and not props:
            lines.append(f"{prefix} {{}}")
            return lines
        if key is not None:
            lines.append(prefix)
        for k, child in props:
            lines.extend(
                _render_yaml_from_schema(
                    child,
                    indent=indent + (1 if key is not None else 0),
                    key=k,
                    include_comments=include_comments,
                )
            )
        if key is None and not props:
            lines.append("{}")
        return lines

    if t == "array":
        item = node.get("items")
        if item is None:
            ex = _default_for_schema(node)
            if key is None:
                lines.append(_quote_scalar(ex))
            else:
                lines.append(f"{prefix} []")
            return lines
        try:
            item_node = _coerce_mapping(item)
        except Exception:
            item_node = {"default": item}
        if key is None:
            lines.append("- " + _quote_scalar(_default_for_schema(item_node)))
            return lines
        lines.append(prefix)
        child_lines = _render_yaml_from_schema(item_node, indent=indent + 1, key=None, include_comments=include_comments)
        if child_lines:
            first = child_lines[0]
            rest = child_lines[1:]
            if first.strip().startswith("#"):
                lines.extend(child_lines)
            else:
                lines.append(("  " * (indent + 1)) + "- " + first.strip())
                for r in rest:
                    lines.append(("  " * (indent + 2)) + r.strip())
        else:
            lines.append(("  " * (indent + 1)) + "- null")
        return lines

    ex = _default_for_schema(node)
    if key is None:
        lines.append(_quote_scalar(ex))
    else:
        lines.append(f"{prefix} {_quote_scalar(ex)}")
    return lines
def get_overrides_schema() -> Mapping[str, Any]:
    """Load the overrides schema from src.overrides.schema with a tolerant API surface."""
    from . import schema as schema_mod  # type: ignore

    for attr in ("OVERRIDES_SCHEMA", "OVERRIDE_SCHEMA", "SCHEMA", "schema"):
        if hasattr(schema_mod, attr):
            candidate = getattr(schema_mod, attr)
            if callable(candidate):
                try:
                    return _coerce_mapping(candidate())
                except TypeError:
                    pass
            try:
                return _coerce_mapping(candidate)
            except Exception:
                continue

    for fn in ("get_overrides_schema", "get_schema", "overrides_schema"):
        if hasattr(schema_mod, fn) and callable(getattr(schema_mod, fn)):
            return _coerce_mapping(getattr(schema_mod, fn)())

    raise AttributeError("Could not locate overrides schema in src.overrides.schema")
def generate_example_overrides_yaml(*, include_comments: bool = True) -> str:
    """Return a canonical example overrides YAML document with defaults and comments."""
    schema = get_overrides_schema()
    lines = [
        "# Example overrides file",
        "#",
        "# This document is generated from the overrides schema to show supported keys,",
        "# expected shapes, and default/example values.",
        "",
    ]
    body = _render_yaml_from_schema(schema, indent=0, key=None, include_comments=include_comments)
    lines.extend(body)
    if not lines or lines[-1].strip():
        lines.append("")
    return "\n".join(lines)


def write_example_overrides_yaml(path: str) -> None:
    from pathlib import Path

    Path(path).write_text(generate_example_overrides_yaml(), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import sys

    p = argparse.ArgumentParser(description="Generate an example overrides YAML document from the schema.")
    p.add_argument("-o", "--out", help="Write to a file instead of stdout.")
    p.add_argument("--no-comments", action="store_true", help="Omit comment lines.")
    args = p.parse_args(list(argv) if argv is not None else None)

    text = generate_example_overrides_yaml(include_comments=not args.no_comments)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
