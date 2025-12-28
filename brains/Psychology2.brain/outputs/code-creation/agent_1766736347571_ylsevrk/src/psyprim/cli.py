\"\"\"psyprim CLI: generate validation + adoption roadmaps for standardized primary-source workflows.\"\"\"
from __future__ import annotations
import argparse, json, sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Any, Optional

DESIGNS = {
  "survey": "Survey of primary-source practices, barriers, perceived usefulness, and willingness-to-adopt.",
  "audit": "Audit study of published articles: verify citations against primary sources; quantify error types.",
  "rct": "Randomized evaluation of tool/workflow adoption vs control on accuracy, time, and reproducibility.",
  "quasi": "Quasi-experimental rollout (stepped-wedge / diff-in-diff) using policy/tool introduction over time.",
  "logstudy": "Telemetry/log-based analysis of workflow tool usage and downstream outcomes (opt-in, privacy-preserving)."
}

METRICS = {
  "citation_accuracy": [
    "Primary-source match rate (exact bibliographic match to original item)",
    "Quotation fidelity (character/word-level edit distance vs source)",
    "Attribution correctness (who/what/where/when claims supported by cited source)",
    "Error taxonomy rates (wrong edition, secondary citation, misquote, fabricated page, miscitation)"
  ],
  "reproducibility": [
    "Re-extraction success rate (independent extractor recovers same quoted passages/metadata)",
    "Evidence trace completeness (all claims have resolvable source pointers + access instructions)",
    "Workflow replay rate (can reproduce search->retrieve->cite steps from recorded provenance)"
  ],
  "usability": [
    "Task completion time (median, p90) for find->verify->cite tasks",
    "Cognitive load (NASA-TLX short), error recovery time, learnability (sessions-to-criterion)",
    "Adoption/retention (activation rate, 4-week retention, continued use at 3/6 months)"
  ]
}

FRAMES = {
  "journals_psych": {
    "unit": "articles",
    "frame": "Psychology journals stratified by subfield, impact tier, and open-access status.",
    "sampling": "Two-stage: sample journals (stratified), then sample articles per journal-year."
  },
  "archives_primary": {
    "unit": "primary sources",
    "frame": "Archives/digital collections holding original datasets, correspondence, lab notes, early reports.",
    "sampling": "Stratify by access mode (digitized vs onsite), language, and era; sample items by collection."
  },
  "researchers": {
    "unit": "researchers",
    "frame": "Researchers (students, postdocs, faculty) doing historical/primary-source work in psychology.",
    "sampling": "Stratified by career stage, subfield, region; recruit via societies, conferences, mailing lists."
  }
}

ANALYSIS = {
  "descriptive": "Report prevalence with uncertainty (Wilson/bootstrapped CIs), stratified by frame strata.",
  "causal_rct": "Intention-to-treat; mixed effects (participant + task random intercepts); preregistered contrasts.",
  "diff_in_diff": "DiD with journal/author fixed effects; check parallel trends; cluster-robust SEs.",
  "measurement": "Inter-rater reliability (Krippendorff’s alpha/ICC), calibration of automated checks vs humans.",
  "power": "Power via simulation: specify baseline error, expected reduction, ICC; report MDE and sample size."
}

def _csv(x: Optional[str]) -> Optional[List[str]]:
  if not x: return None
  return [t.strip() for t in x.split(",") if t.strip()]

def build_roadmap(designs=None, metrics=None, frames=None, analysis=None, seed: int = 0) -> Dict[str, Any]:
  designs = designs or list(DESIGNS)
  metrics = metrics or list(METRICS)
  frames = frames or list(FRAMES)
  analysis = analysis or ["descriptive","measurement","power","causal_rct","diff_in_diff"]
  mblocks = {k: METRICS[k] for k in metrics if k in METRICS}
  fblocks = {k: FRAMES[k] for k in frames if k in FRAMES}
  ablocks = {k: ANALYSIS[k] for k in analysis if k in ANALYSIS}
  experiments: List[Dict[str, Any]] = []
  for d in designs:
    if d not in DESIGNS: continue
    ex = {"id": f"exp_{d}", "design": d, "summary": DESIGNS[d], "hypotheses": [], "sampling_frames": [], "outcomes": [], "data_collection": [], "analysis_plan": []}
    if d == "survey":
      ex["hypotheses"] = ["Higher baseline miscitation exposure predicts willingness-to-adopt standard workflow.",
                          "Perceived time-cost mediates adoption intention; defaults reduce perceived burden."]
      ex["sampling_frames"] = ["researchers"]
      ex["outcomes"] = ["intent_to_adopt", "current_practices", "barriers", "perceived_usefulness", "self_reported_errors"]
      ex["data_collection"] = ["Online survey with vignettes; conjoint/choice tasks for default settings; optional follow-up interview sample."]
      ex["analysis_plan"] = [ablocks.get("descriptive",""), "Ordinal/GLM models; conjoint AMCEs; mediation (pre-registered) with sensitivity checks."]
    elif d == "audit":
      ex["hypotheses"] = ["Non-trivial primary-source citation error rate exists across subfields; higher for older/rare sources.",
                          "Open materials and traceable provenance associate with lower error rates."]
      ex["sampling_frames"] = ["journals_psych","archives_primary"]
      ex["outcomes"] = ["primary_source_match_rate","quotation_fidelity","error_taxonomy_rates","trace_completeness"]
      ex["data_collection"] = ["Codebook-guided extraction by two independent auditors; resolve disagreements; link to source scans/records when permitted."]
      ex["analysis_plan"] = [ablocks.get("measurement",""), ablocks.get("descriptive",""), "Multilevel models (article nested in journal) to estimate correlates; preregistered coding rules."]
    elif d == "rct":
      ex["hypotheses"] = ["Tool+workflow increases citation accuracy and evidence trace completeness vs control.",
                          "Tool reduces time-to-verify after brief onboarding; usability mediates sustained use."]
      ex["sampling_frames"] = ["researchers"]
      ex["outcomes"] = ["task_time","citation_accuracy_metrics","trace_completeness","retention_4w","nasa_tlx"]
      ex["data_collection"] = ["Lab/remote tasks with standardized packets of primary sources; randomize to tool vs baseline workflow; collect artifacts and timestamps."]
      ex["analysis_plan"] = [ablocks.get("causal_rct",""), ablocks.get("power",""), "Primary endpoints: accuracy + trace completeness; secondary: time and workload; report heterogeneous effects by experience."]
    elif d == "quasi":
      ex["hypotheses"] = ["Policy or journal guideline introducing standardized workflow decreases miscitation rates over time.",
                          "Effects larger where editors enforce checklist + templates."]
      ex["sampling_frames"] = ["journals_psych"]
      ex["outcomes"] = ["miscitation_rate","traceability_rate","correction_rate","time_to_correction"]
      ex["data_collection"] = ["Collect article samples pre/post policy; scrape references and availability statements; audit subset for ground truth."]
      ex["analysis_plan"] = [ablocks.get("diff_in_diff",""), ablocks.get("descriptive",""), "Sensitivity: event-study, placebo interventions, varying bandwidths; cluster at journal or author group."]
    elif d == "logstudy":
      ex["hypotheses"] = ["Higher in-tool verification actions predict fewer downstream citation errors in audited outputs.",
                          "Default prompts reduce omission of provenance fields under time pressure."]
      ex["sampling_frames"] = ["researchers"]
      ex["outcomes"] = ["activation_rate","field_completion","verification_actions","error_rate_linked_audit"]
      ex["data_collection"] = ["Opt-in, privacy-preserving telemetry (hashed doc IDs, event counts); periodic short in-app surveys; link to audited submissions with consent."]
      ex["analysis_plan"] = [ablocks.get("descriptive",""), "Survival/retention models; mixed effects linking event patterns to outcomes; privacy threat modeling documented."]
    experiments.append(ex)
  return {
    "generated_on": str(date.today()),
    "seed": seed,
    "mission": "Validate and drive adoption of standardized, lightweight primary-source scholarship workflows in psychology by measuring citation accuracy, reproducibility, and usability under realistic constraints.",
    "metrics_library": mblocks,
    "sampling_frames": fblocks,
    "analysis_library": ablocks,
    "experiments": experiments,
    "reporting": {
      "preregistration": "OSF/AsPredicted; publish codebook, tasks, and analysis plan; specify primary endpoints and stopping rules.",
      "open_materials": "Share de-identified data where permitted; publish audit codebook + adjudication log; provide reproducible notebooks.",
      "ethics_privacy": "IRB review for human subjects and telemetry; minimize data, opt-in, and document retention/consent."
    }
  }

def to_markdown(roadmap: Dict[str, Any]) -> str:
  lines = [f"# psyprim validation & adoption roadmap", f"- Generated: {roadmap['generated_on']}", "", f"## Mission", roadmap["mission"], ""]
  lines += ["## Metrics", ""]
  for k,v in roadmap["metrics_library"].items():
    lines += [f"### {k}"] + [f"- {x}" for x in v] + [""]
  lines += ["## Sampling frames", ""]
  for k,v in roadmap["sampling_frames"].items():
    lines += [f"### {k}", f"- Unit: {v['unit']}", f"- Frame: {v['frame']}", f"- Sampling: {v['sampling']}", ""]
  lines += ["## Experiments", ""]
  for ex in roadmap["experiments"]:
    lines += [f"### {ex['id']} ({ex['design']})", ex["summary"], "", "**Hypotheses**"] + [f"- {h}" for h in ex["hypotheses"]]
    lines += ["", "**Sampling frames**"] + [f"- {s}" for s in ex["sampling_frames"]]
    lines += ["", "**Outcomes**"] + [f"- {o}" for o in ex["outcomes"]]
    lines += ["", "**Data collection**"] + [f"- {d}" for d in ex["data_collection"]]
    lines += ["", "**Analysis plan**"] + [f"- {a}" for a in ex["analysis_plan"] if a] + [""]
  lines += ["## Reporting & governance", ""]
  for k,v in roadmap["reporting"].items():
    lines += [f"- **{k}**: {v}"]
  return "\n".join(lines) + "\n"

def main(argv: Optional[List[str]] = None) -> int:
  p = argparse.ArgumentParser(prog="psyprim", description="Generate empirically grounded validation/adoption roadmaps for primary-source workflows.")
  sp = p.add_subparsers(dest="cmd", required=True)

  lp = sp.add_parser("list", help="List available designs/metrics/frames/analysis options.")
  lp.add_argument("what", choices=["designs","metrics","frames","analysis"])

  gp = sp.add_parser("generate", help="Generate a roadmap.")
  gp.add_argument("--designs", help="Comma-separated designs: " + ",".join(DESIGNS))
  gp.add_argument("--metrics", help="Comma-separated metric bundles: " + ",".join(METRICS))
  gp.add_argument("--frames", help="Comma-separated sampling frames: " + ",".join(FRAMES))
  gp.add_argument("--analysis", help="Comma-separated analysis blocks: " + ",".join(ANALYSIS))
  gp.add_argument("--format", choices=["json","md"], default="json")
  gp.add_argument("--out", help="Output path (default: stdout).")
  gp.add_argument("--indent", type=int, default=2, help="JSON indent (when --format json).")

  a = p.parse_args(argv)
  if a.cmd == "list":
    m = {"designs": DESIGNS, "metrics": METRICS, "frames": FRAMES, "analysis": ANALYSIS}[a.what]
    sys.stdout.write(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
    return 0

  roadmap = build_roadmap(_csv(a.designs), _csv(a.metrics), _csv(a.frames), _csv(a.analysis))
  out = to_markdown(roadmap) if a.format == "md" else json.dumps(roadmap, indent=a.indent, ensure_ascii=False) + "\n"
  if a.out:
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(out, encoding="utf-8")
  else:
    sys.stdout.write(out)
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
