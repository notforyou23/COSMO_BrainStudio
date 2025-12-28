"""rollout.py

Phased rollout planner for provenance-aware primary-source psychology scholarship.

Produces a structured rollout plan with:
- timelines (date ranges per phase),
- governance checkpoints,
- adoption targets,
- evaluation milestones (usage, endorsements, quality/accuracy thresholds).

Pure-Python, dependency-free; intended for use by the project CLI.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _add_days(d: date, days: int) -> date:
    return d + timedelta(days=days)


def _iso(d: date) -> str:
    return d.isoformat()


@dataclass(frozen=True)
class Milestone:
    name: str
    kind: str  # governance | adoption | evaluation | deliverable
    due: str  # ISO date
    success_criteria: Dict[str, Any]
    owner: str = "TBD"
    notes: str = ""


@dataclass(frozen=True)
class Phase:
    id: str
    title: str
    start: str  # ISO date
    end: str  # ISO date
    goals: List[str]
    milestones: List[Milestone]


@dataclass(frozen=True)
class RolloutPlan:
    start_date: str
    cadence_days: int
    governance: Dict[str, Any]
    metrics: Dict[str, Any]
    phases: List[Phase]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["phases"] = [
            {
                **{k: v for k, v in asdict(p).items() if k != "milestones"},
                "milestones": [asdict(m) for m in p.milestones],
            }
            for p in self.phases
        ]
        return d


def default_governance() -> Dict[str, Any]:
    return {
        "bodies": {
            "SteeringCommittee": {
                "purpose": "Set scope, approve releases, manage conflicts, steward endorsements.",
                "composition": [
                    "primary-source psychology scholars (2-4)",
                    "digital library/repository staff (2-4)",
                    "metadata/provenance specialists (1-2)",
                    "tooling maintainers (1-2)",
                    "publisher/rights advisor (optional)",
                ],
                "cadence": "monthly (or per-phase checkpoints)",
            },
            "TechnicalWorkingGroup": {
                "purpose": "Draft checklists/schemas; specify plugin APIs; define test suites; triage issues.",
                "composition": ["engineers", "metadata librarians", "power users"],
                "cadence": "biweekly during drafts/pilots",
            },
            "CommunityReviewPanel": {
                "purpose": "Provide structured review; validate usability; endorse releases.",
                "composition": ["journals", "societies", "archives", "public-domain repositories"],
                "cadence": "per-RFC windows",
            },
        },
        "decision_rules": {
            "RFC": "Open RFC with change log; minimum review window; response matrix required.",
            "release": "Steering approves when validation thresholds met and at least N endorsements acquired.",
            "deprecation": "Announce 90 days; provide migration notes; maintain backwards compatibility when possible.",
        },
        "artifact_registry": {
            "protocols": "versioned checklist + metadata schema with semantic versioning",
            "plugins": "versioned releases with changelogs and reproducible test reports",
            "test_corpus": "frozen evaluation corpora snapshots with license notes",
        },
    }


def default_metrics() -> Dict[str, Any]:
    return {
        "usage": {
            "active_users_30d": {"definition": "distinct users running tooling in last 30 days"},
            "records_annotated": {"definition": "documents with provenance annotations emitted"},
            "repos_integrated": {"definition": "repositories exporting/accepting schema"},
            "plugin_installs": {"definition": "install/activation count across integrations"},
        },
        "quality": {
            "provenance_detection_precision": {"target": 0.90, "min": 0.85},
            "provenance_detection_recall": {"target": 0.85, "min": 0.75},
            "pagination_marker_accuracy": {"target": 0.95, "min": 0.90},
            "citation_resolution_rate": {"target": 0.98, "min": 0.95},
            "metadata_completeness_rate": {"target": 0.90, "min": 0.80},
        },
        "endorsements": {
            "org_endorsements": {"definition": "societies/journals/libraries endorsing v1"},
            "repo_partnerships": {"definition": "public-domain repositories participating in pilots"},
        },
    }


def _m(name: str, kind: str, due: date, criteria: Dict[str, Any], owner: str = "TBD", notes: str = "") -> Milestone:
    return Milestone(name=name, kind=kind, due=_iso(due), success_criteria=criteria, owner=owner, notes=notes)


def build_rollout_plan(
    start: Optional[date] = None,
    cadence_days: int = 60,
    endorsement_target_v1: int = 8,
    repos_target_v1: int = 5,
    installs_target_v1: int = 250,
) -> RolloutPlan:
    """Create a rollout plan with measurable phase outputs.

    cadence_days: default duration for each phase; adjust in CLI as needed.
    """
    start = start or date.today()
    gov = default_governance()
    metrics = default_metrics()

    def phase_window(i: int) -> Tuple[date, date]:
        s = _add_days(start, i * cadence_days)
        e = _add_days(s, cadence_days - 1)
        return s, e

    phases: List[Phase] = []

    # Phase 0: Scoping & stakeholder mobilization
    s, e = phase_window(0)
    phases.append(
        Phase(
            id="P0",
            title="Scoping, stakeholder map, and charter",
            start=_iso(s),
            end=_iso(e),
            goals=[
                "Identify stakeholders (societies, journals, repositories, tool maintainers, educators).",
                "Agree on scope boundaries (editions/translations, pagination/paragraph markers, citations).",
                "Publish governance charter, RFC process, and artifact registry structure.",
            ],
            milestones=[
                _m(
                    "Kickoff workshop + problem framing",
                    "governance",
                    _add_days(s, 14),
                    {"attendance_min": 25, "represented_sectors_min": 4, "notes_published": True},
                    notes="Structured agenda: needs, failure modes, terminology alignment.",
                ),
                _m(
                    "Charter ratified",
                    "governance",
                    _add_days(s, 45),
                    {"steering_committee_formed": True, "rfc_process_published": True},
                ),
                _m(
                    "Pilot partners recruited",
                    "adoption",
                    _add_days(e, 0),
                    {"pilot_repos_min": 3, "pilot_labs_or_courses_min": 2, "mou_templates_ready": True},
                ),
            ],
        )
    )

    # Phase 1: Draft protocols + technical requirements + baseline corpora
    s, e = phase_window(1)
    phases.append(
        Phase(
            id="P1",
            title="Draft v0 protocols and technical specs",
            start=_iso(s),
            end=_iso(e),
            goals=[
                "Draft checklist + metadata schema for edition/translation provenance and repository citations.",
                "Specify paragraph/page marker representation and cross-edition mapping rules.",
                "Define plugin interfaces and minimal conformance test suite; assemble evaluation corpora.",
            ],
            milestones=[
                _m(
                    "Schema v0.1 + checklist v0.1 published (RFC-1)",
                    "deliverable",
                    _add_days(s, 30),
                    {"artifacts_published": True, "rfc_window_days_min": 21},
                ),
                _m(
                    "Test corpus snapshot + labeling guide",
                    "deliverable",
                    _add_days(s, 45),
                    {"docs_min": 200, "langs_min": 2, "licenses_documented": True},
                ),
                _m(
                    "Baseline measurement report",
                    "evaluation",
                    _add_days(e, 0),
                    {"baseline_precision_recall_reported": True, "known_failure_modes_listed": True},
                ),
            ],
        )
    )

    # Phase 2: Pilot implementations + usability validation
    s, e = phase_window(2)
    phases.append(
        Phase(
            id="P2",
            title="Pilot tooling and validation studies",
            start=_iso(s),
            end=_iso(e),
            goals=[
                "Release lightweight plugin prototypes (detection + annotation + export).",
                "Run surveys on protocol usability and clarity; conduct audit study on annotation accuracy.",
                "Iterate with pilots; tighten conformance tests and error taxonomy.",
            ],
            milestones=[
                _m(
                    "Plugin prototype alpha released",
                    "deliverable",
                    _add_days(s, 21),
                    {"integrations_min": 2, "export_formats_min": 2, "conformance_tests_run": True},
                ),
                _m(
                    "Survey study completed (protocol usability)",
                    "evaluation",
                    _add_days(s, 45),
                    {"n_min": 60, "roles_covered_min": 3, "sus_score_target_min": 70},
                    notes="Include cognitive-load questions; measure reliance on defaults and need for guardrails.",
                ),
                _m(
                    "Audit study completed (annotation correctness)",
                    "evaluation",
                    _add_days(e, 0),
                    {
                        "double_coding_rate_min": 0.20,
                        "inter_annotator_agreement_min": 0.75,
                        "meets_quality_thresholds": True,
                    },
                ),
            ],
        )
    )

    # Phase 3: Release candidate + endorsement drive
    s, e = phase_window(3)
    phases.append(
        Phase(
            id="P3",
            title="Release candidate and endorsement campaign",
            start=_iso(s),
            end=_iso(e),
            goals=[
                "Stabilize v1 release candidate based on validation results.",
                "Secure community endorsements from societies/journals/libraries; publish guidance for adoption.",
                "Prepare migration notes and compliance badges for repositories/tools.",
            ],
            milestones=[
                _m(
                    "v1.0 RC published (RFC-2)",
                    "deliverable",
                    _add_days(s, 21),
                    {"rfc_window_days_min": 21, "breaking_changes_documented": True},
                ),
                _m(
                    "Endorsement commitments collected",
                    "adoption",
                    _add_days(s, 50),
                    {"org_endorsements_min": max(3, endorsement_target_v1 // 2), "public_letters_posted": True},
                ),
                _m(
                    "Quality gate passed for v1",
                    "evaluation",
                    _add_days(e, 0),
                    {
                        "precision_min": metrics["quality"]["provenance_detection_precision"]["min"],
                        "recall_min": metrics["quality"]["provenance_detection_recall"]["min"],
                        "pagination_accuracy_min": metrics["quality"]["pagination_marker_accuracy"]["min"],
                        "citation_resolution_min": metrics["quality"]["citation_resolution_rate"]["min"],
                    },
                ),
            ],
        )
    )

    # Phase 4: v1 launch + scale-out adoption + continuous evaluation
    s, e = phase_window(4)
    phases.append(
        Phase(
            id="P4",
            title="v1 launch and scale adoption",
            start=_iso(s),
            end=_iso(e),
            goals=[
                "Launch v1 protocols and stable plugin releases; publish reference implementations.",
                "Drive adoption across repositories, course syllabi, and journals' author guidelines.",
                "Operate monitoring: usage metrics, issue triage, periodic audits, and minor releases.",
            ],
            milestones=[
                _m(
                    "v1.0 released + governance sign-off",
                    "governance",
                    _add_days(s, 7),
                    {"steering_vote_recorded": True, "release_notes_published": True},
                ),
                _m(
                    "Adoption milestone (first 90 days)",
                    "adoption",
                    _add_days(s, 90),
                    {
                        "org_endorsements_min": endorsement_target_v1,
                        "repos_integrated_min": repos_target_v1,
                        "plugin_installs_min": installs_target_v1,
                        "records_annotated_min": 5000,
                    },
                ),
                _m(
                    "Post-launch audit + dashboard report",
                    "evaluation",
                    _add_days(e, 0),
                    {
                        "quality_thresholds_met": True,
                        "support_ticket_rate_target_max_per_100": 5,
                        "schema_breakages": 0,
                    },
                    notes="Repeatable audit sampling; publish dashboard definitions and known limitations.",
                ),
            ],
        )
    )

    return RolloutPlan(
        start_date=_iso(start),
        cadence_days=cadence_days,
        governance=gov,
        metrics=metrics,
        phases=phases,
    )


def plan_summary(plan: RolloutPlan) -> Dict[str, Any]:
    phases = plan.phases
    return {
        "start_date": plan.start_date,
        "cadence_days": plan.cadence_days,
        "phase_count": len(phases),
        "date_range": {"start": phases[0].start if phases else None, "end": phases[-1].end if phases else None},
        "milestone_count": sum(len(p.milestones) for p in phases),
        "adoption_targets_v1": _extract_v1_targets(phases),
    }


def _extract_v1_targets(phases: Sequence[Phase]) -> Dict[str, Any]:
    for p in phases:
        if p.id == "P4":
            for m in p.milestones:
                if "org_endorsements_min" in m.success_criteria:
                    return dict(m.success_criteria)
    return {}


def validate_plan(plan: RolloutPlan) -> List[str]:
    issues: List[str] = []
    if not plan.phases:
        issues.append("no_phases")
        return issues
    # Monotonic phase windows and milestone deadlines within phase or shortly after.
    prev_end: Optional[str] = None
    for p in plan.phases:
        if prev_end and p.start < prev_end:
            issues.append(f"phase_overlap:{p.id}")
        prev_end = p.end
        for m in p.milestones:
            if m.due < p.start:
                issues.append(f"milestone_before_phase:{p.id}:{m.name}")
    # Ensure at least one milestone of each type.
    kinds = {m.kind for p in plan.phases for m in p.milestones}
    for k in ("governance", "adoption", "evaluation", "deliverable"):
        if k not in kinds:
            issues.append(f"missing_kind:{k}")
    return issues
