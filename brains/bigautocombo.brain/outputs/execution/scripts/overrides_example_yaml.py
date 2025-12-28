from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    yaml = None
    _YAML_IMPORT_ERROR = e


ALLOWED_OPS = {"set", "delete", "merge", "append"}


@dataclass(frozen=True)
class OverrideOp:
    op: str
    path: str
    value: Any = None
    note: Optional[str] = None


def build_example_overrides() -> Dict[str, Any]:
    # Intentionally uses a simple, tool-agnostic structure that can be validated and round-tripped.
    ops: List[Dict[str, Any]] = [
        {
            "op": "set",
            "path": "document.title",
            "value": "Example Spec (with overrides)",
            "note": "Demonstrates a scalar set.",
        },
        {
            "op": "merge",
            "path": "document.metadata",
            "value": {"owner": "spec-crosswalk", "version": "2025.12"},
            "note": "Merge a mapping into existing metadata.",
        },
        {
            "op": "append",
            "path": "document.tags",
            "value": ["example", "overrides", "yaml"],
            "note": "Append multiple items to an array.",
        },
        {
            "op": "set",
            "path": "components.schemas.Widget.properties.enabled.default",
            "value": True,
            "note": "Typical deeply-nested path update.",
        },
        {
            "op": "delete",
            "path": "components.schemas.LegacyThing",
            "note": "Remove an obsolete schema definition.",
        },
    ]
    return {"schema_version": 1, "overrides": ops, "source": "scripts/overrides_example_yaml.py"}


def _type_name(x: Any) -> str:
    return type(x).__name__


def validate_overrides_doc(doc: Any) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    if not isinstance(doc, dict):
        return False, [f"document must be a mapping, got {_type_name(doc)}"]

    sv = doc.get("schema_version")
    if sv != 1:
        errs.append(f"schema_version must be 1, got {sv!r}")

    ops = doc.get("overrides")
    if not isinstance(ops, list) or not ops:
        errs.append("overrides must be a non-empty list")
        return False, errs

    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            errs.append(f"overrides[{i}] must be a mapping, got {_type_name(op)}")
            continue
        op_name = op.get("op")
        path = op.get("path")
        if op_name not in ALLOWED_OPS:
            errs.append(f"overrides[{i}].op must be one of {sorted(ALLOWED_OPS)}, got {op_name!r}")
        if not isinstance(path, str) or not path.strip():
            errs.append(f"overrides[{i}].path must be a non-empty string, got {path!r}")

        has_value = "value" in op
        if op_name in {"set", "merge", "append"} and not has_value:
            errs.append(f"overrides[{i}] op={op_name!r} requires a value")
        if op_name == "delete" and has_value:
            errs.append(f"overrides[{i}] op='delete' must not include value")

        if op_name == "merge" and has_value and not isinstance(op.get("value"), dict):
            errs.append(f"overrides[{i}] op='merge' requires mapping value, got {_type_name(op.get('value'))}")
        if op_name == "append" and has_value and not isinstance(op.get("value"), list):
            errs.append(f"overrides[{i}] op='append' requires list value, got {_type_name(op.get('value'))}")

    return not errs, errs


def dump_yaml(doc: Dict[str, Any]) -> str:
    if yaml is None:  # pragma: no cover
        raise RuntimeError(f"PyYAML is required for this example script: {_YAML_IMPORT_ERROR}")  # type: ignore[name-defined]
    return yaml.safe_dump(doc, sort_keys=False, default_flow_style=False, allow_unicode=True)


def load_yaml(text: str) -> Any:
    if yaml is None:  # pragma: no cover
        raise RuntimeError(f"PyYAML is required for this example script: {_YAML_IMPORT_ERROR}")  # type: ignore[name-defined]
    return yaml.safe_load(text)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Generate and validate example overrides YAML.")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output YAML path (default: print to stdout only).",
    )
    args = p.parse_args(argv)

    doc = build_example_overrides()
    ok, errs = validate_overrides_doc(doc)
    if not ok:
        raise SystemExit("Invalid example overrides (pre-dump):\n- " + "\n- ".join(errs))

    text = dump_yaml(doc)
    round_trip = load_yaml(text)
    ok2, errs2 = validate_overrides_doc(round_trip)
    if not ok2:
        raise SystemExit("Invalid example overrides (post-load):\n- " + "\n- ".join(errs2))

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(str(args.out))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
