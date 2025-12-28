from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union
import json


Json = Dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_safe_json(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return _safe_json(obj.__dict__)
    return str(obj)


@dataclass(frozen=True)
class EvidenceQuote:
    passage_id: str
    quote: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    score: Optional[float] = None
    url: Optional[str] = None
    title: Optional[str] = None


@dataclass(frozen=True)
class PassageProvenance:
    passage_id: str
    source_id: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    retrieved_rank: Optional[int] = None
    retrieved_score: Optional[float] = None


@dataclass(frozen=True)
class ClaimAudit:
    claim_id: str
    claim_text: str
    decision: Optional[str] = None
    confidence: Optional[float] = None
    required_passages_ok: Optional[bool] = None
    quote_alignment_ok: Optional[bool] = None
    constraints_ok: Optional[bool] = None
    failures: List[str] = field(default_factory=list)
    constraint_violations: List[str] = field(default_factory=list)
    quotes: List[EvidenceQuote] = field(default_factory=list)
    provenance: List[PassageProvenance] = field(default_factory=list)
    metadata: Json = field(default_factory=dict)


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    run_id: str
    ts_utc: str
    record_id: str
    claim: Optional[ClaimAudit] = None
    summary: Optional[Json] = None
    extra: Json = field(default_factory=dict)


class AuditLogger:
    """Structured JSONL audit log for verifier runs.

    Records per-claim evidence failures, constraint violations, and provenance.
    Use JSONL for append-friendly, downstream audit/aggregation.
    """

    def __init__(self, log_path: Union[str, Path], run_id: str, *, flush: bool = True) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = str(run_id)
        self._flush = bool(flush)
        self._fh = open(self.log_path, "a", encoding="utf-8")

    def close(self) -> None:
        try:
            self._fh.flush()
        finally:
            self._fh.close()

    def __enter__(self) -> "AuditLogger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _write(self, event: AuditEvent) -> None:
        payload: Json = {
            "event_type": event.event_type,
            "run_id": event.run_id,
            "ts_utc": event.ts_utc,
            "record_id": event.record_id,
            "claim": _safe_json(asdict(event.claim)) if event.claim is not None else None,
            "summary": _safe_json(event.summary) if event.summary is not None else None,
            "extra": _safe_json(event.extra),
        }
        self._fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        if self._flush:
            self._fh.flush()

    def log_claim_audit(
        self,
        *,
        record_id: str,
        claim_id: str,
        claim_text: str,
        decision: Optional[str] = None,
        confidence: Optional[float] = None,
        required_passages_ok: Optional[bool] = None,
        quote_alignment_ok: Optional[bool] = None,
        constraints_ok: Optional[bool] = None,
        failures: Optional[Sequence[str]] = None,
        constraint_violations: Optional[Sequence[str]] = None,
        quotes: Optional[Sequence[Union[EvidenceQuote, Json]]] = None,
        provenance: Optional[Sequence[Union[PassageProvenance, Json]]] = None,
        metadata: Optional[Json] = None,
        extra: Optional[Json] = None,
    ) -> None:
        q: List[EvidenceQuote] = []
        for item in (quotes or []):
            if isinstance(item, EvidenceQuote):
                q.append(item)
            else:
                q.append(EvidenceQuote(**dict(item)))
        p: List[PassageProvenance] = []
        for item in (provenance or []):
            if isinstance(item, PassageProvenance):
                p.append(item)
            else:
                p.append(PassageProvenance(**dict(item)))
        claim = ClaimAudit(
            claim_id=str(claim_id),
            claim_text=str(claim_text),
            decision=decision,
            confidence=confidence,
            required_passages_ok=required_passages_ok,
            quote_alignment_ok=quote_alignment_ok,
            constraints_ok=constraints_ok,
            failures=list(failures or []),
            constraint_violations=list(constraint_violations or []),
            quotes=q,
            provenance=p,
            metadata=dict(metadata or {}),
        )
        self._write(
            AuditEvent(
                event_type="claim_audit",
                run_id=self.run_id,
                ts_utc=_utc_now_iso(),
                record_id=str(record_id),
                claim=claim,
                extra=dict(extra or {}),
            )
        )

    def log_run_summary(self, *, record_id: str, summary: Json, extra: Optional[Json] = None) -> None:
        self._write(
            AuditEvent(
                event_type="run_summary",
                run_id=self.run_id,
                ts_utc=_utc_now_iso(),
                record_id=str(record_id),
                summary=dict(summary),
                extra=dict(extra or {}),
            )
        )


def format_evidence_failures(
    *,
    required_passages_ok: Optional[bool],
    quote_alignment_ok: Optional[bool],
    constraints_ok: Optional[bool],
    additional_failures: Optional[Iterable[str]] = None,
) -> List[str]:
    failures: List[str] = []
    if required_passages_ok is False:
        failures.append("missing_required_passages")
    if quote_alignment_ok is False:
        failures.append("missing_quote_alignment")
    if constraints_ok is False:
        failures.append("constraint_check_failed")
    for f in (additional_failures or []):
        if f and str(f) not in failures:
            failures.append(str(f))
    return failures
