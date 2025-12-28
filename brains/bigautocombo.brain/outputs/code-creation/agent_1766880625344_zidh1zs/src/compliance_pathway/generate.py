from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class StandardRef:
    jurisdiction: str  # "US" | "UNECE"
    code: str          # e.g., "FMVSS 108", "UN R10"
    title: str


@dataclass(frozen=True)
class ComponentMapRow:
    component: str
    scope_notes: str
    standards: Tuple[str, ...]  # list of standard codes (deterministic order)
    required_tests: Tuple[str, ...]


def _v1_data() -> Dict[str, object]:
    standards: List[StandardRef] = [
        StandardRef("US", "FMVSS 105", "Hydraulic brake systems"),
        StandardRef("US", "FMVSS 108", "Lamps, reflective devices, and associated equipment"),
        StandardRef("US", "FMVSS 111", "Rear visibility"),
        StandardRef("US", "FMVSS 121", "Air brake systems (if applicable)"),
        StandardRef("US", "FMVSS 124", "Accelerator control systems"),
        StandardRef("US", "FMVSS 135", "Light vehicle brake systems"),
        StandardRef("US", "FMVSS 138", "Tire pressure monitoring systems"),
        StandardRef("US", "FMVSS 305", "Electric-powered vehicles: electrolyte spillage and electrical shock protection"),
        StandardRef("US", "FMVSS 401", "Interior trunk release"),
        StandardRef("UNECE", "UN R10", "Electromagnetic compatibility (EMC)"),
        StandardRef("UNECE", "UN R13H", "Braking of passenger cars"),
        StandardRef("UNECE", "UN R48", "Installation of lighting and light-signalling devices"),
        StandardRef("UNECE", "UN R79", "Steering equipment"),
        StandardRef("UNECE", "UN R100", "Electric power train vehicles (HV safety)"),
    ]

    tests = {
        "EMC": ["Radiated emissions", "Conducted emissions", "Radiated immunity", "Transient immunity"],
        "HV Safety": ["Isolation resistance", "Protection against electric shock", "IP rating / ingress protection", "Interlock / service disconnect"],
        "Braking": ["Brake performance (service/parking)", "ABS/ESC functionality (if equipped)", "Brake warning/diagnostics"],
        "Lighting": ["Photometrics (where applicable)", "Installation/aiming verification", "Tell-tales/indicators"],
        "Labeling": ["VIN/vehicle certification label content", "HV warning labels", "Service labeling (disconnects, PPE)"],
    }

    docs = [
        "Vehicle description & configuration control (BOM, wiring diagrams, HV schematic)",
        "Safety case / hazard analysis (HARA/FMEA) for conversion changes",
        "Test plan, procedures, and objective evidence (reports, raw data, calibration certs)",
        "EMC test report package (setup photos, EUT configuration, pass/fail, deviations)",
        "HV safety compliance evidence (isolation, creepage/clearance rationale, IP, interlocks)",
        "Brake system documentation (line lock-up, bias changes, regen blending strategy, warnings)",
        "Lighting compliance evidence (lamp compliance basis, installation validation, aim records)",
        "Labeling artwork and placement drawings; durability rationale",
        "Change management record (deviations, waivers, re-test triggers)",
        "Owner’s manual / service manual deltas for converted systems",
    ]

    components: List[ComponentMapRow] = [
        ComponentMapRow(
            "High-voltage battery pack & enclosures",
            "HV energy storage integration, crash/hazard controls, enclosures, disconnects.",
            ("FMVSS 305", "UN R100"),
            ("HV Safety", "Labeling"),
        ),
        ComponentMapRow(
            "Traction inverter / motor / HV cabling",
            "HV powertrain electronics, harness routing, shielding/filters.",
            ("FMVSS 305", "UN R10", "UN R100"),
            ("EMC", "HV Safety", "Labeling"),
        ),
        ComponentMapRow(
            "On-board charger / DC-DC converter / charge inlet",
            "Charging interfaces and power electronics; EMC and HV protections.",
            ("FMVSS 305", "UN R10", "UN R100"),
            ("EMC", "HV Safety", "Labeling"),
        ),
        ComponentMapRow(
            "Brake system changes (hydraulic, booster, regen blending)",
            "Any modification to service/parking brakes or controls and warnings.",
            ("FMVSS 105", "FMVSS 135", "UN R13H"),
            ("Braking", "Labeling"),
        ),
        ComponentMapRow(
            "Lighting & signaling modifications",
            "Lamp replacements/relocation, harness changes, tell-tales.",
            ("FMVSS 108", "UN R48"),
            ("Lighting", "Labeling"),
        ),
        ComponentMapRow(
            "Driver controls & instrument cluster updates",
            "Throttle/accelerator mapping, indicators, warnings for HV/charge state.",
            ("FMVSS 124", "FMVSS 108"),
            ("Labeling",),
        ),
        ComponentMapRow(
            "Steering/ADAS related changes (if impacted)",
            "Any influence on steering equipment or control systems.",
            ("UN R79",),
            ("Labeling",),
        ),
    ]

    decision_tree = [
        ("1) Intended market?", ["US (FMVSS self-certification)", "UNECE/WVTA (type approval)", "Both (dual evidence set)"]),
        ("2) Vehicle class / scope?", ["Passenger car/light truck", "Bus/HD (additional brake/lighting rules)"]),
        ("3) Conversion impact level?", ["HV-only (no brake/lighting changes)", "Brakes/lighting affected", "Structural/crashworthiness affected (escalate)"]),
        ("4) Evidence strategy?", ["Use component supplier reports", "Full-vehicle test campaign", "Hybrid (gap-test only)"]),
        ("5) Release gate?", ["Internal compliance review -> build record", "Third-party lab sign-off where needed", "Production control & labeling finalization"]),
    ]

    return {"standards": standards, "tests": tests, "docs": docs, "components": components, "decision_tree": decision_tree}


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    h = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join([h, sep, body]).rstrip() + "\n"


def _render_markdown(data: Dict[str, object]) -> str:
    standards: List[StandardRef] = list(data["standards"])  # type: ignore[assignment]
    tests: Dict[str, List[str]] = dict(data["tests"])  # type: ignore[assignment]
    docs: List[str] = list(data["docs"])  # type: ignore[assignment]
    components: List[ComponentMapRow] = list(data["components"])  # type: ignore[assignment]
    decision_tree = list(data["decision_tree"])  # type: ignore[assignment]

    std_sorted = sorted(standards, key=lambda s: (s.jurisdiction, s.code))
    comp_sorted = sorted(components, key=lambda c: c.component.lower())

    lines: List[str] = []
    lines.append("# Compliance & Certification Pathway (v1)")
    lines.append("")
    lines.append("Deterministic v1 artifact mapping EV conversion components to commonly applicable US (FMVSS) and UNECE standards, required test domains, documentation checklist, and an initial certification strategy decision tree.")
    lines.append("")
    lines.append("## Standards catalog (v1)")
    rows = [[s.jurisdiction, s.code, s.title] for s in std_sorted]
    lines.append(_md_table(["Jurisdiction", "Standard", "Title / Scope"], rows).rstrip())
    lines.append("")
    lines.append("## Component → standards / tests crosswalk (v1)")
    rows2: List[List[str]] = []
    for c in comp_sorted:
        rows2.append([
            c.component,
            c.scope_notes,
            ", ".join(c.standards),
            ", ".join(c.required_tests),
        ])
    lines.append(_md_table(["Conversion component", "Scope notes", "Applicable standards (examples)", "Required test domains"], rows2).rstrip())
    lines.append("")
    lines.append("## Required tests (by domain)")
    for domain in sorted(tests.keys()):
        lines.append(f"### {domain}")
        for item in tests[domain]:
            lines.append(f"- {item}")
        lines.append("")
    lines.append("## Documentation package checklist (minimum v1)")
    for item in docs:
        lines.append(f"- [ ] {item}")
    lines.append("")
    lines.append("## Initial certification strategy decision tree (v1)")
    for node, options in decision_tree:
        lines.append(f"- **{node}**")
        for opt in options:
            lines.append(f"  - {opt}")
    lines.append("")
    lines.append("---")
    lines.append("Generated by `compliance_pathway.generate` (v1).")
    lines.append("")
    return "\n".join(lines)


def _validate(data: Dict[str, object]) -> None:
    assert isinstance(data.get("standards"), list) and data["standards"], "standards missing"
    assert isinstance(data.get("components"), list) and data["components"], "components missing"
    assert isinstance(data.get("tests"), dict) and data["tests"], "tests missing"
    assert isinstance(data.get("docs"), list) and data["docs"], "docs missing"
    # Ensure component references only known test domains
    test_domains = set(data["tests"].keys())  # type: ignore[union-attr]
    for c in data["components"]:  # type: ignore[assignment]
        for td in c.required_tests:
            if td not in test_domains:
                raise ValueError(f"Unknown test domain referenced by component '{c.component}': {td}")


def generate(output_dir: Optional[Path] = None) -> Path:
    base = Path.cwd() if output_dir is None else Path(output_dir)
    out_dir = base / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "compliance_standards_map.md"

    data = _v1_data()
    _validate(data)
    md = _render_markdown(data)
    out_path.write_text(md, encoding="utf-8", newline="\n")
    return out_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    _ = argv
    generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
