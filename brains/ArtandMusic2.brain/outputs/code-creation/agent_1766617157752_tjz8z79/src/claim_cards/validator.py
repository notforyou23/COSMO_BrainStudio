"""Claim card + pilot case study validator.

Validates claim cards against an optional JSON schema and enforces that any
empirical claim in the pilot case study is linked to an existing, valid card.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

RE_CC_ID = re.compile(r"\bCC-[A-Za-z0-9][A-Za-z0-9_-]*\b")
RE_EMPIRICAL = re.compile(r"\bEMPIRICAL_CLAIM\b|\[EMPIRICAL\]|\bEmpirical claim\b", re.IGNORECASE)

REQUIRED_KEYS = {
    "claim_text",
    "scope",
    "evidence_type",
    "citations",
    "verification_status",
    "abstention_triggers",
}

ALLOWED_VERIFICATION = {"unverified", "partially", "verified"}


@dataclass(frozen=True)
class CardResult:
    card_id: str
    path: Path
    data: Dict[str, Any]
    errors: Tuple[str, ...]


def _norm_key(k: str) -> str:
    k = k.strip().lower()
    k = re.sub(r"[\s\-]+", "_", k)
    k = re.sub(r"[^a-z0-9_]+", "", k)
    return k


def _parse_simple_yaml(lines: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for ln in lines:
        if not ln.strip() or ln.lstrip().startswith("#") or ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        k = _norm_key(k)
        v = v.strip()
        if k in out:
            continue
        if k in {"citations", "abstention_triggers"}:
            if v.startswith("[") and v.endswith("]"):
                try:
                    out[k] = json.loads(v)
                except Exception:
                    out[k] = [v]
            else:
                out[k] = [x.strip() for x in v.split(";") if x.strip()] if v else []
        else:
            out[k] = v
    return out


def parse_claim_card_md(text: str) -> Dict[str, Any]:
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    data: Dict[str, Any] = {}

    if len(lines) >= 3 and lines[0].strip() == "---":
        try:
            end = lines.index("---", 1)
            data.update(_parse_simple_yaml(lines[1:end]))
            body_lines = lines[end + 1 :]
        except ValueError:
            body_lines = lines
    else:
        body_lines = lines

    kv = _parse_simple_yaml(body_lines[:80])
    for k, v in kv.items():
        data.setdefault(k, v)

    for k in list(REQUIRED_KEYS):
        if k not in data:
            m = re.search(rf"^\s*{re.escape(k.replace('_',' '))}\s*:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
            if m:
                data[k] = m.group(1).strip()

    if "citations" in data and isinstance(data["citations"], str):
        data["citations"] = [x.strip() for x in data["citations"].split(";") if x.strip()]
    if "abstention_triggers" in data and isinstance(data["abstention_triggers"], str):
        data["abstention_triggers"] = [x.strip() for x in data["abstention_triggers"].split(";") if x.strip()]
    return data


def load_schema(root: Path) -> Optional[Dict[str, Any]]:
    schema_path = root / "config" / "claim_card_schema.json"
    if not schema_path.exists():
        return None
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    req = schema.get("required", [])
    props = schema.get("properties", {})
    for k in req:
        if k not in data or data.get(k) in (None, "", []):
            errors.append(f"missing_required:{k}")
    for k, spec in props.items():
        if k not in data:
            continue
        v = data[k]
        t = spec.get("type")
        if t == "array" and not isinstance(v, list):
            errors.append(f"type:{k}:expected_array")
        if t == "string" and not isinstance(v, str):
            errors.append(f"type:{k}:expected_string")
        enum = spec.get("enum")
        if enum and v not in enum:
            errors.append(f"enum:{k}")
    addl = schema.get("additionalProperties")
    if addl is False:
        allowed = set(props.keys())
        for k in data.keys():
            if k not in allowed:
                errors.append(f"unexpected_field:{k}")
    return errors


def validate_claim_card(path: Path, schema: Optional[Dict[str, Any]] = None) -> CardResult:
    text = path.read_text(encoding="utf-8")
    data = parse_claim_card_md(text)

    cid = data.get("claim_card_id") or data.get("id") or None
    if not cid:
        m = RE_CC_ID.search(text)
        cid = m.group(0) if m else path.stem

    errs: List[str] = []
    if schema:
        errs.extend(_validate_against_schema(data, schema))
    else:
        for k in REQUIRED_KEYS:
            if k not in data or data.get(k) in (None, "", []):
                errs.append(f"missing_required:{k}")
        vs = (data.get("verification_status") or "").strip().lower()
        if vs and vs not in ALLOWED_VERIFICATION:
            errs.append("invalid:verification_status")
        if "citations" in data and not isinstance(data.get("citations"), list):
            errs.append("type:citations:expected_array")
        if "abstention_triggers" in data and not isinstance(data.get("abstention_triggers"), list):
            errs.append("type:abstention_triggers:expected_array")

    return CardResult(str(cid), path, data, tuple(errs))


def discover_claim_cards(dir_path: Path) -> Dict[str, CardResult]:
    out: Dict[str, CardResult] = {}
    if not dir_path.exists():
        return out
    schema = load_schema(dir_path.parent.parent)  # project root assumption
    for p in sorted(dir_path.glob("*.md")):
        res = validate_claim_card(p, schema=schema)
        out[res.card_id] = res
    return out


def validate_pilot_case_study(case_path: Path, cards: Dict[str, CardResult]) -> List[str]:
    if not case_path.exists():
        return [f"missing_case_study:{case_path}"]
    text = case_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = text.split("\n")
    errors: List[str] = []

    bad_cards = {cid for cid, r in cards.items() if r.errors}
    if bad_cards:
        errors.append("invalid_claim_cards:" + ",".join(sorted(bad_cards)))

    for i, ln in enumerate(lines):
        if not RE_EMPIRICAL.search(ln):
            continue
        window = "\n".join(lines[i : i + 4])
        ids = sorted(set(RE_CC_ID.findall(window)))
        if not ids:
            errors.append(f"empirical_claim_missing_card:line_{i+1}")
            continue
        for cid in ids:
            if cid not in cards:
                errors.append(f"missing_claim_card:{cid}:line_{i+1}")
            elif cards[cid].errors:
                errors.append(f"linked_invalid_claim_card:{cid}:line_{i+1}")
    return errors


def validate_project(root: Path) -> int:
    cards_dir = root / "src" / "claim_cards"
    cards = discover_claim_cards(cards_dir)
    pilot_paths = [
        root / "pilot_case_study.md",
        root / "case_studies" / "pilot.md",
        root / "case_studies" / "pilot_case_study.md",
    ]
    pilot = next((p for p in pilot_paths if p.exists()), pilot_paths[0])

    errors: List[str] = []
    if not cards:
        errors.append(f"no_claim_cards_found:{cards_dir}")
    errors.extend(validate_pilot_case_study(pilot, cards))

    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 2
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(argv[0]).resolve() if argv else Path.cwd()
    return validate_project(root)


if __name__ == "__main__":
    raise SystemExit(main())
