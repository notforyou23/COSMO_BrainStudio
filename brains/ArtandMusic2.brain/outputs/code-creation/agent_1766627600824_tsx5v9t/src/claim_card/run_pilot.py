from __future__ import annotations
from pathlib import Path
import json, datetime

def _now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _load_schema(schema_path: Path):
    if not schema_path.exists():
        return None
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _semverish(s: str) -> bool:
    if not isinstance(s, str) or not s.strip():
        return False
    s = s.strip().lstrip("v")
    parts = s.split(".")
    if len(parts) < 2 or len(parts) > 3:
        return False
    return all(p.isdigit() for p in parts)

def _add_issue(issues, mode, code, message, path=""):
    issues.append({"failure_mode": mode, "code": code, "message": message, "path": path})

def _schema_validate(card: dict, schema: dict | None):
    issues = []
    if not schema:
        return issues
    try:
        import jsonschema
        v = jsonschema.Draft202012Validator(schema)
        for e in sorted(v.iter_errors(card), key=lambda x: list(x.path)):
            p = "/".join(str(x) for x in e.path)
            mode = "missing_metadata" if e.validator == "required" else "schema_violation"
            _add_issue(issues, mode, f"schema.{e.validator}", e.message, p)
    except Exception as ex:
        _add_issue(issues, "validator_error", "validator.exception", str(ex), "")
    return issues

def _custom_checks(card: dict):
    issues = []
    required = ["verbatim_claim", "source", "created_at", "created_by", "schema_version", "card_version"]
    for k in required:
        if k not in card or card.get(k) in (None, "", []):
            _add_issue(issues, "missing_metadata", "missing.required_field", f"Missing or empty required field '{k}'", k)

    sv = card.get("schema_version")
    cv = card.get("card_version")
    if sv is None or (isinstance(sv, str) and not _semverish(sv)):
        _add_issue(issues, "version_ambiguity", "version.schema_version_ambiguous", "schema_version should be semver-like (e.g., 1.0.0)", "schema_version")
    if cv is None or (isinstance(cv, str) and not _semverish(cv)):
        _add_issue(issues, "version_ambiguity", "version.card_version_ambiguous", "card_version should be semver-like (e.g., 0.1.0)", "card_version")

    ch = card.get("correction_history")
    status = str(card.get("status", "")).lower().strip()
    if status in ("corrected", "amended") and not ch:
        _add_issue(issues, "correction_history", "corrections.missing_history", "status indicates corrections but correction_history is missing/empty", "correction_history")

    if ch is not None:
        if not isinstance(ch, list):
            _add_issue(issues, "correction_history", "corrections.not_list", "correction_history must be a list", "correction_history")
        else:
            for i, entry in enumerate(ch):
                if not isinstance(entry, dict):
                    _add_issue(issues, "correction_history", "corrections.entry_not_object", "Each correction entry must be an object", f"correction_history/{i}")
                    continue
                for rk in ("at", "by", "reason", "changes"):
                    if rk not in entry or entry.get(rk) in (None, "", []):
                        _add_issue(issues, "correction_history", "corrections.entry_missing_field", f"Correction entry missing/empty '{rk}'", f"correction_history/{i}/{rk}")
                if "changes" in entry and entry.get("changes") is not None and not isinstance(entry.get("changes"), list):
                    _add_issue(issues, "correction_history", "corrections.changes_not_list", "changes must be a list", f"correction_history/{i}/changes")
    return issues

def validate_card(card: dict, schema: dict | None):
    issues = []
    issues.extend(_schema_validate(card, schema))
    issues.extend(_custom_checks(card))
    dedup = {}
    for it in issues:
        k = (it["failure_mode"], it["code"], it.get("path",""), it["message"])
        dedup[k] = it
    issues = list(dedup.values())
    ok = len([i for i in issues if i["failure_mode"] not in ("validator_error",)]) == 0
    return ok, sorted(issues, key=lambda x: (x["failure_mode"], x["code"], x.get("path","")))

def run_pilot(base: Path):
    schema_path = base / "config" / "claim_card.schema.json"
    schema = _load_schema(schema_path)
    out_dir = base / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "claim_card_pilot_failure_report.json"

    samples = [
        ("claim_1_missing_metadata", {
            "verbatim_claim": "Students learn better when taught in smaller classes.",
            "source": {"type": "web", "url": "https://example.com/study"},
            "schema_version": "1.0.0",
            "card_version": "0.1.0"
        }),
        ("claim_2_version_ambiguity", {
            "verbatim_claim": "A 10% increase in sleep improves memory by 20%.",
            "source": {"type": "paper", "citation": "Doe et al. (2022)"},
            "created_at": _now_iso(),
            "created_by": {"name": "Pilot Runner", "role": "analyst"},
            "schema_version": "1",
            "card_version": "v1"
        }),
        ("claim_3_correction_history_issue", {
            "verbatim_claim": "Adding fluoride to water reduces cavities.",
            "source": {"type": "report", "citation": "Agency Report 2019"},
            "created_at": _now_iso(),
            "created_by": {"name": "Pilot Runner", "role": "analyst"},
            "schema_version": "1.0.0",
            "card_version": "0.2.0",
            "status": "corrected",
            "correction_history": [{"at": _now_iso(), "by": "", "reason": "typo", "changes": "fixed"}]
        }),
    ]

    results, counts = [], {}
    for name, card in samples:
        ok, issues = validate_card(card, schema)
        for it in issues:
            counts[it["failure_mode"]] = counts.get(it["failure_mode"], 0) + 1
        results.append({"name": name, "ok": ok, "issue_count": len(issues), "issues": issues})

    report = {
        "run_at": _now_iso(),
        "schema_path": str(schema_path),
        "schema_loaded": bool(schema),
        "sample_count": len(samples),
        "failure_mode_counts": counts,
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print("PILOT_REPORT_WRITTEN:" + str(report_path))
    return report

def main():
    base = Path(__file__).resolve().parents[2]
    run_pilot(base)

if __name__ == "__main__":
    main()
