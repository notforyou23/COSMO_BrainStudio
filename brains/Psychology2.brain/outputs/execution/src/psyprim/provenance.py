from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


class ProvenanceError(ValueError):
    pass


def _isodate(x: Optional[str]) -> Optional[date]:
    if x is None or x == "":
        return None
    return date.fromisoformat(x)


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    return list(x) if isinstance(x, (list, tuple)) else [x]


def _nonempty(s: Optional[str]) -> bool:
    return bool(s and str(s).strip())


@dataclass(frozen=True)
class SourceRepository:
    """Where the primary source or derivative file is hosted."""

    kind: str  # e.g., "url", "doi", "internet_archive", "local_path"
    locator: str  # URL/DOI/IA identifier/path
    accessed: Optional[date] = None
    notes: Optional[str] = None

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not _nonempty(self.kind):
            issues.append("repository.kind is required")
        if not _nonempty(self.locator):
            issues.append("repository.locator is required")
        return issues

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "locator": self.locator,
            "accessed": self.accessed.isoformat() if self.accessed else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SourceRepository":
        return cls(
            kind=d.get("kind", ""),
            locator=d.get("locator", ""),
            accessed=_isodate(d.get("accessed")),
            notes=d.get("notes"),
        )


@dataclass(frozen=True)
class TransformationStep:
    """A lightweight, auditable transform (scan/OCR/cleanup/translation/etc.)."""

    kind: str  # e.g., "scan", "ocr", "normalize", "translate", "paginate_map"
    tool: Optional[str] = None  # e.g., "tesseract 5.3"
    actor: Optional[str] = None  # person/org
    when: Optional[date] = None
    params: Dict[str, Any] = field(default_factory=dict)
    input_ref: Optional[str] = None  # points to upstream node id or file label
    output_ref: Optional[str] = None  # points to produced artifact label
    notes: Optional[str] = None

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not _nonempty(self.kind):
            issues.append("step.kind is required")
        if self.params is not None and not isinstance(self.params, dict):
            issues.append("step.params must be a dict")
        return issues

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "tool": self.tool,
            "actor": self.actor,
            "when": self.when.isoformat() if self.when else None,
            "params": self.params,
            "input_ref": self.input_ref,
            "output_ref": self.output_ref,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TransformationStep":
        return cls(
            kind=d.get("kind", ""),
            tool=d.get("tool"),
            actor=d.get("actor"),
            when=_isodate(d.get("when")),
            params=d.get("params") or {},
            input_ref=d.get("input_ref"),
            output_ref=d.get("output_ref"),
            notes=d.get("notes"),
        )
@dataclass(frozen=True)
class ProvenanceNode:
    """One link in an edition/translation provenance chain."""

    id: str
    label: str
    role: str  # e.g., "original", "edition", "translation", "reprint", "transcript"
    language: Optional[str] = None
    year: Optional[int] = None
    creators: List[str] = field(default_factory=list)  # author/editor/translator
    repository: Optional[SourceRepository] = None
    citation: Optional[str] = None  # human-readable citation string
    public_domain: Optional[bool] = None
    pagination_variant: Optional[str] = None  # e.g., "original", "pdf", "ebook"
    pagination_map: Dict[str, Any] = field(default_factory=dict)  # variant mapping metadata
    steps: List[TransformationStep] = field(default_factory=list)
    derived_from: List[str] = field(default_factory=list)  # upstream node ids
    extra: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not _nonempty(self.id):
            issues.append("node.id is required")
        if not _nonempty(self.label):
            issues.append(f"{self.id or '<node>'}: label is required")
        if not _nonempty(self.role):
            issues.append(f"{self.id or '<node>'}: role is required")
        if self.year is not None and (self.year < 0 or self.year > 9999):
            issues.append(f"{self.id}: year is out of range")
        if self.repository:
            issues += [f"{self.id}: {m}" for m in self.repository.validate()]
        if self.citation is not None and not _nonempty(self.citation):
            issues.append(f"{self.id}: citation must be non-empty if provided")
        if self.public_domain is True and not (_nonempty(self.citation) or self.repository):
            issues.append(f"{self.id}: public_domain marked true but missing citation/repository")
        if self.pagination_map and not isinstance(self.pagination_map, dict):
            issues.append(f"{self.id}: pagination_map must be a dict")
        for i, s in enumerate(self.steps):
            issues += [f"{self.id}: step[{i}]: {m}" for m in s.validate()]
        return issues

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "role": self.role,
            "language": self.language,
            "year": self.year,
            "creators": list(self.creators),
            "repository": self.repository.to_dict() if self.repository else None,
            "citation": self.citation,
            "public_domain": self.public_domain,
            "pagination_variant": self.pagination_variant,
            "pagination_map": self.pagination_map,
            "steps": [s.to_dict() for s in self.steps],
            "derived_from": list(self.derived_from),
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProvenanceNode":
        return cls(
            id=d.get("id", ""),
            label=d.get("label", ""),
            role=d.get("role", ""),
            language=d.get("language"),
            year=d.get("year"),
            creators=[str(x) for x in _as_list(d.get("creators"))],
            repository=SourceRepository.from_dict(d["repository"]) if d.get("repository") else None,
            citation=d.get("citation"),
            public_domain=d.get("public_domain"),
            pagination_variant=d.get("pagination_variant"),
            pagination_map=d.get("pagination_map") or {},
            steps=[TransformationStep.from_dict(x) for x in (d.get("steps") or [])],
            derived_from=[str(x) for x in _as_list(d.get("derived_from"))],
            extra=d.get("extra") or {},
        )
@dataclass(frozen=True)
class ProvenanceChain:
    """A DAG of provenance nodes; typically a chain but supports merges."""

    nodes: Dict[str, ProvenanceNode]
    head: str

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.nodes:
            return ["provenance.nodes is empty"]
        if self.head not in self.nodes:
            issues.append("provenance.head must be a node id present in nodes")
            return issues
        for nid, n in self.nodes.items():
            if nid != n.id:
                issues.append(f"node key '{nid}' does not match node.id '{n.id}'")
            issues += n.validate()
            for up in n.derived_from:
                if up not in self.nodes:
                    issues.append(f"{n.id}: derived_from references missing node '{up}'")
        # cycle detection
        visited: Dict[str, int] = {}  # 0=unseen,1=visiting,2=done

        def dfs(u: str) -> None:
            state = visited.get(u, 0)
            if state == 1:
                issues.append(f"cycle detected at '{u}'")
                return
            if state == 2:
                return
            visited[u] = 1
            for v in self.nodes[u].derived_from:
                if v in self.nodes:
                    dfs(v)
            visited[u] = 2

        dfs(self.head)
        return issues

    def require_valid(self) -> None:
        issues = self.validate()
        if issues:
            raise ProvenanceError("; ".join(issues))

    def topological_upstream(self) -> List[str]:
        """Return upstream-first order for the head (best-effort if disconnected)."""
        self.require_valid()
        order: List[str] = []
        seen: set[str] = set()

        def walk(u: str) -> None:
            if u in seen:
                return
            for v in self.nodes[u].derived_from:
                walk(v)
            seen.add(u)
            order.append(u)

        walk(self.head)
        return order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "head": self.head,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProvenanceChain":
        nodes_d = d.get("nodes") or {}
        nodes = {k: ProvenanceNode.from_dict(v) for k, v in nodes_d.items()}
        return cls(nodes=nodes, head=d.get("head", ""))

    def compact_report(self) -> List[Dict[str, Any]]:
        """A minimal, auditable report suitable for CLI output."""
        self.require_valid()
        out: List[Dict[str, Any]] = []
        for nid in self.topological_upstream():
            n = self.nodes[nid]
            out.append(
                {
                    "id": n.id,
                    "role": n.role,
                    "year": n.year,
                    "language": n.language,
                    "creators": n.creators,
                    "repository": n.repository.to_dict() if n.repository else None,
                    "citation": n.citation,
                    "public_domain": n.public_domain,
                    "pagination_variant": n.pagination_variant,
                    "derived_from": n.derived_from,
                    "steps": [s.to_dict() for s in n.steps],
                }
            )
        return out


def build_simple_chain(nodes: Sequence[ProvenanceNode], head: Optional[str] = None) -> ProvenanceChain:
    """Create a linear chain in provided order (upstream->downstream)."""
    if not nodes:
        raise ProvenanceError("nodes must be non-empty")
    by_id = {n.id: n for n in nodes}
    # enforce linear derived_from if not already set
    fixed: Dict[str, ProvenanceNode] = {}
    prev: Optional[str] = None
    for n in nodes:
        df = list(n.derived_from) if n.derived_from else ([prev] if prev else [])
        fixed[n.id] = ProvenanceNode(**{**n.to_dict(), "repository": n.repository, "steps": n.steps, "derived_from": [x for x in df if x]})
        prev = n.id
    h = head or nodes[-1].id
    chain = ProvenanceChain(nodes=fixed, head=h)
    chain.require_valid()
    return chain
