from __future__ import annotations
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
COVERAGE_CSV = OUTPUTS / "coverage_matrix.csv"
EVAL_MD = OUTPUTS / "eval_loop.md"
ROADMAP_MD = OUTPUTS / "roadmap_v1.md"

START = "<!-- GENERATED_ARTIFACT_LINKS:START -->"
END = "<!-- GENERATED_ARTIFACT_LINKS:END -->"

def ensure_outputs():
    OUTPUTS.mkdir(parents=True, exist_ok=True)

def write_coverage_csv():
    domains = {
        "Strategy & Roadmap": ["Objectives", "Milestones", "Risks & Mitigations", "Dependencies"],
        "Data & Labeling": ["Data sources", "Schema/contracts", "Labeling policy", "Quality checks"],
        "Modeling": ["Baselines", "Training", "Evaluation", "Ablations"],
        "Safety & Policy": ["Guardrails", "Red-teaming", "Privacy", "Compliance"],
        "Infra & MLOps": ["CI/CD", "Experiment tracking", "Serving", "Monitoring"],
        "Product & UX": ["User needs", "Interaction design", "Feedback loops", "Docs & support"],
        "Research": ["Infrastructure lemmas", "Decomposition", "Structured+pseudorandom", "Implications"],
    }
    artifact_types = ["spec", "dataset", "notebook", "benchmark", "report", "dashboard", "runbook"]
    rows = []
    for d, subs in domains.items():
        for s in subs:
            for a in artifact_types:
                rows.append({
                    "domain": d,
                    "subtopic": s,
                    "artifact_type": a,
                    "status": "planned",
                    "links": "",
                })
    with COVERAGE_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["domain", "subtopic", "artifact_type", "status", "links"])
        w.writeheader()
        w.writerows(rows)

def write_eval_loop_md():
    text = """# Evaluation loop (5-cycle cadence)

This document defines a lightweight, repeating review loop to improve quality while preventing scope creep.

## Cycle cadence (repeat every cycle)
1. **Plan (Day 1)**: confirm targets, freeze inputs, define success criteria for this cycle.
2. **Build (Days 2–3)**: implement changes; keep a changelog entry for each hypothesis.
3. **Evaluate (Day 4)**: run the evaluation suite; record metrics + qualitative findings.
4. **Review (Day 5)**: decision meeting (ship / iterate / rollback); update coverage matrix statuses.
5. **Harden (Day 6)**: documentation/runbooks, monitoring hooks, and regression tests.

## Required metrics (track every cycle)
- **Outcome**: task success rate (or top-line KPI), paired with confidence intervals when possible.
- **Quality**: error taxonomy counts (top 5), severity-weighted.
- **Reliability**: p95 latency, timeout rate, crash rate.
- **Cost**: cost per successful task, GPU/CPU hours, storage growth.
- **Safety**: policy violation rate, privacy incidents, jailbreak/red-team pass rate.
- **Drift**: input distribution shift indicators; data freshness.

## Acceptance gates (minimum to ship)
- No regression > **1% absolute** in top-line KPI (unless explicitly approved).
- No increase in **high-severity** error count.
- Latency p95 within the agreed SLO band.
- Safety metrics at/above prior baseline; no new P0/P1 issues.

## Deprioritization rules (when to stop or pause work)
Pause or drop an initiative if any of the following holds for **2 consecutive cycles**:
- ROI is negative: cost increases while KPI is flat or decreasing.
- Improvements are within noise: KPI delta < **0.3% absolute** and CI overlaps baseline.
- Complexity is rising: added maintenance burden without commensurate benefit.
- Risk is rising: safety/compliance exposure increases or cannot be bounded.
- Dependencies blocked: critical upstream changes are >1 cycle out.

## Artifacts to update each cycle
- `outputs/coverage_matrix.csv`: status transitions (planned → in_progress → done / parked).
- Evaluation notes: experiment IDs, datasets, prompts/configs, and diffs.
- Roadmap: reflect decisions and rationale.
"""
    EVAL_MD.write_text(text.strip() + "\n", encoding="utf-8")

def upsert_roadmap_links():
    link_block = "\n".join([
        START,
        "## Generated artifacts",
        "- [coverage_matrix.csv](coverage_matrix.csv)",
        "- [eval_loop.md](eval_loop.md)",
        END,
        "",
    ])
    if not ROADMAP_MD.exists():
        ROADMAP_MD.write_text("# Roadmap v1\n\n" + link_block, encoding="utf-8")
        return
    existing = ROADMAP_MD.read_text(encoding="utf-8")
    if START in existing and END in existing:
        pre = existing.split(START, 1)[0].rstrip() + "\n"
        post = existing.split(END, 1)[1].lstrip()
        ROADMAP_MD.write_text(pre + link_block + post, encoding="utf-8")
    else:
        new_text = existing.rstrip() + "\n\n" + link_block
        ROADMAP_MD.write_text(new_text, encoding="utf-8")

def main():
    ensure_outputs()
    write_coverage_csv()
    write_eval_loop_md()
    upsert_roadmap_links()

if __name__ == "__main__":
    main()
