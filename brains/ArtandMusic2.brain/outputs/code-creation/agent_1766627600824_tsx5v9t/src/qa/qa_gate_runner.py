from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
ROOT = Path(__file__).resolve()
for _ in range(8):
    if (ROOT.parent / "config").exists():
        break
    ROOT = ROOT.parent
ROOT = ROOT.parent if (ROOT.parent / "config").exists() else Path.cwd()
def _load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return 
def load_yaml(path: Path) -> Dict[str, Any]:
    text = _load_text(path)
    if not text.strip():
        return {}
    try:
        import yaml  # type: ignore
        obj = yaml.safe_load(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        # Minimal, permissive fallback: only supports flat key:value and top-level lists under a key.
        out: Dict[str, Any] = {}
        current_key: Optional[str] = None
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].rstrip("\n")
            if not line.strip():
                continue
            if line.lstrip() == line and ":" in line:
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip()
                current_key = k
                if v == "":
                    out[k] = []
                elif v.lower() in ("true", "false"):
                    out[k] = (v.lower() == "true")
                else:
                    out[k] = v.strip('"').strip("'")
            elif current_key and line.strip().startswith("-") and isinstance(out.get(current_key), list):
                out[current_key].append(line.strip()[1:].strip().strip('"').strip("'"))
        return out
@dataclass
class Issue:
    gate: str
    code: str
    message: str
    path: str = ""
    hint: str = ""

    def as_dict(self) -> Dict[str, Any]:
        d = {"gate": self.gate, "code": self.code, "message": self.message}
        if self.path:
            d["path"] = self.path
        if self.hint:
            d["hint"] = self.hint
        return d
def _find_claim_card_template(root: Path) -> Optional[Path]:
    candidates = [
        root / "outputs" / "templates" / "CLAIM_CARD.yaml",
        root / "outputs" / "templates" / "CLAIM_CARD.yml",
        root / "outputs" / "templates" / "CLAIM_CARD.md",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None
def _validate_claim_card_fields(obj: Any) -> List[Tuple[str, str]]:
    # Returns list of (field, issue_message)
    req = ["verbatim_claim", "source_context", "provenance_anchor"]
    issues: List[Tuple[str, str]] = []
    if not isinstance(obj, dict):
        return [("document", "Claim card must be a YAML mapping/object at the top level.")]
    for k in req:
        v = obj.get(k)
        if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, (list, dict)) and not v):
            issues.append((k, f"Missing or empty required field: {k}."))
    # Optional lifecycle checks if present
    status = obj.get("status")
    allowed = obj.get("status_lifecycle", {}).get("allowed_statuses") if isinstance(obj.get("status_lifecycle"), dict) else None
    if status is not None:
        if isinstance(allowed, list) and allowed and status not in allowed:
            issues.append(("status", f"Status '{status}' not in allowed_statuses: {allowed}."))
        if not isinstance(status, str) or not status.strip():
            issues.append(("status", "If provided, status must be a non-empty string."))
    return issues
def _validate_against_schema(data: Any, schema_path: Path) -> Optional[str]:
    if not schema_path.exists():
        return None
    try:
        import yaml  # type: ignore
        schema = yaml.safe_load(_load_text(schema_path))
    except Exception:
        return f"Failed to load schema YAML: {schema_path}"
    try:
        import jsonschema  # type: ignore
        jsonschema.validate(instance=data, schema=schema)
        return None
    except Exception as e:
        return f"Schema validation failed: {e}
def run_claim_card_gate(root: Path) -> Dict[str, Any]:
    gate = "claim_card"
    issues: List[Issue] = []
    tpl = _find_claim_card_template(root)
    wf = root / "outputs" / "workflows" / "CLAIM_VERIFICATION_WORKFLOW.md"
    schema = root / "config" / "claim_card.schema.yaml"

    if tpl is None:
        issues.append(Issue(gate, "MISSING_TEMPLATE", "Missing claim card template.", str(root / "outputs/templates/CLAIM_CARD.yaml"),
                            "Add outputs/templates/CLAIM_CARD.yaml (or .md/.yml) with required fields: verbatim_claim, source_context, provenance_anchor."))
    else:
        if tpl.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml  # type: ignore
                data = yaml.safe_load(_load_text(tpl))
            except Exception as e:
                data = None
                issues.append(Issue(gate, "INVALID_YAML", f"Template YAML could not be parsed: {e}", str(tpl),
                                    "Fix YAML syntax so the template can be validated."))
            if data is not None:
                sch_err = _validate_against_schema(data, schema)
                if sch_err:
                    issues.append(Issue(gate, "SCHEMA_FAIL", sch_err, str(schema),
                                        "Ensure config/claim_card.schema.yaml exists and the template conforms to it."))
                for field, msg in _validate_claim_card_fields(data):
                    issues.append(Issue(gate, "FIELD_FAIL", msg, str(tpl),
                                        "Populate all mandatory fields and ensure they are non-empty."))
        else:
            txt = _load_text(tpl)
            for token in ("verbatim claim", "source/context", "provenance anchor"):
                if token not in txt.lower():
                    issues.append(Issue(gate, "MD_MISSING_FIELD", f"Markdown template missing required cue: '{token}'.", str(tpl),
                                        "Include headings/labels for verbatim claim, source/context, and provenance anchor."))
    if not wf.exists():
        issues.append(Issue(gate, "MISSING_WORKFLOW", "Missing claim verification workflow spec.", str(wf),
                            "Add outputs/workflows/CLAIM_VERIFICATION_WORKFLOW.md describing required inputs, validation rules, and status lifecycle."))
    else:
        wtxt = _load_text(wf).lower()
        for token in ("verbatim", "source", "provenance", "validation", "status"):
            if token not in wtxt:
                issues.append(Issue(gate, "WORKFLOW_INCOMPLETE", f"Workflow appears incomplete (missing cue: '{token}').", str(wf),
                                    "Ensure workflow includes required inputs, validation rules, and claim status lifecycle."))
    if not schema.exists():
        issues.append(Issue(gate, "MISSING_SCHEMA", "Missing claim card schema.", str(schema),
                            "Add config/claim_card.schema.yaml to enable machine validation of claim cards."))

    return {
        "gate": gate,
        "passed": len(issues) == 0,
        "issues": [i.as_dict() for i in issues],
    }
def load_gate_config(root: Path) -> Dict[str, Any]:
    cfg = load_yaml(root / "config" / "qa_gates.yaml")
    gates = cfg.get("gates")
    if isinstance(gates, dict):
        return gates
    if isinstance(cfg, dict) and any(k in cfg for k in ("claim_card", "gates")):
        return cfg  # permissive fallback
    return {}
def run_all(root: Optional[Path] = None) -> Dict[str, Any]:
    root = root or ROOT
    gate_cfg = load_gate_config(root)
    enabled = True
    required = True
    cc_cfg = gate_cfg.get("claim_card") if isinstance(gate_cfg, dict) else None
    if isinstance(cc_cfg, dict):
        enabled = bool(cc_cfg.get("enabled", True))
        required = bool(cc_cfg.get("required", True))

    results: List[Dict[str, Any]] = []
    if enabled or required:
        results.append(run_claim_card_gate(root))

    passed = all(r.get("passed", False) for r in results) if results else True
    issues = [it for r in results for it in (r.get("issues") or [])]
    report = {
        "overall_passed": passed,
        "gates_run": [r["gate"] for r in results],
        "issues": issues,
    }
    return report
def main() -> None:
    report = run_all()
    print(json.dumps(report, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
