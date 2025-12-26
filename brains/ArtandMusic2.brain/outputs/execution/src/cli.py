#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, sys

def _id(path: list[str]) -> str:
    s = " > ".join(path).encode("utf-8")
    return "sec-" + hashlib.sha1(s).hexdigest()[:10]

def _canon_outline() -> list[dict]:
    O = []
    def sec(title, kids=None):
        return {"title": title, "children": kids or []}
    O = [
        sec("Executive summary"),
        sec("Scope, audience, and definitions"),
        sec("Research questions and method"),
        sec("Findings: measurement design as an equity lever"),
        sec("Recommendations"),
        sec("Implementation plan (4-week agent schedule)"),
        sec("Risks, ethics, and governance"),
        sec("Appendix"),
    ]
    return O

def _walk(outline: list[dict], prefix=None):
    prefix = prefix or []
    for n in outline:
        path = prefix + [n["title"]]
        yield path, _id(path)
        yield from _walk(n.get("children") or [], path)

def _render_report_outline(outline: list[dict]) -> str:
    lines = ["# REPORT_OUTLINE", ""]
    for i, (path, sid) in enumerate(_walk(outline), 1):
        if len(path) != 1:  # only top-level for this v0
            continue
        lines += [f'- [{i}. {path[0]}](#{sid})']
    lines += ["", "## Section index (canonical IDs)", ""]
    for i, (path, sid) in enumerate(_walk(outline), 1):
        if len(path) != 1:
            continue
        lines.append(f"- {i}. {path[0]} — `{sid}`")
    return "
".join(lines).strip() + "
"

def _render_draft_skeleton(outline: list[dict]) -> str:
    lines = ["# DRAFT_REPORT_v0", "", "This is a deterministic section skeleton aligned to REPORT_OUTLINE.", ""]
    for i, (path, sid) in enumerate(_walk(outline), 1):
        if len(path) != 1:
            continue
        title = path[0]
        lines += [f'<a id="{sid}"></a>', f"## {i}. {title}", "", "- Content pending.", ""]
    return "
".join(lines).strip() + "
"

def _render_plan(outline: list[dict]) -> str:
    rows = []
    for i, (path, sid) in enumerate(_walk(outline), 1):
        if len(path) != 1:
            continue
        rows.append((str(i), path[0], sid))
    def row(cols): return "| " + " | ".join(cols) + " |"
    lines = [
        "# plan_project_scope_and_outline",
        "",
        "## Mission",
        "Create `runtime/outputs/plan_project_scope_and_outline.md` that deterministically maps to `runtime/outputs/REPORT_OUTLINE.md` and the section skeleton inside `runtime/outputs/DRAFT_REPORT_v0.md`.",
        "",
        "## Intended audience",
        "- Project stakeholders who need a stable, inspectable structure before drafting content.",
        "- Agentic/automated contributors who will fill sections without drifting the outline.",
        "",
        "## Research questions",
        "- What is the report trying to decide, explain, or recommend?",
        "- Which definitions and assumptions must be locked to keep the draft consistent?",
        "- Where can measurement design create equity risks (hidden levers), and how can that be audited?",
        "",
        "## Deterministic mapping contract",
        "Each top-level section has a canonical stable ID computed from its title path. The same IDs appear in:",
        "- `REPORT_OUTLINE.md` (index links)",
        "- `DRAFT_REPORT_v0.md` (anchors on headings)",
        "- This plan (table below).",
        "",
        "### Canonical section map",
        row(["#", "Section", "Canonical ID"]),
        row(["---", "---", "---"]),
    ]
    lines += [row(list(r)) for r in rows]
    lines += [
        "",
        "## Work plan (4-week agent schedule)",
        "- Week 1: Confirm scope/audience/definitions; finalize section map and acceptance checks.",
        "- Week 2: Populate Background/Method; add initial evidence notes under Findings.",
        "- Week 3: Draft Recommendations and Implementation Plan; run coherence and gap checks.",
        "- Week 4: Risk/ethics review; edit for clarity; finalize executive summary and appendix artifacts.",
        "",
        "## Acceptance checks",
        "- The ordered list of canonical IDs is identical across all three outputs.",
        "- Section titles match exactly (case/punctuation stable).",
        "- Newlines are normalized (LF) and outputs are deterministic given this code.",
        "",
        "## Reference insights captured",
        "- Implication: measurement design becomes a hidden equity lever (and risk) if poorly specified/audited.",
        "- Sub-goal focus: define report scope/structure and design a 4-week agent work schedule.",
    ]
    return "
".join(lines).strip() + "
"

def _validate_ids(outline: list[dict], report_outline: str, draft: str, plan: str) -> None:
    ids = [sid for path, sid in _walk(outline) if len(path) == 1]
    for sid in ids:
        if f"(#{sid})" not in report_outline:
            raise SystemExit(f"Missing ID in REPORT_OUTLINE: {sid}")
        if f'<a id="{sid}"></a>' not in draft:
            raise SystemExit(f"Missing ID anchor in DRAFT_REPORT_v0: {sid}")
        if f"`{sid}`" not in plan:
            raise SystemExit(f"Missing ID in plan_project_scope_and_outline: {sid}")

def run(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    outline = _canon_outline()
    report_outline = _render_report_outline(outline)
    draft = _render_draft_skeleton(outline)
    plan = _render_plan(outline)
    _validate_ids(outline, report_outline, draft, plan)

    paths = {
        "plan": out_dir / "plan_project_scope_and_outline.md",
        "outline": out_dir / "REPORT_OUTLINE.md",
        "draft": out_dir / "DRAFT_REPORT_v0.md",
    }
    paths["plan"].write_text(plan, encoding="utf-8", newline="\n")
    paths["outline"].write_text(report_outline, encoding="utf-8", newline="\n")
    paths["draft"].write_text(draft, encoding="utf-8", newline="\n")
    return {k: str(v) for k, v in paths.items()}

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="plan-scope-outline", add_help=True)
    default_root = Path(__file__).resolve().parents[1]
    p.add_argument("--root", type=Path, default=default_root, help="Project root (default: repo root inferred from src/cli.py)")
    args = p.parse_args(argv)
    out_dir = args.root / "runtime" / "outputs"
    written = run(out_dir)
    sys.stdout.write("WROTE:" + ",".join(sorted(Path(v).name for v in written.values())) + "\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
