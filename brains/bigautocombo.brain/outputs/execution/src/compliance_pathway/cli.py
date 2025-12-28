"""CLI entry point for generating the v1 compliance/certification pathway artifact."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


DEFAULT_OUT_REL = Path("outputs") / "compliance_standards_map.md"


@dataclass(frozen=True)
class CLIOptions:
    region: str
    out_path: Path
    fmt: str
    include_checklist: bool
    include_decision_tree: bool


def _try_render_from_package(region: str, fmt: str, include_checklist: bool, include_decision_tree: bool) -> Optional[str]:
    """Try to delegate rendering to the library if present; otherwise return None."""
    try:
        from . import render as _render  # type: ignore

        if hasattr(_render, "render_markdown"):
            return _render.render_markdown(
                region=region,
                fmt=fmt,
                include_checklist=include_checklist,
                include_decision_tree=include_decision_tree,
            )
        if hasattr(_render, "render"):
            return _render.render(
                region=region,
                fmt=fmt,
                include_checklist=include_checklist,
                include_decision_tree=include_decision_tree,
            )
        if hasattr(_render, "generate_markdown"):
            return _render.generate_markdown(
                region=region,
                include_checklist=include_checklist,
                include_decision_tree=include_decision_tree,
            )
    except Exception:
        return None
    return None


def _md_table(headers: list[str], rows: Iterable[list[str]]) -> str:
    def esc(s: str) -> str:
        return (s or "").replace("\n", "<br>").replace("|", "\\|")

    h = "| " + " | ".join(esc(x) for x in headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(esc(x) for x in r) + " |" for r in rows)
    return "\n".join([h, sep, body]).strip() + "\n"


def _fallback_markdown(region: str, include_checklist: bool, include_decision_tree: bool) -> str:
    """Minimal v1 artifact renderer to keep the CLI functional without other modules."""
    title_region = {"us": "US (FMVSS)", "eu": "EU (UNECE)", "both": "US+EU"}.get(region, region)

    rows = [
        [
            "High-voltage battery pack & HV wiring",
            "FMVSS 305 (Electric-powered vehicles: electrolyte spillage & electrical shock)",
            "UN R100 (Electric power train; HV safety)",
            "HV isolation, dielectric withstand, IP protection, crash/post-crash safety, labeling",
            "HV architecture, schematics, isolation test report, component certs, risk assessment",
        ],
        [
            "Traction inverter/motor/controller",
            "FMVSS 305 (electrical safety, as applicable); Part 15B (EMC) (supplier-driven)",
            "UN R10 (EMC); UN R100 (HV safety, as applicable)",
            "EMC (radiated/conducted), functional safety evidence, HV insulation verification",
            "EMC test reports, SW/firmware ID, change control, supplier declarations",
        ],
        [
            "On-board charger / DC-DC converter",
            "FMVSS 305 (HV safety, as applicable)",
            "UN R10 (EMC); UN R100 (HV safety)",
            "EMC, dielectric/insulation, thermal protection verification",
            "EMC report, insulation test report, installation instructions",
        ],
        [
            "Service disconnects, interlocks, HV connectors",
            "FMVSS 305",
            "UN R100",
            "Interlock validation, insulation, ingress protection",
            "Connector datasheets, torque specs, harness drawings",
        ],
        [
            "Brake system modifications (regen integration)",
            "FMVSS 135 (Light vehicle brake systems) / 105 (hydraulic & electric brake systems; as applicable)",
            "UN R13H (M1) / UN R13 (as applicable)",
            "Stopping distance, fade, ABS/ESC integration checks, brake lamps logic",
            "Brake performance test plan/report, control strategy description",
        ],
        [
            "Exterior lighting/lamps if modified",
            "FMVSS 108",
            "UNECE lighting regs (e.g., R48 installation; lamp-specific regs)",
            "Photometry/aim/installation compliance, tell-tales",
            "Lamp certifications, installation drawings, labeling",
        ],
        [
            "EMC overall vehicle impact",
            "FCC/Part 15 (where applicable) (market-driven); OEM best-practice",
            "UN R10",
            "Radiated/conducted emissions & immunity (vehicle/system level)",
            "EMC plan, test reports, configuration control, wiring layout",
        ],
        [
            "Labels, VIN, placards affected by conversion",
            "49 CFR parts (labeling/VIN); FMVSS affected labeling references",
            "National type-approval admin requirements; UN regs label clauses",
            "Label content/placement verification",
            "Updated label artwork, conformity documentation, traceability",
        ],
    ]

    if region == "us":
        for r in rows:
            r[2] = "—"
    elif region == "eu":
        for r in rows:
            r[1] = "—"

    md = []
    md.append(f"# Compliance / Certification Pathway (v1) — {title_region}\n")
    md.append("## Scope\n")
    md.append(
        "This artifact maps common EV conversion components to applicable standards (FMVSS/UNECE where relevant), "
        "typical required tests (EMC, HV safety, braking, lighting, labeling), and a documentation package checklist.\n"
    )
    md.append("## Component-to-Standard Crosswalk (v1)\n")
    md.append(
        _md_table(
            ["Conversion component", "US (FMVSS / related)", "EU (UNECE)", "Typical required tests", "Documentation package (examples)"],
            rows,
        )
    )

    if include_checklist:
        md.append("## Documentation Package Checklist (v1)\n")
        checklist = [
            "Vehicle description & configuration (BOM, variant ID, build record)",
            "System architecture (HV schematic, grounding, isolation strategy)",
            "Installation instructions/work instructions + torque/spec sheets",
            "Hazard analysis & risk assessment (HV shock, thermal runaway, functional hazards)",
            "Test plans and reports: HV isolation/dielectric, EMC, braking performance, lighting verification",
            "Software/firmware configuration control (versioning, release notes, change log)",
            "Labeling pack: HV warning labels, placards, VIN/identifier mapping (as required)",
            "Supplier compliance evidence (component certifications, declarations, material specs)",
            "Traceability: serial numbers, calibration records, inspection checklists",
        ]
        md.append("\n".join(["- " + x for x in checklist]) + "\n")

    if include_decision_tree:
        md.append("## Initial Certification Strategy Decision Tree (v1)\n")
        md.append(
            "- Start\n"
            "  - Target market?\n"
            "    - US\n"
            "      - Is this a new vehicle manufacturer/alterer stage?\n"
            "        - Alterer/Final-stage manufacturer: assess FMVSS impact scope; create compliance matrix; test where impacted\n"
            "        - Converter/modifier: confirm state/registration requirements; maintain evidence; consider third-party testing\n"
            "      - Any braking/lighting changes?\n"
            "        - Yes: plan FMVSS 135/108 verification\n"
            "        - No: focus on FMVSS 305 HV safety + labeling/VIN obligations\n"
            "    - EU\n"
            "      - Type approval path?\n"
            "        - Full vehicle WVTA: engage technical service early; UN R100 + UN R10 baseline\n"
            "        - National/IVA/low-volume: confirm country scheme; test to UN regs where required\n"
            "      - Any EMC-relevant changes?\n"
            "        - Yes: UN R10 test plan at vehicle/system level\n"
            "        - No: document rationale + configuration freeze\n"
            "    - Both\n"
            "      - Build a combined compliance matrix; design to the stricter requirement where practical\n"
            "      - Schedule: component evidence first, then integration tests (HV safety, EMC, braking, lighting)\n"
        )

    md.append("\n---\n")
    md.append("Generated by compliance_pathway CLI (v1).\n")
    return "\n".join(md).strip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="compliance-pathway",
        description="Generate v1 compliance/certification pathway markdown artifact into outputs.",
    )
    p.add_argument(
        "--region",
        default="both",
        choices=["us", "eu", "both"],
        help="Region focus for standards mapping.",
    )
    p.add_argument(
        "--format",
        default="md",
        choices=["md", "markdown"],
        help="Output formatting (v1 supports markdown).",
    )
    p.add_argument(
        "--out",
        default=str(DEFAULT_OUT_REL),
        help="Output path (relative to project root by default).",
    )
    p.add_argument("--no-checklist", action="store_true", help="Exclude documentation checklist section.")
    p.add_argument("--no-decision-tree", action="store_true", help="Exclude certification decision tree section.")
    return p


def parse_args(argv: Optional[list[str]] = None) -> CLIOptions:
    ns = build_parser().parse_args(argv)
    out_path = Path(ns.out)
    if not out_path.is_absolute():
        out_path = Path.cwd() / out_path
    fmt = "md" if ns.format in ("md", "markdown") else str(ns.format)
    return CLIOptions(
        region=str(ns.region),
        out_path=out_path,
        fmt=fmt,
        include_checklist=not bool(ns.no_checklist),
        include_decision_tree=not bool(ns.no_decision_tree),
    )


def generate_markdown(region: str = "both", fmt: str = "md", include_checklist: bool = True, include_decision_tree: bool = True) -> str:
    rendered = _try_render_from_package(region, fmt, include_checklist, include_decision_tree)
    return rendered if isinstance(rendered, str) and rendered.strip() else _fallback_markdown(region, include_checklist, include_decision_tree)


def run(argv: Optional[list[str]] = None) -> Path:
    opts = parse_args(argv)
    opts.out_path.parent.mkdir(parents=True, exist_ok=True)
    md = generate_markdown(
        region=opts.region,
        fmt=opts.fmt,
        include_checklist=opts.include_checklist,
        include_decision_tree=opts.include_decision_tree,
    )
    opts.out_path.write_text(md, encoding="utf-8")
    return opts.out_path


def main(argv: Optional[list[str]] = None) -> int:
    out_path = run(argv)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
