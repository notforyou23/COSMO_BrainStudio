"""Empirical evaluation protocol generator for PsyProv.

Produces test-ready survey instruments, audit-study designs, sampling plans,
outcome metrics, and analysis templates for provenance/variant/citation workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import json
from pathlib import Path
@dataclass
class SurveyItem:
    id: str
    construct: str
    prompt: str
    response: str
    scale: Optional[str] = None


@dataclass
class SurveyInstrument:
    id: str
    audience: str
    administration: str
    items: List[SurveyItem]
    scoring: Dict[str, Any]


@dataclass
class AuditTask:
    id: str
    condition: str
    materials: str
    participant_role: str
    instructions: str
    outcomes: List[str]


@dataclass
class SamplingPlan:
    strata: List[Dict[str, Any]]
    recruitment: Dict[str, Any]
    inclusion_exclusion: Dict[str, Any]
    target_n: Dict[str, int]


@dataclass
class OutcomeMetrics:
    primary: List[Dict[str, Any]]
    secondary: List[Dict[str, Any]]
    quality_checks: List[Dict[str, Any]]


@dataclass
class AnalysisTemplate:
    prereg_questions: List[str]
    models: List[Dict[str, Any]]
    reporting: List[str]
    example_code: Dict[str, str]
def default_protocol(version: str = "1.0") -> Dict[str, Any]:
    """Return a concrete, testable protocol specification as a JSON-ready dict."""
    surveys = [
        SurveyInstrument(
            id="S1_usability_authors",
            audience="primary-source scholars/authors",
            administration="post-task (10–12 min); Likert + short free text",
            items=[
                SurveyItem("S1_Q1", "task_success", "I could identify the edition/translation used.", "Likert", "1–7"),
                SurveyItem("S1_Q2", "task_success", "I could reconcile page/paragraph variants across editions.", "Likert", "1–7"),
                SurveyItem("S1_Q3", "trust", "I trust the tool's provenance inference and citations.", "Likert", "1–7"),
                SurveyItem("S1_Q4", "effort", "The workflow reduced effort vs my usual process.", "Likert", "1–7"),
                SurveyItem("S1_Q5", "error_visibility", "When uncertain, the tool made uncertainty explicit.", "Likert", "1–7"),
                SurveyItem("S1_Q6", "open", "Describe the hardest step and what evidence you needed.", "FreeText"),
            ],
            scoring={"scales": {"task_success": ["S1_Q1", "S1_Q2"], "trust": ["S1_Q3"], "effort": ["S1_Q4"], "transparency": ["S1_Q5"]}},
        ),
        SurveyInstrument(
            id="S2_archivists_librarians",
            audience="archivists/librarians/repository staff",
            administration="remote (15 min); policy + metadata adequacy",
            items=[
                SurveyItem("S2_Q1", "metadata_fit", "Proposed fields match repository citation needs.", "Likert", "1–7"),
                SurveyItem("S2_Q2", "provenance", "Edition/translation provenance fields are unambiguous.", "Likert", "1–7"),
                SurveyItem("S2_Q3", "pd_status", "Public-domain claims are appropriately evidenced.", "Likert", "1–7"),
                SurveyItem("S2_Q4", "open", "Which fields are missing/overly burdensome?", "FreeText"),
            ],
            scoring={"scales": {"metadata_fit": ["S2_Q1", "S2_Q2", "S2_Q3"]}},
        ),
        SurveyInstrument(
            id="S3_journal_partners",
            audience="journal editors/reviewers/production staff",
            administration="scenario-based (10 min); adoption + enforcement",
            items=[
                SurveyItem("S3_Q1", "policy", "I would support requiring this provenance block in submissions.", "Likert", "1–7"),
                SurveyItem("S3_Q2", "review_burden", "The workflow reduces reviewer burden verifying citations.", "Likert", "1–7"),
                SurveyItem("S3_Q3", "compliance", "I can see how to audit compliance using the exported report.", "Likert", "1–7"),
                SurveyItem("S3_Q4", "open", "What would block adoption in your journal?", "FreeText"),
            ],
            scoring={"scales": {"adoption": ["S3_Q1", "S3_Q2", "S3_Q3"]}},
        ),
    ]

    audit_tasks = [
        AuditTask(
            id="A1_blinded_extraction",
            condition="control: manual; treatment: plugin-assisted",
            materials="20 primary-source excerpts with known gold provenance + variant anchors",
            participant_role="authors with prior primary-source citation experience",
            instructions="For each excerpt, cite the primary source with edition/translation provenance, variant page/paragraph anchors, and repository citation.",
            outcomes=["accuracy_provenance", "accuracy_variant_anchor", "citation_completeness", "time_on_task", "confidence"],
        ),
        AuditTask(
            id="A2_repository_traceback",
            condition="within-subject: tool export vs PDF-only",
            materials="10 public-domain repository items (IA/Hathi/Gutenberg/etc.) with stable identifiers; include 3 tricky multi-scan editions",
            participant_role="research assistants / librarians",
            instructions="Reconstruct the exact item used (scan/edition/translation) and verify PD-repository citation integrity.",
            outcomes=["traceback_success", "identifier_validity", "pd_evidence_presence", "notes_discrepancies"],
        ),
        AuditTask(
            id="A3_false_positive_challenge",
            condition="adversarial set: near-duplicate editions/translations",
            materials="Pairs of visually similar title pages/OCR with differing translator/year/publisher; include multilingual",
            participant_role="authors",
            instructions="Use the tool to infer provenance; flag uncertainty; select best match and evidence.",
            outcomes=["fp_rate", "uncertainty_calibration", "evidence_quality_score"],
        ),
    ]

    sampling = SamplingPlan(
        strata=[
            {"name": "language", "levels": ["EN", "DE", "FR"], "min_per_level": 10},
            {"name": "era", "levels": ["1850-1899", "1900-1949", "1950-1970"], "min_per_level": 10},
            {"name": "source_type", "levels": ["book", "journal_article", "chapter/collected"], "min_per_level": 8},
            {"name": "repository", "levels": ["InternetArchive", "HathiTrust", "Gutenberg", "Wikimedia", "Institutional"], "min_per_level": 6},
        ],
        recruitment={
            "channels": ["society listservs", "journal partners", "library networks", "graduate methods courses"],
            "incentives": {"authors": "gift card or donation", "librarians": "professional development credit if feasible"},
        },
        inclusion_exclusion={
            "include": ["basic citation literacy", "access to web browser", "consent to screen recording for task timing (optional)"],
            "exclude": ["conflicts of interest with tool developers (for blinded conditions)", "inability to read task language set"],
        },
        target_n={"authors": 60, "librarians": 20, "editors_reviewers": 20},
    )

    metrics = OutcomeMetrics(
        primary=[
            {"name": "accuracy_provenance", "type": "binary/ordinal", "definition": "correct edition+translation match to gold", "unit": "per-item"},
            {"name": "accuracy_variant_anchor", "type": "ordinal", "definition": "anchor matches gold mapping across editions (page/para)", "unit": "per-item"},
            {"name": "citation_completeness", "type": "score", "definition": "required fields present + identifiers resolvable", "unit": "0–10"},
            {"name": "time_on_task", "type": "continuous", "definition": "seconds per excerpt/task", "unit": "seconds"},
        ],
        secondary=[
            {"name": "trust_scale", "type": "Likert mean", "definition": "mean of trust items", "unit": "1–7"},
            {"name": "uncertainty_calibration", "type": "Brier-like", "definition": "alignment of stated confidence with correctness", "unit": "0–1"},
            {"name": "interrater_agreement", "type": "kappa/ICC", "definition": "agreement on provenance decisions across raters", "unit": "kappa/ICC"},
        ],
        quality_checks=[
            {"name": "attention_checks", "definition": "1–2 items with instructed response", "threshold": ">=1 pass"},
            {"name": "gold_set_integrity", "definition": "gold labels verified by 2 independent experts", "threshold": "100% reconciled"},
        ],
    )

    analysis = AnalysisTemplate(
        prereg_questions=[
            "Does plugin assistance improve provenance accuracy vs control?",
            "Does plugin assistance reduce time-on-task without reducing accuracy?",
            "Are uncertainty estimates better calibrated in treatment?",
            "Which strata (language/era/repository) show the largest error modes?",
        ],
        models=[
            {"name": "mixed_logit_accuracy", "dv": "accuracy_provenance", "iv": ["condition"], "random_effects": ["participant", "item"], "link": "logit"},
            {"name": "mixed_linear_time", "dv": "log_time_on_task", "iv": ["condition"], "random_effects": ["participant", "item"]},
            {"name": "ordinal_variant", "dv": "accuracy_variant_anchor", "iv": ["condition"], "random_effects": ["participant", "item"], "family": "ordinal"},
        ],
        reporting=[
            "Report effect sizes with 95% CIs; include per-stratum error tables and confusion matrices for provenance matches.",
            "Publish anonymized task logs + gold labels where licensing permits; otherwise publish derived metrics and hashed identifiers.",
            "Document failure cases: OCR noise, title-page ambiguity, multiple scans/editions, translator mismatches, repository URL rot.",
        ],
        example_code={
            "python": "import pandas as pd\nimport statsmodels.formula.api as smf\n# df: one row per item x participant\n# df['condition'] in {0,1}\n# Mixed models: consider pymer4 or bambi for GLMM\n",
            "r": "library(lme4)\n# glmer(accuracy ~ condition + (1|participant) + (1|item), data=df, family=binomial)\n",
        },
    )

    return {
        "protocol_id": "psyprov_eval",
        "version": version,
        "ethics": {
            "consent": "informed consent; optional screen recording; store de-identified logs",
            "privacy": "minimize collected personal data; separate consent keys from task logs",
            "risk": "minimal; primary risk is confidentiality of unpublished manuscripts",
        },
        "survey_instruments": [asdict(s) for s in surveys],
        "audit_studies": [asdict(a) for a in audit_tasks],
        "sampling_plan": asdict(sampling),
        "outcome_metrics": asdict(metrics),
        "analysis_template": asdict(analysis),
    }
def export_protocol(path: str | Path, protocol: Optional[Dict[str, Any]] = None) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    protocol = protocol or default_protocol()
    p.write_text(json.dumps(protocol, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def protocol_markdown_brief(protocol: Optional[Dict[str, Any]] = None) -> str:
    pr = protocol or default_protocol()
    s = pr["sampling_plan"]["target_n"]
    m = [x["name"] for x in pr["outcome_metrics"]["primary"]]
    return (
        f"# PsyProv Evaluation Protocol v{pr['version']}\n\n"
        f"## Targets\n- Authors: {s['authors']}  Librarians: {s['librarians']}  Editors/Reviewers: {s['editors_reviewers']}\n\n"
        f"## Primary outcomes\n" + "".join([f"- {x}\n" for x in m]) + "\n"
        "## Audit tasks\n" + "".join([f"- {a['id']}: {a['condition']}\n" for a in pr["audit_studies"]])
    )


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="psyprov-eval-protocol")
    ap.add_argument("--out", default="psyprov_protocol.json", help="Output JSON path")
    ap.add_argument("--md", action="store_true", help="Print a short markdown brief to stdout")
    ns = ap.parse_args(argv)
    out_path = export_protocol(ns.out)
    if ns.md:
        print(protocol_markdown_brief())
    else:
        print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
