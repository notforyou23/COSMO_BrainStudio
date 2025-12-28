from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal

Jurisdiction = Literal["US", "UNECE", "GLOBAL"]
StandardKind = Literal["FMVSS", "UNECE", "SAE", "ISO", "IEC", "CISPR", "OTHER"]
TestKind = Literal["EMC", "HV_SAFETY", "BRAKING", "LIGHTING", "LABELING", "CRASH", "OTHER"]
DocKind = Literal["DESIGN", "TEST", "QUALITY", "TRACEABILITY", "REGULATORY", "MANUFACTURING", "OTHER"]

def _req(d: Dict[str, Any], k: str, t: Any = None) -> Any:
    if k not in d:
        raise KeyError(f"Missing required field: {k}")
    v = d[k]
    if t and not isinstance(v, t):
        raise TypeError(f"Field {k} expected {t}, got {type(v)}")
    return v
@dataclass(frozen=True, slots=True)
class Standard:
    id: str
    kind: StandardKind
    jurisdiction: Jurisdiction
    code: str
    title: str
    url: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in ("id","kind","jurisdiction","code","title","url","notes")}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Standard":
        return Standard(
            id=str(_req(d,"id")),
            kind=_req(d,"kind"),
            jurisdiction=_req(d,"jurisdiction"),
            code=str(_req(d,"code")),
            title=str(_req(d,"title")),
            url=d.get("url"),
            notes=d.get("notes"),
        )
@dataclass(frozen=True, slots=True)
class Component:
    id: str
    name: str
    category: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in ("id","name","category","description")}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Component":
        return Component(
            id=str(_req(d,"id")),
            name=str(_req(d,"name")),
            category=str(_req(d,"category")),
            description=d.get("description"),
        )
@dataclass(frozen=True, slots=True)
class TestRequirement:
    id: str
    kind: TestKind
    name: str
    scope: str
    applies_to: Tuple[str, ...] = field(default_factory=tuple)  # component ids
    related_standards: Tuple[str, ...] = field(default_factory=tuple)  # standard ids
    acceptance: Optional[str] = None
    lab_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "kind": self.kind, "name": self.name, "scope": self.scope,
            "applies_to": list(self.applies_to),
            "related_standards": list(self.related_standards),
            "acceptance": self.acceptance, "lab_notes": self.lab_notes,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TestRequirement":
        return TestRequirement(
            id=str(_req(d,"id")),
            kind=_req(d,"kind"),
            name=str(_req(d,"name")),
            scope=str(_req(d,"scope")),
            applies_to=tuple(d.get("applies_to", ())),
            related_standards=tuple(d.get("related_standards", ())),
            acceptance=d.get("acceptance"),
            lab_notes=d.get("lab_notes"),
        )
@dataclass(frozen=True, slots=True)
class DocumentationItem:
    id: str
    kind: DocKind
    name: str
    required: bool = True
    description: Optional[str] = None
    evidence_examples: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "kind": self.kind, "name": self.name, "required": self.required,
            "description": self.description, "evidence_examples": list(self.evidence_examples),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "DocumentationItem":
        return DocumentationItem(
            id=str(_req(d,"id")),
            kind=_req(d,"kind"),
            name=str(_req(d,"name")),
            required=bool(d.get("required", True)),
            description=d.get("description"),
            evidence_examples=tuple(d.get("evidence_examples", ())),
        )
@dataclass(frozen=True, slots=True)
class DecisionNode:
    id: str
    question: str
    options: Tuple[str, ...]
    next_by_option: Dict[str, str]  # option -> next node id (or terminal id)
    rationale: Optional[str] = None

    def __post_init__(self) -> None:
        if set(self.next_by_option.keys()) != set(self.options):
            raise ValueError(f"DecisionNode {self.id} next_by_option must cover all options exactly")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "question": self.question, "options": list(self.options),
            "next_by_option": dict(self.next_by_option), "rationale": self.rationale,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "DecisionNode":
        opts = tuple(_req(d,"options"))
        nxt = dict(_req(d,"next_by_option"))
        return DecisionNode(
            id=str(_req(d,"id")),
            question=str(_req(d,"question")),
            options=opts,
            next_by_option=nxt,
            rationale=d.get("rationale"),
        )
@dataclass(frozen=True, slots=True)
class ComponentStandardMapRow:
    component_id: str
    standard_ids: Tuple[str, ...] = field(default_factory=tuple)
    test_ids: Tuple[str, ...] = field(default_factory=tuple)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "standard_ids": list(self.standard_ids),
            "test_ids": list(self.test_ids),
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ComponentStandardMapRow":
        return ComponentStandardMapRow(
            component_id=str(_req(d,"component_id")),
            standard_ids=tuple(d.get("standard_ids", ())),
            test_ids=tuple(d.get("test_ids", ())),
            notes=d.get("notes"),
        )
@dataclass(frozen=True, slots=True)
class ComplianceDataset:
    standards: Tuple[Standard, ...] = field(default_factory=tuple)
    components: Tuple[Component, ...] = field(default_factory=tuple)
    tests: Tuple[TestRequirement, ...] = field(default_factory=tuple)
    documentation: Tuple[DocumentationItem, ...] = field(default_factory=tuple)
    decision_tree: Tuple[DecisionNode, ...] = field(default_factory=tuple)
    mapping: Tuple[ComponentStandardMapRow, ...] = field(default_factory=tuple)

    def index(self) -> Dict[str, Dict[str, Any]]:
        return {
            "standards": {s.id: s for s in self.standards},
            "components": {c.id: c for c in self.components},
            "tests": {t.id: t for t in self.tests},
            "documentation": {d.id: d for d in self.documentation},
            "decision_tree": {n.id: n for n in self.decision_tree},
        }

    def validate_references(self) -> None:
        idx = self.index()
        for row in self.mapping:
            if row.component_id not in idx["components"]:
                raise ValueError(f"Unknown component_id in mapping: {row.component_id}")
            for sid in row.standard_ids:
                if sid not in idx["standards"]:
                    raise ValueError(f"Unknown standard_id in mapping: {sid}")
            for tid in row.test_ids:
                if tid not in idx["tests"]:
                    raise ValueError(f"Unknown test_id in mapping: {tid}")
        for t in self.tests:
            for cid in t.applies_to:
                if cid not in idx["components"]:
                    raise ValueError(f"Unknown component_id in test {t.id}: {cid}")
            for sid in t.related_standards:
                if sid not in idx["standards"]:
                    raise ValueError(f"Unknown standard_id in test {t.id}: {sid}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standards": [s.to_dict() for s in self.standards],
            "components": [c.to_dict() for c in self.components],
            "tests": [t.to_dict() for t in self.tests],
            "documentation": [d.to_dict() for d in self.documentation],
            "decision_tree": [n.to_dict() for n in self.decision_tree],
            "mapping": [m.to_dict() for m in self.mapping],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ComplianceDataset":
        ds = ComplianceDataset(
            standards=tuple(Standard.from_dict(x) for x in d.get("standards", [])),
            components=tuple(Component.from_dict(x) for x in d.get("components", [])),
            tests=tuple(TestRequirement.from_dict(x) for x in d.get("tests", [])),
            documentation=tuple(DocumentationItem.from_dict(x) for x in d.get("documentation", [])),
            decision_tree=tuple(DecisionNode.from_dict(x) for x in d.get("decision_tree", [])),
            mapping=tuple(ComponentStandardMapRow.from_dict(x) for x in d.get("mapping", [])),
        )
        ds.validate_references()
        return ds
