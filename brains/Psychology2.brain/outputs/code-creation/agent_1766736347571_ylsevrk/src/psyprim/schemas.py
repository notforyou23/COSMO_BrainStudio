from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Type, Union
from pydantic import BaseModel, Field
ExperimentType = Literal["survey", "audit_study", "field_experiment", "lab_experiment", "observational"]
MetricDirection = Literal["higher_better", "lower_better", "target_range", "none"]
SamplingUnit = Literal["article", "claim", "citation", "dataset", "archive_item", "researcher", "lab", "journal"]


class MetricSpec(BaseModel):
    """Operationalized outcome to evaluate workflow/tool adoption effects."""
    name: str = Field(..., description="Short label for the metric.")
    construct: str = Field(..., description="Underlying construct (e.g., citation accuracy, reproducibility).")
    definition: str = Field(..., description="Human-readable definition and scope.")
    computation: str = Field(..., description="How the metric is computed from raw data.")
    direction: MetricDirection = Field("none", description="Interpretation direction for improvement.")
    unit: Optional[str] = Field(None, description="Unit of analysis (e.g., % correct, minutes, ICC).")
    reliability_plan: Optional[str] = Field(None, description="Inter-rater/measurement reliability plan.")
    validity_notes: Optional[str] = Field(None, description="Known threats and mitigation for construct validity.")

class SamplingFrameSpec(BaseModel):
    """Defines where cases/participants come from and how they are sampled."""
    unit: SamplingUnit = Field(..., description="Primary sampling unit.")
    population: str = Field(..., description="Target population description.")
    sources: List[str] = Field(default_factory=list, description="Concrete sources (journals, registries, archives).")
    inclusion_criteria: List[str] = Field(default_factory=list)
    exclusion_criteria: List[str] = Field(default_factory=list)
    sampling_method: str = Field(..., description="e.g., stratified random, quota, cluster, convenience.")
    stratification: Optional[str] = Field(None, description="Strata and allocation rules if applicable.")
    n_target: Optional[int] = Field(None, ge=1, description="Planned sample size for units/participants.")
    power_notes: Optional[str] = Field(None, description="Effect size assumptions, MDE, alpha, power, ICC if clustered.")

class DataCollectionSpec(BaseModel):
    """Procedures/instruments used to collect primary data."""
    instruments: List[str] = Field(default_factory=list, description="Surveys, rubrics, extraction forms, logs.")
    procedure: str = Field(..., description="Step-by-step data collection workflow.")
    randomization: Optional[str] = Field(None, description="Randomization unit/method if experimental.")
    blinding: Optional[str] = Field(None, description="Who is blinded to condition/labels, and how.")
    training_qc: Optional[str] = Field(None, description="Rater training, calibration, spot-checking.")
    preregistration: Optional[str] = Field(None, description="Registry + key prereg items, or justification if none.")
    ethics: Optional[str] = Field(None, description="IRB/ethics considerations and consent model.")
    data_management: Optional[str] = Field(None, description="Storage, identifiers, de-identification, retention.")

class AnalysisPlanSpec(BaseModel):
    """Statistical/qualitative analysis plan and decision rules."""
    estimand: str = Field(..., description="Target causal/associational estimand.")
    design: str = Field(..., description="Design class: RCT, DiD, interrupted time series, audit, etc.")
    models: List[str] = Field(default_factory=list, description="Model formulas/families and key covariates.")
    inference: str = Field(..., description="SEs, clustering, Bayesian priors, multiple testing approach.")
    missing_data: Optional[str] = Field(None, description="Missingness handling: MI, weighting, bounds.")
    robustness_checks: List[str] = Field(default_factory=list)
    qualitative_methods: Optional[str] = Field(None, description="If applicable: coding scheme, reflexivity, saturation.")
    reporting: Optional[str] = Field(None, description="Tables/figures, effect sizes, uncertainty, transparency artifacts.")
class ExperimentSpec(BaseModel):
    """A single empirical study evaluating workflow/tool adoption and outcomes."""
    id: str = Field(..., pattern=r"^[A-Za-z0-9_.-]+$", description="Stable identifier for cross-referencing.")
    type: ExperimentType
    title: str
    research_question: str
    hypotheses: List[str] = Field(default_factory=list)
    intervention: str = Field(..., description="Workflow/tooling condition(s) being evaluated.")
    comparator: str = Field(..., description="Baseline/alternative condition(s).")
    design_summary: str = Field(..., description="Compact narrative of design and operationalization.")
    metrics: List[MetricSpec] = Field(default_factory=list)
    sampling_frame: SamplingFrameSpec
    data_collection: DataCollectionSpec
    analysis_plan: AnalysisPlanSpec
    threats_to_validity: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list, description="Planned outputs: datasets, prereg, reports.")
    timeline: Optional[str] = Field(None, description="Approximate schedule and milestones.")

class RoadmapSpec(BaseModel):
    """Top-level validation/adoption roadmap specification."""
    title: str
    version: str = Field(..., description="Semantic-ish version for the roadmap spec.")
    mission: str = Field(..., description="Why this roadmap exists and what it seeks to validate.")
    scope: str = Field(..., description="In/out-of-scope domains, audiences, and artifacts.")
    standardized_workflows: List[str] = Field(default_factory=list, description="Named workflow elements to validate.")
    lightweight_tooling: List[str] = Field(default_factory=list, description="Tools/CLI features or integrations.")
    experiments: List[ExperimentSpec] = Field(default_factory=list)
    governance: Optional[str] = Field(None, description="Decision rights, iteration cadence, maintainer roles.")
    adoption_strategy: Optional[str] = Field(None, description="Training, incentives, partnerships, dissemination.")
    success_criteria: List[str] = Field(default_factory=list, description="Program-level success thresholds.")
    metadata: Dict[str, Any] = Field(default_factory=dict)

def _model_dump(obj: BaseModel) -> Dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj.dict()

def json_schema(model: Union[Type[BaseModel], BaseModel]) -> Dict[str, Any]:
    cls = model if isinstance(model, type) else model.__class__
    if hasattr(cls, "model_json_schema"):
        return cls.model_json_schema()
    return cls.schema()

def export_roadmap_schema() -> Dict[str, Any]:
    return json_schema(RoadmapSpec)

def write_json_schema(path: str) -> None:
    from pathlib import Path as _Path
    p = _Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(export_roadmap_schema(), indent=2, sort_keys=True), encoding="utf-8")
