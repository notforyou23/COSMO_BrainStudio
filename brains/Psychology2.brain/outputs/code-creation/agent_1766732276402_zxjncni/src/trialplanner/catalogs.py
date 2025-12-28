"""Curated catalogs used to assemble mechanism-oriented multi-wave trial plans.

Design intent:
- Link within-child cognitive growth (executive function; processing speed) to reasoning and
  real-world decisions, via fine-grained social support operationalizations (ZPD: type/timing/fading).
- Provide composable building blocks for experimental arms, measures, and causal-chain tests.
"""

from __future__ import annotations

from typing import Dict, List, Any


def _item(**kwargs: Any) -> Dict[str, Any]:
    """Small helper to keep catalogs compact and JSON-serializable."""
    return dict(kwargs)
INTERVENTION_COMPONENTS: Dict[str, Dict[str, Any]] = {
    "choice_architecture": _item(
        label="Nudge / choice-architecture",
        mechanisms=["attention/salience", "friction", "default effects", "temporal discounting", "planning prompts"],
        core_elements=[
            _item(name="defaults", levels=["opt-out", "active choice"], dosage_unit="per decision-point"),
            _item(name="salience_highlighting", levels=["visual cue", "summary dashboard"], dosage_unit="per task/session"),
            _item(name="friction_tuning", levels=["reduce steps", "add pause/confirm"], dosage_unit="per decision-point"),
            _item(name="ordering_and_grouping", levels=["best-first", "category grouping"], dosage_unit="per interface"),
            _item(name="implementation_intentions", levels=["if-then plan", "calendar commit"], dosage_unit="per week"),
        ],
        fidelity_markers=["exposure logs", "screen recordings/sample audits", "comprehension checks"],
        typical_targets=["financial choices", "health choices", "learning choices", "prosocial/helping"],
    ),
    "targeted_debiasing": _item(
        label="Targeted debiasing training",
        mechanisms=["metacognitive monitoring", "conflict detection", "rule abstraction", "inhibition of heuristics"],
        core_elements=[
            _item(name="bias_modules", levels=["present bias", "confirmation", "overconfidence", "framing"], dosage_unit="module"),
            _item(name="consider_the_opposite", levels=["single alt", "multiple alts"], dosage_unit="per decision"),
            _item(name="numeracy_and_base_rate", levels=["worked examples", "self-explanation"], dosage_unit="per session"),
            _item(name="calibration_feedback", levels=["immediate", "delayed summary"], dosage_unit="per assessment"),
            _item(name="transfer_prompts", levels=["near", "far"], dosage_unit="per week"),
        ],
        fidelity_markers=["module completion", "attention checks", "strategy reports"],
        typical_targets=["reasoning accuracy", "risk judgments", "belief updating", "academic decisions"],
    ),
    "sleep_restoration": _item(
        label="Sleep-restoration / circadian support",
        mechanisms=["arousal regulation", "memory consolidation", "processing speed", "executive control"],
        core_elements=[
            _item(name="sleep_hygiene_coaching", levels=["standard", "tailored barriers"], dosage_unit="per week"),
            _item(name="bedtime_routine", levels=["caregiver-supported", "self-managed"], dosage_unit="daily"),
            _item(name="light_and_screen_plan", levels=["evening reduction", "morning light"], dosage_unit="daily"),
            _item(name="nap_or_rest_breaks", levels=["scheduled", "as-needed"], dosage_unit="school day"),
            _item(name="actigraphy_feedback", levels=["none", "weekly report"], dosage_unit="per week"),
        ],
        fidelity_markers=["actigraphy wear time", "sleep diary completion", "adherence check-ins"],
        typical_targets=["EF/processing speed", "emotion regulation", "classroom behavior", "health decisions"],
    ),
}
COGNITIVE_TASKS: Dict[str, Dict[str, Any]] = {
    "executive_function": _item(
        label="Executive function task battery",
        tasks=[
            _item(name="n_back", construct="updating/working memory", primary_metric="d' or accuracy", timing_min=6),
            _item(name="flanker", construct="inhibitory control/attention", primary_metric="RT cost", timing_min=5),
            _item(name="go_no_go", construct="response inhibition", primary_metric="commission errors", timing_min=5),
            _item(name="task_switching", construct="cognitive flexibility", primary_metric="switch cost (RT/acc)", timing_min=7),
            _item(name="digit_span", construct="working memory span", primary_metric="span length", timing_min=4),
        ],
        recommended_frequency="baseline + each wave; short form for high-frequency bursts",
    ),
    "processing_speed": _item(
        label="Processing speed tasks",
        tasks=[
            _item(name="simple_reaction_time", construct="motor/alertness", primary_metric="median RT", timing_min=3),
            _item(name="choice_reaction_time", construct="speeded selection", primary_metric="median RT", timing_min=4),
            _item(name="symbol_search", construct="perceptual speed", primary_metric="items correct", timing_min=3),
            _item(name="rapid_visual_search", construct="visual attention speed", primary_metric="RT/accuracy", timing_min=4),
        ],
        recommended_frequency="baseline + midline + endline; optional weekly micro-assessments",
    ),
    "reasoning": _item(
        label="Reasoning and learning transfer tasks",
        tasks=[
            _item(name="matrix_reasoning", construct="fluid reasoning", primary_metric="items correct", timing_min=10),
            _item(name="probabilistic_reasoning", construct="base-rate use", primary_metric="calibration error", timing_min=8),
            _item(name="cognitive_reflection", construct="override heuristics", primary_metric="CRT score", timing_min=5),
            _item(name="planning_task", construct="multi-step planning", primary_metric="optimality", timing_min=8),
        ],
        recommended_frequency="baseline + endline + follow-ups (durability/transfer)",
    ),
}
PROXIMAL_MEDIATORS: Dict[str, Dict[str, Any]] = {
    "momentary_self_regulation": _item(
        label="Momentary self-regulation",
        measures=[
            _item(name="EMA_goals_and_effort", modality="EMA", cadence="2-5/day for 1-2 weeks per wave",
                  metrics=["goal salience", "effort", "temptation", "strategy use"]),
            _item(name="delay_of_gratification_microtasks", modality="app task", cadence="weekly burst",
                  metrics=["wait time", "choice patterns"]),
        ],
        links_to=["executive_function", "present-bias decisions"],
    ),
    "attention_and_cognitive_load": _item(
        label="Attention allocation and cognitive load",
        measures=[
            _item(name="pupil_or_eye_tracking_proxy", modality="camera/optional", cadence="lab waves", metrics=["pupil dilation", "fixations"]),
            _item(name="subjective_load_scale", modality="survey", cadence="each session", metrics=["NASA-TLX short", "mental fatigue"]),
            _item(name="response_time_variability", modality="task-derived", cadence="each cognitive battery", metrics=["RTV", "lapses"]),
        ],
        links_to=["processing_speed", "decision consistency"],
    ),
    "metacognition_and_conflict_detection": _item(
        label="Metacognition / conflict detection",
        measures=[
            _item(name="confidence_ratings", modality="task-embedded", cadence="each reasoning task", metrics=["calibration", "resolution"]),
            _item(name="error_awareness_probe", modality="task-embedded", cadence="subset trials", metrics=["awareness rate"]),
            _item(name="strategy_report", modality="brief survey", cadence="each module", metrics=["strategy repertoire", "transfer intent"]),
        ],
        links_to=["debiasing uptake", "reasoning accuracy"],
    ),
    "sleep_and_arousal": _item(
        label="Sleep and arousal regulation",
        measures=[
            _item(name="actigraphy", modality="wearable", cadence="continuous 7-14d per wave", metrics=["TST", "SE", "WASO", "midpoint"]),
            _item(name="sleep_diary", modality="daily diary", cadence="continuous 7-14d per wave", metrics=["bed/wake times", "quality"]),
            _item(name="daytime_sleepiness", modality="brief scale", cadence="2-3/week", metrics=["sleepiness", "fatigue"]),
        ],
        links_to=["processing_speed", "executive control", "emotion regulation"],
    ),
    "zpd_support_process": _item(
        label="ZPD support process (micro-coded scaffolding)",
        measures=[
            _item(name="support_episode_coding", modality="video/audio coding", cadence="sampled sessions",
                  metrics=["support type", "timing relative to errors", "fade schedule", "child autonomy"]),
            _item(name="hint_request_and_use", modality="platform log", cadence="continuous", metrics=["requests", "latency", "effect on success"]),
            _item(name="contingency_index", modality="derived", cadence="per session", metrics=["support matched to performance"]),
        ],
        links_to=["learning rate", "transfer/durability"],
    ),
}
DISTAL_OUTCOMES: Dict[str, Dict[str, Any]] = {
    "real_world_decisions": _item(
        label="Real-world decision quality",
        outcomes=[
            _item(name="health_choices", examples=["snack selection", "screen-time budgeting", "activity choice"],
                  metrics=["choice proportions", "goal-consistency"], timeframe="weekly-monthly"),
            _item(name="financial_choices", examples=["saving vs spending tokens", "charitable giving", "price comparisons"],
                  metrics=["delay discounting params", "budget adherence"], timeframe="monthly"),
            _item(name="academic_choices", examples=["study planning", "help-seeking", "task persistence"],
                  metrics=["on-time completion", "plan quality"], timeframe="term"),
        ],
    ),
    "reasoning_and_transfer": _item(
        label="Reasoning performance and transfer",
        outcomes=[
            _item(name="near_transfer", metrics=["similar task gains", "strategy generalization"], timeframe="post-intervention"),
            _item(name="far_transfer", metrics=["novel domain decisions", "ecological scenarios"], timeframe="follow-up"),
            _item(name="durability", metrics=["maintenance of gains", "decay slope"], timeframe="1-12 months"),
        ],
    ),
    "school_and_functioning": _item(
        label="School functioning and behavior",
        outcomes=[
            _item(name="teacher_ratings", instruments=["BRIEF-2 short", "engagement scale"], timeframe="each term"),
            _item(name="attendance_and_tardiness", metrics=["days absent", "late arrivals"], timeframe="term"),
            _item(name="discipline_incidents", metrics=["counts", "severity"], timeframe="term"),
        ],
    ),
}
ZPD_OPERATIONALIZATIONS: List[Dict[str, Any]] = [
    _item(
        name="contingent_hinting",
        type="cognitive scaffolding",
        timing="triggered by hesitation/error (e.g., >8s or 2 errors)",
        fading="progressive: worked example -> partial hint -> metacognitive prompt -> none",
        dosage="max 3 hints/problem; cap per session",
        intended_mechanism="optimize challenge point; support updating without dependency",
    ),
    _item(
        name="metacognitive_coaching",
        type="strategy support",
        timing="pre-task plan + post-error reflection within 30s",
        fading="reduce coach prompts by 20% each session; shift to child self-prompts",
        dosage="2-4 prompts/session",
        intended_mechanism="increase monitoring/conflict detection; promote transfer",
    ),
    _item(
        name="affect_regulation_buffer",
        type="socio-emotional support",
        timing="immediately after frustration marker (self-report or behavioral cue)",
        fading="from guided breathing to brief label-and-choose; then self-initiated",
        dosage="1-2 min as-needed",
        intended_mechanism="reduce arousal; preserve processing speed/EF under stress",
    ),
    _item(
        name="peer_assisted_zpd",
        type="peer support",
        timing="paired when mismatch in mastery is within 1 SD; rotate weekly",
        fading="scripted roles -> open collaboration; increase independent trials",
        dosage="10-15 min/session",
        intended_mechanism="social explanation; strengthen rule abstraction and autonomy",
    ),
]
CAUSAL_CHAIN_TESTS: Dict[str, Dict[str, Any]] = {
    "within_wave_mediation": _item(
        label="Within-wave mediator tests",
        description="Test arm -> proximal mediator change -> distal outcome at same wave.",
        recommended_models=["SEM with clustered SEs", "Bayesian multilevel mediation", "product-of-coefficients with bootstrap"],
        assumptions_and_checks=["temporal ordering in schedule", "common-method bias checks", "sensitivity analysis (ρ)"],
    ),
    "cross_lagged_growth": _item(
        label="Cross-lagged / growth mediation",
        description="Test whether earlier mediator shifts predict later reasoning/decisions controlling prior levels.",
        recommended_models=["RI-CLPM", "latent growth mediation", "DSEM for intensive longitudinal data"],
        assumptions_and_checks=["measurement invariance", "random intercept separation", "missingness model"],
    ),
    "moderated_mechanisms": _item(
        label="Moderation of mechanism",
        description="Test whether ZPD parameters (type/timing/fading) or baseline EF/sleep moderate mediation paths.",
        recommended_models=["moderated mediation", "varying-slope multilevel models", "CATE with causal forests (exploratory)"],
        assumptions_and_checks=["pre-specify moderators", "multiplicity control", "heterogeneity robustness"],
    ),
    "transfer_and_durability": _item(
        label="Transfer and durability contrasts",
        description="Compare near vs far transfer and maintenance across follow-ups within same cohort.",
        recommended_models=["difference-in-differences across outcomes", "decay curve models", "dynamic treatment regimes (SMART extensions)"],
        assumptions_and_checks=["practice effects modeling", "anchor tasks for invariance", "interference/contamination checks"],
    ),
}


def list_catalog_names() -> List[str]:
    return [
        "INTERVENTION_COMPONENTS",
        "COGNITIVE_TASKS",
        "PROXIMAL_MEDIATORS",
        "DISTAL_OUTCOMES",
        "ZPD_OPERATIONALIZATIONS",
        "CAUSAL_CHAIN_TESTS",
    ]
