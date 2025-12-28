from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
import json
import time


Citation = Dict[str, Any]


def _now_ms() -> int:
    return int(time.time() * 1000)


def _coerce_span(span: Any) -> Optional[Tuple[int, int]]:
    if span is None:
        return None
    if isinstance(span, (list, tuple)) and len(span) == 2:
        try:
            a, b = int(span[0]), int(span[1])
            return (a, b) if a <= b else (b, a)
        except Exception:
            return None
    if isinstance(span, dict) and "start" in span and "end" in span:
        try:
            a, b = int(span["start"]), int(span["end"])
            return (a, b) if a <= b else (b, a)
        except Exception:
            return None
    return None


def validate_must_cite(answer: str, citations: List[Citation]) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    if not citations:
        return False, ["missing_citations"]
    for i, c in enumerate(citations):
        quote = (c.get("quote") or "").strip()
        url = (c.get("url") or "").strip()
        doi = (c.get("doi") or "").strip()
        span = _coerce_span(c.get("span") or c.get("answer_span"))
        if not quote:
            errs.append(f"c{i}:missing_quote")
            continue
        if not (url or doi):
            errs.append(f"c{i}:missing_url_or_doi")
        if span is None:
            errs.append(f"c{i}:missing_or_bad_span")
            continue
        a, b = span
        if a < 0 or b > len(answer) or a >= b:
            errs.append(f"c{i}:span_oob")
            continue
        if answer[a:b] != quote:
            errs.append(f"c{i}:span_quote_mismatch")
    return (len(errs) == 0), errs


def normalize_citations(answer: str, citations: List[Citation]) -> List[Citation]:
    out: List[Citation] = []
    for c in citations or []:
        c2 = dict(c)
        c2["quote"] = (c2.get("quote") or "").strip()
        c2["url"] = (c2.get("url") or "").strip()
        c2["doi"] = (c2.get("doi") or "").strip()
        span = _coerce_span(c2.get("span") or c2.get("answer_span"))
        if span is not None:
            c2["span"] = [span[0], span[1]]
        out.append(c2)
    return out


@dataclass
class DecisionRecord:
    qid: str
    mode: str
    accepted: bool
    abstained: bool
    confidence: float
    must_cite_ok: bool
    must_cite_errors: List[str]
    answer_len: int
    n_citations: int
    ts_ms: int
    meta: Dict[str, Any]


class HarnessAdapter:
    """Adapter layer for Borderline QA evaluation harness.

    Integrates pipelines into a stable output schema and logs per-item decisions
    to enable FAR (false accept rate) and coverage analysis.
    """

    def __init__(
        self,
        pipeline: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        *,
        log_path: Optional[str | Path] = None,
        accept_threshold: float = 0.5,
        confidence_threshold: float = 0.7,
    ) -> None:
        self.pipeline = pipeline
        self.accept_threshold = float(accept_threshold)
        self.confidence_threshold = float(confidence_threshold)
        self.log_path = Path(log_path) if log_path else None
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _append_log(self, rec: DecisionRecord) -> None:
        if not self.log_path:
            return
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")

    def run_item(self, item: Dict[str, Any], *, mode: str = "retrieve_verify") -> Dict[str, Any]:
        qid = str(item.get("id") or item.get("qid") or item.get("question_id") or "")
        question = item.get("question") or item.get("query") or item.get("prompt") or ""
        gold = item.get("answer") if "answer" in item else item.get("gold")
        meta: Dict[str, Any] = {"gold_present": gold is not None}

        if mode not in {"retrieve_verify", "self_confidence"}:
            raise ValueError(f"unknown mode: {mode}")

        if self.pipeline is None:
            raw = {"answer": "", "confidence": 0.0, "citations": [], "verified": False}
        else:
            raw = self.pipeline(item)

        answer = str(raw.get("answer") or "")
        citations = normalize_citations(answer, raw.get("citations") or [])
        confidence = float(raw.get("confidence") if raw.get("confidence") is not None else 0.0)
        verified = bool(raw.get("verified")) if "verified" in raw else None

        must_ok, must_errs = validate_must_cite(answer, citations)

        if mode == "retrieve_verify":
            score = float(raw.get("score") if raw.get("score") is not None else confidence)
            ver_ok = bool(verified) if verified is not None else (score >= self.accept_threshold)
            accepted = bool(answer.strip()) and ver_ok and must_ok
        else:
            accepted = bool(answer.strip()) and (confidence >= self.confidence_threshold) and must_ok

        abstained = not accepted
        rec = DecisionRecord(
            qid=qid,
            mode=mode,
            accepted=accepted,
            abstained=abstained,
            confidence=confidence,
            must_cite_ok=must_ok,
            must_cite_errors=must_errs,
            answer_len=len(answer),
            n_citations=len(citations),
            ts_ms=_now_ms(),
            meta=meta,
        )
        self._append_log(rec)

        out = {
            "id": qid,
            "question": question,
            "prediction": answer,
            "citations": citations,
            "accepted": accepted,
            "abstained": abstained,
            "confidence": confidence,
            "mode": mode,
            "must_cite_ok": must_ok,
            "must_cite_errors": must_errs,
        }
        if isinstance(raw, dict):
            for k in ("passages", "sources", "retrieval", "debug"):
                if k in raw:
                    out[k] = raw[k]
        return out

    def run(self, items: Iterable[Dict[str, Any]], *, mode: str = "retrieve_verify") -> List[Dict[str, Any]]:
        return [self.run_item(it, mode=mode) for it in items]


def compute_far_coverage(
    outputs: Iterable[Dict[str, Any]],
    *,
    is_borderline_key: str = "is_borderline",
) -> Dict[str, float]:
    outs = list(outputs)
    n = len(outs)
    if n == 0:
        return {"n": 0, "coverage": 0.0, "far": 0.0}
    accepted = [o for o in outs if bool(o.get("accepted"))]
    coverage = len(accepted) / n
    borderline = [o for o in accepted if bool(o.get(is_borderline_key))]
    far = (len(borderline) / len(accepted)) if accepted else 0.0
    return {"n": float(n), "coverage": float(coverage), "far": float(far)}
