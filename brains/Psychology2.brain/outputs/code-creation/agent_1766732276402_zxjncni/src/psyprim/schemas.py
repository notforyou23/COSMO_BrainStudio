from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Any, Dict, List, Literal, Type, TypeVar, get_args, get_origin

T = TypeVar("T", bound="SchemaBase")


def _strip_none(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _strip_none(v) for k, v in x.items() if v is not None}
    if isinstance(x, list):
        return [_strip_none(v) for v in x]
    return x


def _coerce(dc_type: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(dc_type)
    if origin in (list, List) and isinstance(value, list):
        inner = (get_args(dc_type) or (Any,))[0]
        return [_coerce(inner, v) for v in value]
    if origin in (dict, Dict) and isinstance(value, dict):
        k_t, v_t = (get_args(dc_type) or (Any, Any))
        return {_coerce(k_t, k): _coerce(v_t, v) for k, v in value.items()}
    if origin is Literal:
        return value
    if isinstance(dc_type, type) and is_dataclass(dc_type) and isinstance(value, dict):
        return dc_type.from_dict(value)  # type: ignore[attr-defined]
    return value


@dataclass
class SchemaBase:
    schema: str = field(init=False, default="psyprim/v1")

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.__class__.__name__
        return _strip_none(d)

    @classmethod
    def from_dict(cls: Type[T], d: Dict[str, Any]) -> T:
        kwargs = {}
        for f in cls.__dataclass_fields__.values():  # type: ignore[attr-defined]
            if f.init and f.name in d:
                kwargs[f.name] = _coerce(f.type, d[f.name])
        return cls(**kwargs)  # type: ignore[arg-type]


@dataclass
class WorkflowStep(SchemaBase):
    id: str
    name: str
    goal: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    checks: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)


@dataclass
class Workflow(SchemaBase):
    id: str
    name: str
    audience: str
    steps: List[WorkflowStep]
    repositories: List[str] = field(default_factory=list)
    citations_required: List[str] = field(default_factory=lambda: ["edition", "translation", "repository_url", "stable_id"])
    version: str = "1.0"


@dataclass
class MetadataField(SchemaBase):
    key: str
    label: str
    required: bool = True
    guidance: str = ""
    examples: List[str] = field(default_factory=list)


@dataclass
class MetadataChecklist(SchemaBase):
    id: str
    name: str
    fields: List[MetadataField]
    scope: str = "primary_source_citation"
    minimum_pass_required_keys: List[str] = field(default_factory=lambda: ["work_title", "author", "edition", "year", "repository_url"])


@dataclass
class SurveyQuestion(SchemaBase):
    id: str
    prompt: str
    response_type: Literal["likert5", "yes_no", "multiple_choice", "free_text"]
    choices: List[str] = field(default_factory=list)
    construct: str = ""
    required: bool = True


@dataclass
class SurveyInstrument(SchemaBase):
    id: str
    name: str
    population: str
    sampling: str
    questions: List[SurveyQuestion]
    outcomes: List[str] = field(default_factory=lambda: ["workflow_adoption", "metadata_completeness", "perceived_burden"])
    analysis_plan: str = "Descriptives + regression/ordinal models; preregister; report reliability for multi-item constructs."


@dataclass
class AuditStudyDesign(SchemaBase):
    id: str
    name: str
    sampling_frame: str
    unit_of_analysis: str = "article"
    sample_size_target: int = 200
    inclusion_criteria: List[str] = field(default_factory=lambda: ["psychology primary-source claims", "accessible full text"])
    coding_protocol: str = "Dual-code; adjudicate disagreements; compute IRR (Krippendorff's alpha)."
    primary_measures: List[str] = field(default_factory=lambda: ["edition_provenance_present", "translation_provenance_present", "variant_pagination_addressed", "repository_citation_present"])
    repositories_to_check: List[str] = field(default_factory=lambda: ["HathiTrust", "Internet Archive", "Gallica", "Google Books", "PsycINFO/Publisher PDFs"])
    preregistration_repo: str = "OSF"
    data_repo: str = "Zenodo"


@dataclass
class DetectionFeature(SchemaBase):
    key: str
    description: str
    regex_hint: str = ""
    weight: float = 1.0


@dataclass
class DetectionResult(SchemaBase):
    file: str
    total_matches: int
    feature_hits: Dict[str, int] = field(default_factory=dict)
    evidence: Dict[str, List[str]] = field(default_factory=dict)
    score: float = 0.0
    flags: List[str] = field(default_factory=list)


@dataclass
class SpecialistAgentTask(SchemaBase):
    agent: str
    objective: str
    deliverables: List[str]
    inputs: List[str] = field(default_factory=list)
    evaluation: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Roadmap(SchemaBase):
    id: str
    mission: str
    workflows: List[Workflow]
    checklist: MetadataChecklist
    survey: SurveyInstrument
    audit: AuditStudyDesign
    detection_features: List[DetectionFeature]
    agent_tasks: List[SpecialistAgentTask]
    repositories: List[str] = field(default_factory=lambda: ["OSF", "Zenodo", "GitHub"])
    success_criteria: List[str] = field(default_factory=lambda: ["higher metadata completeness", "higher primary-source traceability", "acceptable false-positive rate in detection"])
    timeline_weeks: int = 12
