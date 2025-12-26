"""Single blessed CLI for case study metadata scaffolding/validation/reporting."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None


def _default_schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "schemas" / "METADATA_SCHEMA.json"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema(schema_path: Path | None) -> dict:
    p = Path(schema_path) if schema_path else _default_schema_path()
    if not p.exists():
        raise FileNotFoundError(f"Schema not found: {p}")
    schema = _load_json(p)
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a JSON object")
    return schema


def _type_default(t) -> object:
    if isinstance(t, list):
        for v in t:
            if v != "null":
                return _type_default(v)
        return None
    if t == "string":
        return ""
    if t == "array":
        return []
    if t == "object":
        return {}
    if t == "number":
        return 0
    if t == "integer":
        return 0
    if t == "boolean":
        return False
    return None


def scaffold(out_path: Path, schema_path: Path | None) -> int:
    schema = _load_schema(schema_path)
    props = (schema.get("properties") or {}) if isinstance(schema, dict) else {}
    req = schema.get("required") or []
    data = {}
    if isinstance(props, dict) and props:
        for k, v in props.items():
            if isinstance(v, dict) and "default" in v:
                data[k] = v["default"]
            elif isinstance(v, dict) and "type" in v:
                data[k] = _type_default(v.get("type"))
            else:
                data[k] = None
        for k in req if isinstance(req, list) else []:
            data.setdefault(k, "")

    if not data:
        data = {"case_study_id": "", "title": "", "summary": "", "tags": [], "authors": [], "created": ""}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"SCAFFOLDED:{out_path}")
    return 0


def _format_error(e) -> str:
    path = "/".join(str(p) for p in getattr(e, "absolute_path", []) or [])
    loc = f" at {path}" if path else ""
    rule = f" [{e.validator}]" if getattr(e, "validator", None) else ""
    return f"{e.message}{loc}{rule}"


def validate(metadata_path: Path, schema_path: Path | None, *, quiet: bool = False) -> tuple[int, list[str], dict]:
    schema = _load_schema(schema_path)
    inst = _load_json(metadata_path)
    errors: list[str] = []
    if jsonschema is None:
        errors.append("jsonschema is not installed; cannot validate")
    else:
        try:
            v = jsonschema.Draft202012Validator(schema)  # type: ignore[attr-defined]
        except Exception:
            v = jsonschema.Draft7Validator(schema)  # type: ignore
        for e in sorted(v.iter_errors(inst), key=lambda x: (list(getattr(x, "absolute_path", [])), x.message)):
            errors.append(_format_error(e))

    ok = 0 if not errors else 1
    if not quiet:
        status = "OK" if ok == 0 else "FAIL"
        print(f"VALIDATE:{status}:{metadata_path}")
        if errors:
            for msg in errors:
                print(f"ERROR:{msg}")
    return ok, errors, schema


def report(metadata_path: Path, schema_path: Path | None) -> int:
    code, errors, schema = validate(metadata_path, schema_path, quiet=True)
    inst = _load_json(metadata_path)
    sid = schema.get("$id") or schema.get("id") or ""
    title = schema.get("title") or ""
    keys = sorted(inst.keys()) if isinstance(inst, dict) else []
    print(f"REPORT:metadata={metadata_path}")
    print(f"REPORT:schema={schema_path or _default_schema_path()}")
    if sid:
        print(f"REPORT:schema_id={sid}")
    if title:
        print(f"REPORT:schema_title={title}")
    print(f"REPORT:top_level_keys={len(keys)}")
    if keys:
        print("REPORT:keys=" + ",".join(keys))
    print(f"REPORT:errors={len(errors)}")
    if errors:
        for msg in errors[:50]:
            print(f"ERROR:{msg}")
        if len(errors) > 50:
            print(f"ERROR:... and {len(errors)-50} more")
    print("REPORT:status=" + ("OK" if code == 0 else "FAIL"))
    return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="metadata_cli", description="Scaffold/validate/report case study metadata JSON.")
    ap.add_argument("--schema", type=Path, default=None, help="Path to METADATA_SCHEMA.json (defaults to ./schemas/METADATA_SCHEMA.json)")
    sp = ap.add_subparsers(dest="cmd", required=True)

    a = sp.add_parser("scaffold", help="Write a starter metadata JSON file.")
    a.add_argument("out", type=Path, help="Output JSON path to write.")

    a = sp.add_parser("validate", help="Validate a metadata JSON file against the schema.")
    a.add_argument("metadata", type=Path, help="Metadata JSON path to validate.")

    a = sp.add_parser("report", help="Validate and print a compact report.")
    a.add_argument("metadata", type=Path, help="Metadata JSON path to report on.")

    ns = ap.parse_args(argv)
    if ns.cmd == "scaffold":
        return scaffold(ns.out, ns.schema)
    if ns.cmd == "validate":
        return validate(ns.metadata, ns.schema)[0]
    if ns.cmd == "report":
        return report(ns.metadata, ns.schema)
    ap.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
