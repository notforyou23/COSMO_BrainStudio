"""psyprim.roadmap: assemble empirically grounded validation + adoption roadmap plans.

Focus: standardized primary-source scholarship workflows + lightweight tooling in psychology.
Outputs are JSON-serializable dicts suitable for CLI rendering/writing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import datetime as _dt


def _today() -> str:
    return _dt.date.today().isoformat()


def default_metrics() -> Dict[str, Any]:
    return {
        "citation_accuracy": {
            "definition": "Match between cited primary-source claim and source text; includes quotation fidelity and claim attribution.",
            "operationalization": [
                "Binary correctness (correct/incorrect) per claim-source link.",
                "Error taxonomy: wrong source, wrong page/section, paraphrase drift, quote altered, secondary-source laundering.",
                "Severity: minor (metadata), moderate (interpretation), major (claim reversed/unsupported).",
            ],
            "indices": ["accuracy_rate", "major_error_rate", "laundering_rate"],
        },
        "reproducibility": {
            "definition": "Ability to reproduce the evidence trail from claim to archival artifact using recorded workflow.",
            "operationalization": [
                "Time-to-locate primary artifact (minutes).",
                "Success locating exact passage/artifact (yes/no).",
                "Completeness of provenance fields (archive, call number/URL, date accessed, version hash).",
            ],
            "indices": ["locatability_rate", "median_time_to_locate", "provenance_completeness"],
        },
        "usability": {
            "definition": "Efficiency, cognitive load, and perceived usefulness of the workflow/tooling.",
            "operationalization": [
                "System Usability Scale (SUS).",
                "NASA-TLX (or short-form) for workload.",
                "Task success and task time on standardized extraction/citation tasks.",
            ],
            "indices": ["sus_score", "task_success_rate", "median_task_time", "nasa_tlx"],
        },
        "adoption": {
            "definition": "Sustained use and integration into researchers' routine practices.",
            "operationalization": [
                "Activation: first project created within 7 days.",
                "Retention: active use at 30/90 days.",
                "Shareability: proportion producing exportable evidence packs (e.g., JSON/CSV + cited artifacts).",
            ],
            "indices": ["activation_rate", "retention_30d", "retention_90d", "evidence_pack_rate"],
        },
    }


def default_sampling_frames() -> Dict[str, Any]:
    return {
        "journals": {
            "scope": "Psychology journals emphasizing narrative review, theory, or historical/archival claims.",
            "frames": [
                "Top-cited general psychology journals (impact/visibility stratum).",
                "Specialty journals with frequent historical/theoretical citations (e.g., social/personality, clinical, developmental).",
                "Open-access vs subscription stratification to test accessibility effects.",
            ],
            "units": ["article", "claim", "citation"],
        },
        "archives": {
            "scope": "Primary-source repositories used in psychology scholarship.",
            "frames": [
                "Major digital libraries (e.g., HathiTrust/Internet Archive equivalents).",
                "University special collections with psychology holdings.",
                "Publisher-hosted historical archives (journal backfiles).",
            ],
            "units": ["artifact", "passage", "metadata record"],
        },
        "researchers": {
            "scope": "Populations producing or consuming primary-source claims.",
            "frames": [
                "Graduate students (methods + writing-intensive courses).",
                "Postdocs/early-career faculty (high throughput).",
                "Senior scholars/editors/reviewers (policy leverage).",
            ],
            "units": ["individual", "lab", "course cohort"],
        },
    }


def default_study_templates() -> List[Dict[str, Any]]:
    m = default_metrics()
    sf = default_sampling_frames()
    return [
        {
            "id": "survey_needs_barriers",
            "type": "survey",
            "purpose": "Measure current practices, barriers, and demand for standardized primary-source workflows.",
            "design": {
                "sampling_frame": sf["researchers"],
                "method": "Online survey with vignette-based items (claim verification scenarios) + scales.",
                "core_measures": ["self-reported practices", "perceived norms", "barriers", "tool readiness", "SUS for prototypes"],
                "recommended_n": {"min": 200, "target": 600},
            },
            "metrics": {"usability": m["usability"], "adoption": m["adoption"]},
            "analysis": {
                "models": [
                    "Ordinal/logistic regression for willingness-to-adopt vs barriers.",
                    "Factor analysis for barrier structure; reliability (alpha/omega).",
                    "Measurement invariance across career stages.",
                ],
                "notes": "Pre-register hypotheses; include attention checks; weight strata if needed.",
            },
        },
        {
            "id": "audit_citation_accuracy",
            "type": "audit_study",
            "purpose": "Estimate baseline citation accuracy and primary-source laundering in psychology articles.",
            "design": {
                "sampling_frame": sf["journals"],
                "method": "Two-coder audit of sampled claims with adjudication; blinded to journal condition.",
                "sampling": "Stratified random sample of articles; within-article sample of primary-source claims/citations.",
                "recommended_n": {"articles": 120, "claims_per_article": 8},
                "coder_training": "Codebook + calibration set; require kappa/alpha >= 0.70 before production coding.",
            },
            "metrics": {"citation_accuracy": m["citation_accuracy"], "reproducibility": m["reproducibility"]},
            "analysis": {
                "models": [
                    "Multilevel logistic model (claim nested in article/journal) for error probability.",
                    "Interrater reliability (Krippendorff's alpha); bootstrap CIs for rates.",
                    "Sensitivity: exclude ambiguous claims; report robustness.",
                ]
            },
        },
        {
            "id": "rct_tool_adoption_effect",
            "type": "adoption_experiment",
            "purpose": "Causal test: whether the workflow/tool improves citation accuracy and evidence-trail reproducibility.",
            "design": {
                "sampling_frame": sf["researchers"],
                "method": "Randomized controlled trial with standardized tasks (extract, cite, export evidence pack).",
                "arms": [
                    {"name": "control", "description": "Status-quo tools (PDF + reference manager)."},
                    {"name": "treatment", "description": "Standardized workflow + lightweight tooling + default templates."},
                ],
                "outcomes_primary": ["accuracy_rate", "locatability_rate", "median_time_to_locate"],
                "outcomes_secondary": ["sus_score", "nasa_tlx", "evidence_pack_rate"],
                "recommended_n": {"min_per_arm": 60, "target_per_arm": 120},
                "randomization": "Blocked by career stage; conceal allocation until onboarding complete.",
            },
            "metrics": {"citation_accuracy": m["citation_accuracy"], "reproducibility": m["reproducibility"], "usability": m["usability"], "adoption": m["adoption"]},
            "analysis": {
                "models": [
                    "ITT analysis; mixed models for repeated tasks; robust SEs.",
                    "Mediation: usability/workload -> adoption -> accuracy.",
                    "Heterogeneity: accessibility of sources, domain, prior experience.",
                ],
                "data_quality": "Instrument tasks; log events; preregister exclusion rules; blinded scoring of accuracy.",
            },
        },
    ]


def assemble_roadmap(
    studies: Optional[List[str]] = None,
    horizon_months: int = 12,
    context: str = "psychology_primary_source_scholarship",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    templates = {s["id"]: s for s in default_study_templates()}
    selected = [templates[i] for i in (studies or list(templates.keys())) if i in templates]
    plan = {
        "context": context,
        "created": _today(),
        "horizon_months": int(horizon_months),
        "metrics_library": default_metrics(),
        "sampling_frames": default_sampling_frames(),
        "studies": selected,
        "governance": {
            "open_science": ["preregistration", "shared codebooks", "anonymized datasets where feasible", "reproducible analysis scripts"],
            "ethics": ["IRB/ethics review for human subjects", "data minimization", "secure storage", "consent for telemetry"],
            "reporting": ["CONSORT-style flow for experiments", "STROBE-style for audits", "transparent error taxonomy"],
        },
        "decision_thresholds": {
            "adopt_if": {
                "accuracy_rate_delta": ">= +0.10 absolute (treatment-control)",
                "major_error_rate_delta": "<= -0.05 absolute",
                "locatability_rate_delta": ">= +0.15 absolute",
                "sus_score": ">= 70 and not worse than control by >5 points",
            }
        },
    }
    if extra:
        plan["extra"] = dict(extra)
    return plan


@dataclass(frozen=True)
class RoadmapBundle:
    plan: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return self.plan

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.plan, ensure_ascii=False, indent=indent, sort_keys=False)
