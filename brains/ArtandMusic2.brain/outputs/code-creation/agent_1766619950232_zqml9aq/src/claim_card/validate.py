from __future__ import annotations
import argparse, json, sys, re
from pathlib import Path
from datetime import datetime

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None


def _emit(logs, kind, level, message, path=None, pointer=None, details=None):
    logs.append({
        "kind": kind,
        "level": level,
        "message": message,
        "path": str(path) if path else None,
        "pointer": pointer,
        "details": details or {},
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    })


def _load_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _parse_md_front_matter(text: str):
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if not m:
        return None, {"missing_front_matter": True}
    raw = m.group(1)
    if yaml:
        try:
            return yaml.safe_load(raw) or {}, {}
        except Exception as e:
            return None, {"front_matter_parse_error": str(e)}
    try:
        return json.loads(raw), {}
    except Exception as e:
        return None, {"front_matter_parse_error": str(e), "hint": "Install PyYAML for YAML front matter."}


def load_claim_card(path: Path, logs):
    suf = path.suffix.lower()
    try:
        text = _load_text(path)
    except Exception as e:
        _emit(logs, "io_error", "error", f"Failed to read file: {e}", path=path)
        return None
    if suf in (".json",):
        try:
            return json.loads(text)
        except Exception as e:
            _emit(logs, "parse_error", "error", f"Invalid JSON: {e}", path=path)
            return None
    if suf in (".yaml", ".yml"):
        if not yaml:
            _emit(logs, "dependency_missing", "error", "PyYAML not installed; cannot parse YAML.", path=path)
            return None
        try:
            return yaml.safe_load(text)
        except Exception as e:
            _emit(logs, "parse_error", "error", f"Invalid YAML: {e}", path=path)
            return None
    if suf in (".md", ".markdown"):
        obj, meta = _parse_md_front_matter(text)
        if obj is None:
            _emit(logs, "parse_error", "error", "Failed to parse Markdown front matter.", path=path, details=meta)
            return None
        if meta.get("missing_front_matter"):
            _emit(logs, "missing_metadata", "error", "Markdown file missing YAML/JSON front matter.", path=path, pointer="/")
            return None
        if meta:
            _emit(logs, "parse_warning", "warning", "Front matter parsed with warnings.", path=path, details=meta)
        return obj
    _emit(logs, "unsupported_type", "error", f"Unsupported file type: {suf}", path=path)
    return None


def _get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _required_checks(obj, logs, path: Path):
    req = [
        ("/claim", ("claim",), "verbatim claim text"),
        ("/metadata", ("metadata",), "metadata section"),
        ("/metadata/id", ("metadata", "id"), "unique id"),
        ("/metadata/schema_version", ("metadata", "schema_version"), "schema_version"),
        ("/metadata/version", ("metadata", "version"), "card version"),
        ("/metadata/created_at", ("metadata", "created_at"), "created_at"),
        ("/metadata/authors", ("metadata", "authors"), "authors list"),
        ("/sources", ("sources",), "sources list"),
    ]
    for ptr, ks, desc in req:
        v = _get(obj, *ks, default=None)
        missing = v is None or v == "" or (isinstance(v, (list, dict)) and len(v) == 0)
        if missing:
            _emit(logs, "missing_metadata", "error", f"Missing required field: {desc}", path=path, pointer=ptr)
    authors = _get(obj, "metadata", "authors", default=None)
    if authors is not None and not isinstance(authors, list):
        _emit(logs, "missing_metadata", "error", "metadata.authors must be a list", path=path, pointer="/metadata/authors")
    sources = _get(obj, "sources", default=None)
    if sources is not None and not isinstance(sources, list):
        _emit(logs, "missing_metadata", "error", "sources must be a list", path=path, pointer="/sources")


def _version_ambiguity_checks(obj, logs, path: Path):
    md = _get(obj, "metadata", default={}) or {}
    if not isinstance(md, dict):
        return
    if "schemaVersion" in md and "schema_version" in md and md.get("schemaVersion") != md.get("schema_version"):
        _emit(logs, "version_ambiguity", "error", "Conflicting schema version fields (schemaVersion vs schema_version).", path=path, pointer="/metadata")
    if "ver" in md and "version" in md and str(md.get("ver")) != str(md.get("version")):
        _emit(logs, "version_ambiguity", "error", "Conflicting version fields (ver vs version).", path=path, pointer="/metadata")
    v = md.get("version")
    if isinstance(v, str) and re.search(r"\b(latest|current)\b", v, flags=re.I):
        _emit(logs, "version_ambiguity", "warning", "Ambiguous version label (e.g., 'latest'/'current'); use semantic or integer version.", path=path, pointer="/metadata/version")
    hist = _get(obj, "correction_history", default=[])
    if isinstance(hist, list) and hist:
        to_versions = [h.get("to_version") for h in hist if isinstance(h, dict) and "to_version" in h]
        if v is not None and any(tv is not None and str(tv) != str(v) for tv in to_versions):
            _emit(logs, "version_ambiguity", "warning", "metadata.version does not match last correction_history.to_version for at least one entry.", path=path, pointer="/correction_history", details={"metadata_version": v, "to_versions": to_versions[-5:]})


def _correction_history_checks(obj, logs, path: Path):
    hist = _get(obj, "correction_history", default=None)
    if hist is None:
        return
    if not isinstance(hist, list):
        _emit(logs, "correction_history_issues", "error", "correction_history must be a list.", path=path, pointer="/correction_history")
        return
    seen = set()
    prev_to = None
    for i, h in enumerate(hist):
        ptr = f"/correction_history/{i}"
        if not isinstance(h, dict):
            _emit(logs, "correction_history_issues", "error", "Each correction_history entry must be an object.", path=path, pointer=ptr)
            continue
        for fld in ("date", "reason", "changes", "from_version", "to_version"):
            if fld not in h or h[fld] in (None, "", []):
                _emit(logs, "correction_history_issues", "error", f"Missing correction_history field: {fld}", path=path, pointer=f"{ptr}/{fld}")
        key = (str(h.get("from_version")), str(h.get("to_version")), str(h.get("date")))
        if key in seen:
            _emit(logs, "correction_history_issues", "warning", "Duplicate correction_history entry (from_version/to_version/date).", path=path, pointer=ptr, details={"key": key})
        seen.add(key)
        tv = h.get("to_version")
        fv = h.get("from_version")
        if prev_to is not None and fv is not None and str(fv) != str(prev_to):
            _emit(logs, "correction_history_issues", "warning", "Non-contiguous correction history: from_version does not equal previous to_version.", path=path, pointer=ptr, details={"previous_to_version": prev_to, "from_version": fv})
        prev_to = tv if tv is not None else prev_to
        dt = h.get("date")
        if isinstance(dt, str):
            try:
                datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except Exception:
                _emit(logs, "correction_history_issues", "warning", "Correction history date is not ISO-8601 parseable.", path=path, pointer=f"{ptr}/date", details={"date": dt})


def _schema_validate(obj, schema_path: Path, logs, path: Path):
    if not schema_path.exists():
        _emit(logs, "schema_missing", "warning", f"Schema not found: {schema_path}", path=path)
        return
    if not jsonschema:
        _emit(logs, "dependency_missing", "warning", "jsonschema not installed; skipping schema validation.", path=path, details={"schema": str(schema_path)})
        return
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        _emit(logs, "schema_parse_error", "error", f"Failed to parse schema JSON: {e}", path=path, details={"schema": str(schema_path)})
        return
    try:
        v = jsonschema.Draft202012Validator(schema)
        for err in sorted(v.iter_errors(obj), key=lambda e: list(e.path)):
            ptr = "/" + "/".join(str(p) for p in err.path) if err.path else "/"
            _emit(logs, "schema_validation", "error", err.message, path=path, pointer=ptr, details={"validator": err.validator, "schema_path": list(err.schema_path)})
    except Exception as e:
        _emit(logs, "schema_validation_error", "error", f"Schema validation failed to run: {e}", path=path, details={"schema": str(schema_path)})


def validate_file(path: Path, schema_path: Path):
    logs = []
    obj = load_claim_card(path, logs)
    if obj is None:
        return None, logs
    if not isinstance(obj, dict):
        _emit(logs, "parse_error", "error", "Claim Card root must be an object.", path=path, pointer="/")
        return obj, logs
    _required_checks(obj, logs, path)
    _version_ambiguity_checks(obj, logs, path)
    _correction_history_checks(obj, logs, path)
    _schema_validate(obj, schema_path, logs, path)
    return obj, logs


def main(argv=None):
    ap = argparse.ArgumentParser(prog="claim-card-validate", description="Validate Claim Card YAML/JSON/MD and emit structured failure-mode logs.")
    ap.add_argument("input", help="Path to Claim Card (.json/.yaml/.yml/.md)")
    ap.add_argument("--schema", default=str(Path(__file__).resolve().parents[2] / "config" / "claim_card.schema.json"), help="Path to JSON schema.")
    ap.add_argument("--out", default="-", help="Write logs as JSONL to file (default: stdout).")
    ap.add_argument("--quiet", action="store_true", help="Only exit code; do not emit logs.")
    args = ap.parse_args(argv)

    in_path = Path(args.input)
    schema_path = Path(args.schema)

    _, logs = validate_file(in_path, schema_path)
    ok = not any(l["level"] == "error" for l in logs)
    if not args.quiet:
        out = sys.stdout if args.out == "-" else open(args.out, "w", encoding="utf-8")
        try:
            for l in logs:
                out.write(json.dumps(l, ensure_ascii=False) + "\n")
        finally:
            if out is not sys.stdout:
                out.close()
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
