from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple
import hashlib
import datetime as _dt

def _stable_id(*parts: str, n: int = 10) -> str:
    h = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
    return h[:n]

def _today() -> str:
    return _dt.date.today().isoformat()

@dataclass(frozen=True)
class ZPDSupport:
    support_type: str  # e.g., modeling, prompting, worked_example, feedback, peer_support
    timing: str        # e.g., pre-task, in-task, post-task, just-in-time
    fading: str        # e.g., none, fixed, performance_contingent, adaptive
    dose_minutes: int = 10
    contingencies: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class Arm:
    name: str
    modality: str  # choice_architecture, debiasing, sleep_restoration
    description: str
    zpd: ZPDSupport
    components: Dict[str, Any]
    fidelity: Dict[str, Any]

@dataclass(frozen=True)
class Measure:
    name: str
    domain: str  # mediator/outcome/context/fidelity
    grain: str   # momentary/session/wave/followup
    instrument: str
    schedule: List[str]  # timepoint ids
    notes: str = ""

def default_arms() -> List[Arm]:
    return [
        Arm(
            name="choice_architecture",
            modality="choice_architecture",
            description=("Nudge/choice-architecture that shifts decisions without changing incentives: "
                         "defaults, option ordering, friction/simplification, salience prompts, and "
                         "implementation-intention templates tied to the child's current strategy repertoire."),
            zpd=ZPDSupport(
                support_type="just_in_time_prompting",
                timing="in-task",
                fading="performance_contingent",
                dose_minutes=8,
                contingencies={"fade_rule": "reduce prompt frequency after 3 consecutive correct strategy selections",
                               "increase_rule": "reintroduce prompts after 2 lapses or high RT variability"},
            ),
            components={"defaults": True, "ordering": True, "friction": "reduce", "salience": "highlight tradeoffs",
                        "commitment": "opt-in", "reflection_pause_seconds": 10},
            fidelity={"log_events": ["prompt_shown", "default_used", "reflection_pause"], "adherence_threshold": 0.8},
        ),
        Arm(
            name="targeted_debiasing",
            modality="debiasing",
            description=("Targeted debiasing micro-lessons and practice that make heuristics explicit and train "
                         "replacement strategies (consider-the-opposite, base-rate check, counterfactual search) "
                         "scaffolded within the child's ZPD with calibrated feedback."),
            zpd=ZPDSupport(
                support_type="worked_example_plus_feedback",
                timing="pre-task",
                fading="adaptive",
                dose_minutes=12,
                contingencies={"adapt_rule": "increase example support when error type repeats; fade when near-transfer improves"},
            ),
            components={"bias_targets": ["present_bias", "overconfidence", "availability", "sunk_cost"],
                        "strategy_cards": True, "metacognitive_checklist": True, "error_explanations": "brief"},
            fidelity={"log_events": ["lesson_completed", "strategy_selected", "error_type"], "adherence_threshold": 0.85},
        ),
        Arm(
            name="sleep_restoration",
            modality="sleep_restoration",
            description=("Sleep-restoration package to improve processing speed and executive control capacity: "
                         "sleep hygiene coaching, consistent schedules, morning light exposure guidance, "
                         "and brief relaxation; includes family support for environment/constraints."),
            zpd=ZPDSupport(
                support_type="caregiver_coaching",
                timing="post-task",
                fading="fixed",
                dose_minutes=10,
                contingencies={"fading_schedule": "weekly taper after week 2"},
            ),
            components={"sleep_hygiene": True, "bedtime_consistency": True, "light_exposure": "morning",
                        "relaxation": "5min", "screen_cutoff_minutes": 45},
            fidelity={"log_events": ["sleep_diary_complete", "lights_out_time", "wake_time"], "adherence_threshold": 0.75},
        ),
    ]

def default_timepoints(n_waves: int = 3, sessions_per_wave: int = 6, followups: Sequence[int] = (14, 90)) -> List[Dict[str, Any]]:
    tps: List[Dict[str, Any]] = []
    day = 0
    tps.append({"id": "T0_baseline", "day": day, "label": "baseline"})
    for w in range(1, n_waves + 1):
        tps.append({"id": f"W{w}_pre", "day": day + 1, "label": f"wave{w}_pre"})
        for s in range(1, sessions_per_wave + 1):
            tps.append({"id": f"W{w}_S{s}", "day": day + 1 + s, "label": f"wave{w}_session{s}"})
        tps.append({"id": f"W{w}_post", "day": day + 2 + sessions_per_wave, "label": f"wave{w}_post"})
        day = day + 2 + sessions_per_wave
    for k in followups:
        tps.append({"id": f"FU_{k}d", "day": day + k, "label": f"followup_{k}d"})
    return tps
def default_measures(timepoints: List[Dict[str, Any]], n_waves: int) -> List[Measure]:
    ids = [t["id"] for t in timepoints]
    def _wave_ids(prefixes: Tuple[str, ...]) -> List[str]:
        return [i for i in ids if i.startswith(prefixes)]
    baseline = ["T0_baseline"]
    prepost = [i for i in ids if i.endswith("_pre") or i.endswith("_post")]
    sessions = [i for i in ids if "_S" in i]
    followups = [i for i in ids if i.startswith("FU_")]

    return [
        Measure(
            name="executive_function",
            domain="mediator",
            grain="wave",
            instrument="EF_battery(inhibition,working_memory,shifting)",
            schedule=baseline + prepost + followups,
            notes="Primary proximal mediator; scored as latent EF factor per wave.",
        ),
        Measure(
            name="processing_speed",
            domain="mediator",
            grain="wave",
            instrument="simple_choice_RT+symbol_search",
            schedule=baseline + prepost + followups,
            notes="RT distribution metrics (median, IIV) to capture efficiency/stability.",
        ),
        Measure(
            name="strategy_use_micro",
            domain="mediator",
            grain="session",
            instrument="in-task logs + brief self-report",
            schedule=sessions,
            notes="Momentary strategy selection, switching costs, and error-recovery markers.",
        ),
        Measure(
            name="zpd_support_exposure",
            domain="context",
            grain="session",
            instrument="scaffold_log(type,timing,fading,dose)",
            schedule=sessions,
            notes="Operationalizes ZPD: support type/timing/fading delivered and received.",
        ),
        Measure(
            name="near_transfer_reasoning",
            domain="outcome",
            grain="wave",
            instrument="matrix/relational reasoning (near transfer)",
            schedule=prepost + followups,
            notes="Mechanistic bridge from EF/PS to reasoning; alternate forms per wave.",
        ),
        Measure(
            name="far_transfer_decisions",
            domain="outcome",
            grain="wave",
            instrument="behavioral decisions (delay discounting, risk, fairness) + parent/teacher reports",
            schedule=prepost + followups,
            notes="Real-world decision tasks plus ecological ratings; includes incentivized choices when feasible.",
        ),
        Measure(
            name="sleep_quantity_quality",
            domain="mediator",
            grain="session",
            instrument="sleep diary + optional actigraphy",
            schedule=baseline + sessions + followups,
            notes="Key mediator for sleep arm; moderator for other arms; captures latency/efficiency/variability.",
        ),
        Measure(
            name="fidelity_and_engagement",
            domain="fidelity",
            grain="session",
            instrument="checklists + usage logs + brief engagement scale",
            schedule=sessions,
            notes="Used for complier-average effects and heterogeneity analyses.",
        ),
    ]

def default_causal_tests() -> List[Dict[str, Any]]:
    return [
        {
            "name": "primary_mechanism_chain",
            "type": "longitudinal_mediation",
            "estimand": "arm -> (ZPD exposure, sleep) -> (EF, processing_speed) -> reasoning -> decisions",
            "model": "multilevel_DSEM_or_latent_change_score",
            "notes": "Tests within-child change; separates between/within effects; uses time-varying mediators.",
        },
        {
            "name": "zpd_operationalization_moderation",
            "type": "moderated_mediation",
            "moderators": ["support_type", "timing", "fading", "baseline_EF", "baseline_sleep_variability"],
            "notes": "Identifies which scaffolding parameters optimize EF/PS growth and downstream transfer.",
        },
        {
            "name": "transfer_contrast",
            "type": "within_cohort_transfer",
            "contrast": "near_transfer_reasoning vs far_transfer_decisions",
            "notes": "Compares effect sizes and mediation strength for near vs far outcomes within same cohort.",
        },
        {
            "name": "durability_decay",
            "type": "durability",
            "contrast": "post vs followups",
            "notes": "Estimates persistence/decay; tests whether fading schedules predict longer durability.",
        },
    ]

def default_logistics() -> Dict[str, Any]:
    return {
        "randomization_unit": "individual",
        "masking": {"assessors": True, "participants": False},
        "delivery_modes": ["tablet_app", "coach_session", "caregiver_module"],
        "staffing": {"coach_training_hours": 6, "assessor_training_hours": 4, "supervision_weekly_minutes": 30},
        "fidelity": {"audio_record_fraction": 0.1, "automated_logs": True, "drift_checks_every_waves": 1},
        "data_capture": {"time_sync": "server", "offline_buffering": True, "privacy": "de-identified child ids"},
        "burden_limits": {"session_minutes": 25, "assessment_minutes_per_wave": 45},
    }

def build_trial_plan(
    cohort: str = "cohort_A",
    n_waves: int = 3,
    sessions_per_wave: int = 6,
    followups: Sequence[int] = (14, 90),
    arms: Optional[Sequence[Arm]] = None,
    design: str = "multi_wave_parallel_within_cohort_transfer",
    rerandomize_each_wave: bool = False,
) -> Dict[str, Any]:
    arms_l = list(arms) if arms is not None else default_arms()
    tps = default_timepoints(n_waves=n_waves, sessions_per_wave=sessions_per_wave, followups=followups)
    measures = default_measures(tps, n_waves=n_waves)
    plan_id = _stable_id("trialplan", cohort, design, str(n_waves), str(sessions_per_wave), ",".join(map(str, followups)))
    rand = {
        "scheme": "blocked" if not rerandomize_each_wave else "SMART_like",
        "blocking_vars": ["site", "age_band", "baseline_EF_quartile"],
        "allocation": {a.name: 1 / len(arms_l) for a in arms_l},
        "rerandomize_each_wave": rerandomize_each_wave,
        "notes": "Use baseline blocking to improve precision; if rerandomized, preserve prior assignment for carryover modeling.",
    }
    comparisons = {
        "transfer": {"near": "near_transfer_reasoning", "far": "far_transfer_decisions", "within_cohort": True},
        "durability": {"followups": [f"FU_{k}d" for k in followups], "within_cohort": True},
        "dose_response": {"source": "zpd_support_exposure", "method": "g_methods_or_IV_using_assignment"},
    }
    return {
        "id": plan_id,
        "created": _today(),
        "design": design,
        "cohort": cohort,
        "structure": {"n_waves": n_waves, "sessions_per_wave": sessions_per_wave, "followups_days": list(followups)},
        "arms": [asdict(a) for a in arms_l],
        "timepoints": tps,
        "randomization": rand,
        "measures": [asdict(m) for m in measures],
        "causal_tests": default_causal_tests(),
        "logistics": default_logistics(),
        "comparisons": comparisons,
        "analysis_notes": [
            "Primary estimands target within-child growth (latent change) in EF/processing speed and downstream effects.",
            "Model carryover and learning across waves; include time-varying compliance and ZPD exposure.",
            "Pre-register decision task incentive compatibility; harmonize RT hardware to reduce measurement artifacts.",
        ],
    }

def validate_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    req_top = ["id", "design", "cohort", "arms", "timepoints", "randomization", "measures", "causal_tests", "logistics", "comparisons"]
    missing = [k for k in req_top if k not in plan]
    if missing:
        raise ValueError(f"Plan missing keys: {missing}")
    arm_names = [a["name"] for a in plan["arms"]]
    if len(set(arm_names)) != len(arm_names):
        raise ValueError("Duplicate arm names.")
    tp_ids = [t["id"] for t in plan["timepoints"]]
    if len(set(tp_ids)) != len(tp_ids):
        raise ValueError("Duplicate timepoint ids.")
    for m in plan["measures"]:
        bad = [s for s in m["schedule"] if s not in set(tp_ids)]
        if bad:
            raise ValueError(f"Measure {m['name']} has unknown schedule ids: {bad}")
    return plan
