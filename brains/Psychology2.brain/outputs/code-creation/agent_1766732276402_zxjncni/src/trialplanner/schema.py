from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional, Sequence, Union

from pydantic import BaseModel, Field, model_validator


class SupportType(str, Enum):
    modeling = "modeling"
    prompting = "prompting"
    worked_example = "worked_example"
    feedback = "feedback"
    co_regulation = "co_regulation"
    peer_support = "peer_support"
    scaffolding_tool = "scaffolding_tool"


class SupportTiming(str, Enum):
    pre_task = "pre_task"
    in_task = "in_task"
    post_task = "post_task"
    just_in_time = "just_in_time"


class FadingRule(str, Enum):
    fixed = "fixed"
    performance_contingent = "performance_contingent"
    time_contingent = "time_contingent"
    adaptive_bayesian = "adaptive_bayesian"


class RandomizationUnit(str, Enum):
    child = "child"
    classroom = "classroom"
    school = "school"


class ArmKind(str, Enum):
    nudge_choice_architecture = "nudge_choice_architecture"
    targeted_debiasing = "targeted_debiasing"
    sleep_restoration = "sleep_restoration"
    active_control = "active_control"
    waitlist = "waitlist"


class TaskDomain(str, Enum):
    executive_function = "executive_function"
    processing_speed = "processing_speed"
    reasoning = "reasoning"
    decision = "decision"
    real_world = "real_world"


class ZPDSupport(BaseModel):
    type: SupportType
    timing: SupportTiming
    intensity: float = Field(ge=0, le=1, description="0-1 dose within session")
    fading: FadingRule
    fade_param: Optional[float] = Field(default=None, description="e.g., slope/threshold")
    agent: Literal["adult", "peer", "tool", "mixed"] = "adult"
    target_skill: Optional[str] = Field(default=None, description="micro-skill (e.g., updating, inhibition, rule-switch)")
    notes: Optional[str] = None


class InterventionComponent(BaseModel):
    name: str
    description: str
    zpd: List[ZPDSupport] = Field(default_factory=list)
    dose_minutes: Optional[int] = Field(default=None, ge=1)
    delivery: Literal["in_person", "digital", "hybrid"] = "hybrid"
    fidelity_checks: List[str] = Field(default_factory=list)


class ExperimentalArm(BaseModel):
    arm_id: str
    kind: ArmKind
    label: str
    components: List[InterventionComponent] = Field(default_factory=list)
    comparator_notes: Optional[str] = None


class Measure(BaseModel):
    measure_id: str
    name: str
    domain: TaskDomain
    construct: str = Field(description="e.g., inhibition, working_memory, processing_speed, fluid_reasoning, risk_preference")
    method: Literal["task", "survey", "passive", "admin", "observational"] = "task"
    expected_direction: Optional[Literal["increase", "decrease", "none"]] = None


class Timepoint(BaseModel):
    tp: str = Field(description="e.g., W0, W2, W6, M3")
    week: float = Field(ge=0)
    label: Optional[str] = None
    window_days: int = Field(default=7, ge=0)
    phase: Literal["baseline", "intervention", "post", "followup"] = "intervention"


class MeasurementSchedule(BaseModel):
    timepoints: List[Timepoint]
    measures_by_timepoint: Dict[str, List[str]] = Field(default_factory=dict, description="tp -> [measure_id]")
    frequency_notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate_mapping(self):
        tps = {t.tp for t in self.timepoints}
        for k in self.measures_by_timepoint:
            if k not in tps:
                raise ValueError(f"measures_by_timepoint has unknown timepoint: {k}")
        return self


class CausalTestKind(str, Enum):
    mediation = "mediation"
    moderation = "moderation"
    moderated_mediation = "moderated_mediation"
    transfer = "transfer"
    durability = "durability"


class CausalTest(BaseModel):
    test_id: str
    kind: CausalTestKind
    description: str
    iv_arm_ids: List[str] = Field(default_factory=list, description="intervention vs comparator")
    mediator_ids: List[str] = Field(default_factory=list, description="proximal mediators (EF/PS, ZPD process, sleep)")
    outcome_ids: List[str] = Field(default_factory=list, description="distal reasoning/decision/real-world outcomes")
    moderator_ids: List[str] = Field(default_factory=list, description="e.g., baseline EF, SES, classroom climate")
    time_lag_weeks: Optional[float] = Field(default=None, ge=0)
    analysis: Literal["multilevel", "SEM", "g_methods", "bayesian"] = "multilevel"
    estimand: Optional[str] = Field(default="ATE", description="e.g., ATE, CACE, interventional indirect effect")
    prereg_notes: Optional[str] = None


class TrialDesign(BaseModel):
    trial_id: str
    title: str
    cohort: str = Field(description="population/cohort description")
    waves: int = Field(ge=1, description="number of intervention waves within cohort")
    randomization_unit: RandomizationUnit = RandomizationUnit.child
    arms: List[ExperimentalArm]
    measures: List[Measure]
    schedule: MeasurementSchedule
    causal_tests: List[CausalTest] = Field(default_factory=list)
    logistics: Dict[str, str] = Field(default_factory=dict, description="e.g., staffing, device needs, adherence plans, attrition handling")

    @model_validator(mode="after")
    def _refs_exist(self):
        arm_ids = {a.arm_id for a in self.arms}
        meas_ids = {m.measure_id for m in self.measures}
        for ct in self.causal_tests:
            if any(a not in arm_ids for a in ct.iv_arm_ids):
                raise ValueError(f"{ct.test_id}: unknown arm in iv_arm_ids")
            for mid in ct.mediator_ids + ct.outcome_ids + ct.moderator_ids:
                if mid and mid not in meas_ids:
                    raise ValueError(f"{ct.test_id}: unknown measure_id reference: {mid}")
        for tp, mids in self.schedule.measures_by_timepoint.items():
            for mid in mids:
                if mid not in meas_ids:
                    raise ValueError(f"schedule[{tp}]: unknown measure_id: {mid}")
        return self
