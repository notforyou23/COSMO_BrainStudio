from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import csv, json, random, statistics, time
from typing import Any, Dict, Iterable, List, Optional, Tuple
import os
os.chdir(r'/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')


VERSION = "0.1.0"

@dataclass(frozen=True)
class SurveyItem:
    id: str
    construct: str  # accuracy, reproducibility, effort, usability
    prompt: str
    response: str  # likert5, minutes, boolean, text

@dataclass(frozen=True)
class AuditField:
    id: str
    label: str
    weight: float = 1.0  # for citation-accuracy scoring

def default_survey_instrument() -> Dict[str, Any]:
    items = [
        SurveyItem("acc_1", "citation_accuracy", "I am confident my primary-source citations are correct (author, year, title, venue).", "likert5"),
        SurveyItem("acc_2", "citation_accuracy", "I can reliably link each claim to a specific primary-source passage/page.", "likert5"),
        SurveyItem("rep_1", "reproducibility", "A peer could reproduce my primary-source retrieval steps from my records.", "likert5"),
        SurveyItem("rep_2", "reproducibility", "I record enough metadata to re-locate the exact version/variant I used.", "likert5"),
        SurveyItem("eff_1", "effort", "Minutes spent per primary-source item (average, last project).", "minutes"),
        SurveyItem("eff_2", "effort", "The workflow reduces time wasted on re-finding sources and correcting citations.", "likert5"),
        SurveyItem("use_1", "usability", "The checklist/CLI is easy to learn and integrate into my writing workflow.", "likert5"),
        SurveyItem("use_2", "usability", "Provenance flags and variant numbering reduce confusion about editions/scans.", "likert5"),
        SurveyItem("open_1", "usability", "What was the most difficult step in the workflow?", "text"),
    ]
    return {"version": VERSION, "scale": {"likert5": ["1", "2", "3", "4", "5"]}, "items": [asdict(i) for i in items]}

def default_audit_schema() -> Dict[str, Any]:
    fields = [
        AuditField("author", "Author(s) match", 1.0),
        AuditField("year", "Year match", 1.0),
        AuditField("title", "Title match", 1.0),
        AuditField("container", "Journal/book/proceedings match", 0.75),
        AuditField("locators", "Volume/issue/pages/doi/url match", 1.0),
        AuditField("repository_link", "Repository citation link (stable identifier) present", 0.75),
        AuditField("variant_number", "Variant/edition number recorded", 0.75),
        AuditField("provenance_flag", "Provenance status flagged (original/scan/translation/secondary)", 0.5),
        AuditField("quote_trace", "Claim/quote traceable to exact page/folio/anchor", 1.25),
    ]
    return {"version": VERSION, "fields": [asdict(f) for f in fields]}

def default_audit_sampling_plan(seed: int = 7) -> Dict[str, Any]:
    rng = random.Random(seed)
    plan = {
        "version": VERSION,
        "design": "within-subject crossover (control workflow vs standardized workflow), counterbalanced",
        "sampling": {
            "units": "primary-source citations in manuscripts/notes",
            "sample_per_participant": {"control": 10, "intervention": 10},
            "stratify_by": ["source_type: archival/journal/book", "availability: online/physical", "language: original/translation"],
            "selection": "random within strata from each participant's project bibliography/notes",
            "seed": seed,
        },
        "audit": {"double_coding": True, "adjudication": "resolve disagreements by discussion; record final + coder disagreement rate"},
        "rng_check": [rng.random() for _ in range(3)],
    }
    return plan

def score_audit_row(row: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, float]:
    fields = schema["fields"]
    w_total = sum(float(f.get("weight", 1.0)) for f in fields)
    w_correct = 0.0
    for f in fields:
        fid, w = f["id"], float(f.get("weight", 1.0))
        v = row.get(fid)
        ok = (v is True) or (isinstance(v, (int, float)) and float(v) >= 1.0) or (isinstance(v, str) and v.strip().lower() in {"1", "true", "yes", "y"})
        if ok:
            w_correct += w
    return {"citation_accuracy_score": (w_correct / w_total) if w_total else 0.0}

def aggregate_metrics(audit_rows: Iterable[Dict[str, Any]], survey_rows: Optional[Iterable[Dict[str, Any]]] = None, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    schema = schema or default_audit_schema()
    rows = list(audit_rows)
    for r in rows:
        r.update(score_audit_row(r, schema))
    by_cond: Dict[str, List[float]] = {}
    for r in rows:
        cond = str(r.get("condition", "unknown"))
        by_cond.setdefault(cond, []).append(float(r.get("citation_accuracy_score", 0.0)))
    metrics = {"n_audit": len(rows), "citation_accuracy": {}}
    for cond, scores in by_cond.items():
        metrics["citation_accuracy"][cond] = {
            "mean": statistics.fmean(scores) if scores else 0.0,
            "sd": statistics.pstdev(scores) if len(scores) > 1 else 0.0,
            "n": len(scores),
        }
    if survey_rows is not None:
        srows = list(survey_rows)
        metrics["n_survey"] = len(srows)
        mins = [float(r["eff_1"]) for r in srows if str(r.get("eff_1", "")).strip() not in {"", "NA", "na"}]
        metrics["effort_minutes"] = {"mean": (statistics.fmean(mins) if mins else None), "n": len(mins)}
    return metrics

def export_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def export_rows_csv(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    rows = list(rows)
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

def make_analysis_ready_bundle(out_dir: Path, audit_rows: List[Dict[str, Any]], survey_rows: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = default_audit_schema()
    metrics = aggregate_metrics(audit_rows, survey_rows=survey_rows, schema=schema)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    p_schema = out_dir / f"audit_schema_{stamp}.json"
    p_plan = out_dir / f"audit_sampling_plan_{stamp}.json"
    p_audit = out_dir / f"audit_rows_{stamp}.csv"
    p_survey = out_dir / f"survey_rows_{stamp}.csv"
    p_survey_instrument = out_dir / f"survey_instrument_{stamp}.json"
    p_metrics = out_dir / f"metrics_{stamp}.json"
    export_json(p_schema, schema)
    export_json(p_plan, default_audit_sampling_plan())
    export_rows_csv(p_audit, audit_rows)
    export_json(p_survey_instrument, default_survey_instrument())
    if survey_rows is not None:
        export_rows_csv(p_survey, survey_rows)
    export_json(p_metrics, metrics)
    bundle = {"audit_schema": str(p_schema), "audit_sampling_plan": str(p_plan), "audit_rows_csv": str(p_audit), "metrics_json": str(p_metrics), "survey_instrument": str(p_survey_instrument)}
    if survey_rows is not None:
        bundle["survey_rows_csv"] = str(p_survey)
    return bundle

from pathlib import Path
import json
target_path = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution').joinpath('src/psyprim/evaluation.py')
target_path.parent.mkdir(parents=True, exist_ok=True)
chunks = [Path(__file__).read_text(encoding="utf-8") if "__file__" in globals() else ""]
if chunks == [""]:
    chunks = [""]
final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
target_path.write_text(final_text, encoding='utf-8')
print('FILE_WRITTEN:src/psyprim/evaluation.py')
print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution"))) for p in target_path.parent.glob('*') if p.is_file())))
print("Wrote evaluation scaffolding with survey instrument, audit schema/sampling plan, scoring, metrics aggregation, and analysis-ready exports.")
