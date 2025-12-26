from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple
import json
import hashlib


def _stable_id(prefix: str, *parts: Any) -> str:
    s = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    h = hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{h}"


def _require(obj: Mapping[str, Any], key: str, ctx: str) -> Any:
    if key not in obj:
        raise ValueError(f"Missing required field '{key}' in {ctx}")
    return obj[key]


def _as_str(x: Any, ctx: str) -> str:
    if not isinstance(x, str) or not x.strip():
        raise ValueError(f"Expected non-empty string in {ctx}")
    return x


def _as_list(x: Any, ctx: str) -> List[Any]:
    if not isinstance(x, list):
        raise ValueError(f"Expected list in {ctx}")
    return x


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    text: str
    citation: str
    source: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class GroundedExample:
    example_id: str
    question: str
    answer: str
    evidence_ids: Tuple[str, ...]
    meta: Optional[Dict[str, Any]] = None


class GroundedDataset:
    """Loads and validates a grounded QA dataset with cited evidence.

    Supported file formats:
      - JSON list of examples
      - JSON object with key 'examples' or 'data' as list of examples
      - JSONL (one example per line)
    """

    def __init__(self, examples: List[GroundedExample], evidence: Dict[str, Evidence]):
        self._examples = examples
        self._evidence = evidence
        self._example_by_id = {ex.example_id: ex for ex in examples}
        if len(self._example_by_id) != len(examples):
            raise ValueError("Duplicate example_id detected")

    @classmethod
    def from_path(cls, path: str | Path) -> "GroundedDataset":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        raw = p.read_text(encoding="utf-8")
        items: List[Mapping[str, Any]]
        if raw.lstrip().startswith("{"):
            obj = json.loads(raw)
            if isinstance(obj, dict):
                if "examples" in obj:
                    items = _as_list(obj["examples"], "root.examples")  # type: ignore[assignment]
                elif "data" in obj:
                    items = _as_list(obj["data"], "root.data")  # type: ignore[assignment]
                else:
                    raise ValueError("JSON object must contain 'examples' or 'data' list")
            elif isinstance(obj, list):
                items = obj  # type: ignore[assignment]
            else:
                raise ValueError("Unsupported JSON root type")
        else:
            items = []
            for i, line in enumerate(raw.splitlines()):
                if not line.strip():
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSONL at line {i+1}: {e}") from e

        exs: List[GroundedExample] = []
        ev_index: Dict[str, Evidence] = {}
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                raise ValueError(f"Each example must be an object; got {type(it).__name__} at index {i}")
            ex, evs = cls._parse_example(it, idx=i)
            exs.append(ex)
            for ev in evs:
                if ev.evidence_id in ev_index:
                    prev = ev_index[ev.evidence_id]
                    if (prev.text, prev.citation, prev.source) != (ev.text, ev.citation, ev.source):
                        raise ValueError(f"Evidence id collision with differing content: {ev.evidence_id}")
                ev_index[ev.evidence_id] = ev
        return cls(exs, ev_index)

    @staticmethod
    def _parse_example(obj: Mapping[str, Any], idx: int) -> Tuple[GroundedExample, List[Evidence]]:
        ctx = f"example[{idx}]"
        q = _as_str(_require(obj, "question", ctx), f"{ctx}.question")
        a = _as_str(_require(obj, "answer", ctx), f"{ctx}.answer")
        ex_id = obj.get("id") or obj.get("example_id") or _stable_id("ex", q, a, idx)
        ex_id = _as_str(ex_id, f"{ctx}.id")
        ev_raw = _require(obj, "evidence", ctx)
        ev_list = _as_list(ev_raw, f"{ctx}.evidence")
        evs: List[Evidence] = []
        ev_ids: List[str] = []
        for j, e in enumerate(ev_list):
            ectx = f"{ctx}.evidence[{j}]"
            if not isinstance(e, dict):
                raise ValueError(f"Each evidence item must be an object in {ectx}")
            text = _as_str(_require(e, "text", ectx), f"{ectx}.text")
            citation = _as_str(_require(e, "citation", ectx), f"{ectx}.citation")
            source = e.get("source")
            if source is not None:
                source = _as_str(source, f"{ectx}.source")
            evid = e.get("id") or e.get("evidence_id") or _stable_id("ev", citation, text)
            evid = _as_str(evid, f"{ectx}.id")
            meta = e.get("meta")
            if meta is not None and not isinstance(meta, dict):
                raise ValueError(f"Expected object/dict for {ectx}.meta")
            ev = Evidence(evidence_id=evid, text=text, citation=citation, source=source, meta=meta)
            evs.append(ev)
            ev_ids.append(evid)

        meta = obj.get("meta")
        if meta is not None and not isinstance(meta, dict):
            raise ValueError(f"Expected object/dict for {ctx}.meta")
        ex = GroundedExample(example_id=ex_id, question=q, answer=a, evidence_ids=tuple(ev_ids), meta=meta)
        return ex, evs

    def __len__(self) -> int:
        return len(self._examples)

    def __iter__(self) -> Iterator[GroundedExample]:
        return iter(self._examples)

    @property
    def examples(self) -> List[GroundedExample]:
        return list(self._examples)

    @property
    def evidence(self) -> Dict[str, Evidence]:
        return dict(self._evidence)

    def get_example(self, example_id: str) -> GroundedExample:
        try:
            return self._example_by_id[example_id]
        except KeyError as e:
            raise KeyError(f"Unknown example_id: {example_id}") from e

    def get_evidence(self, evidence_id: str) -> Evidence:
        try:
            return self._evidence[evidence_id]
        except KeyError as e:
            raise KeyError(f"Unknown evidence_id: {evidence_id}") from e

    def evidence_for_example(self, example_id: str) -> List[Evidence]:
        ex = self.get_example(example_id)
        return [self.get_evidence(eid) for eid in ex.evidence_ids]

    def validate_crossrefs(self) -> None:
        for ex in self._examples:
            for eid in ex.evidence_ids:
                if eid not in self._evidence:
                    raise ValueError(f"Example {ex.example_id} references missing evidence_id {eid}")
