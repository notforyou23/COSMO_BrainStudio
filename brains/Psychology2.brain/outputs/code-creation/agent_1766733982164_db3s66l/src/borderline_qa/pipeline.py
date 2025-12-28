from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple, Union

try:
    from .retriever import retrieve as default_retrieve  # type: ignore
except Exception:  # pragma: no cover
    default_retrieve = None

try:
    from .citations import validate_must_cite  # type: ignore
except Exception:  # pragma: no cover
    validate_must_cite = None


Json = Dict[str, Any]


class Retriever(Protocol):
    def __call__(self, question: str, *, k: int = 8, **kwargs: Any) -> List[Json]: ...


class Generator(Protocol):
    def __call__(self, question: str, passages: Sequence[Json], *, mode: str, **kwargs: Any) -> Union[str, Json]: ...


@dataclass(frozen=True)
class PipelineConfig:
    k: int = 8
    self_confidence_threshold: float = 0.8
    require_must_cite: bool = True
    mode: str = "must_cite"  # "must_cite" | "self_confidence"
    strict: bool = True


def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _normalize_answer_payload(payload: Union[str, Mapping[str, Any]]) -> Json:
    if isinstance(payload, str):
        return {"answer": payload, "citations": [], "confidence": None}
    out: Json = dict(payload)
    out.setdefault("answer", "")
    out.setdefault("citations", [])
    out.setdefault("confidence", None)
    return out


def _default_generator(question: str, passages: Sequence[Json], *, mode: str, **_: Any) -> Json:
    ctx = []
    for p in passages[:3]:
        sid = p.get("id") or p.get("source_id") or ""
        title = p.get("title") or ""
        url = p.get("url") or p.get("doi") or ""
        text = p.get("text") or p.get("content") or ""
        ctx.append(f"[{sid}] {title} {url}\n{text}".strip())
    answer = "I don't know."
    if ctx:
        answer = "Based on the provided sources, I cannot reliably answer without an LLM. Retrieved context is available."
    return {"answer": answer, "citations": [], "confidence": None, "mode": mode, "retrieved_context": ctx}
class RetrieveThenVerifyPipeline:
    """End-to-end pipeline for the borderline QA harness.

    Contract:
      - Call with question -> returns dict with keys:
        answer, accepted, reject_reason, mode, passages, citations, confidence, verification
      - 'must_cite' mode enforces deterministic must-cite validation if available.
      - 'self_confidence' mode accepts if confidence >= threshold (no citation enforcement by default).
    """

    def __init__(
        self,
        retriever: Optional[Retriever] = None,
        generator: Optional[Generator] = None,
        *,
        config: Optional[PipelineConfig] = None,
    ) -> None:
        self.config = config or PipelineConfig()
        if retriever is None:
            if default_retrieve is None:
                raise RuntimeError("No retriever provided and borderline_qa.retriever.retrieve is unavailable.")
            retriever = default_retrieve
        self.retriever: Retriever = retriever
        self.generator: Generator = generator or _default_generator

    def __call__(self, question: str, **kwargs: Any) -> Json:
        cfg = self.config
        mode = str(kwargs.pop("mode", cfg.mode))
        passages = self.retriever(question, k=int(kwargs.pop("k", cfg.k)), **kwargs)

        gen_payload = self.generator(question, passages, mode=mode, **kwargs)
        payload = _normalize_answer_payload(gen_payload)
        payload["mode"] = mode
        payload["passages"] = passages

        accepted = False
        reject_reason: Optional[str] = None
        verification: Json = {"performed": False, "ok": None, "errors": []}

        if mode == "self_confidence":
            conf = _as_float(payload.get("confidence"))
            payload["confidence"] = conf
            if conf is not None and conf >= cfg.self_confidence_threshold:
                accepted = True
            else:
                accepted = False
                reject_reason = "low_confidence"
        else:  # must_cite (default)
            if cfg.require_must_cite:
                if validate_must_cite is None:
                    accepted = False
                    reject_reason = "must_cite_validator_unavailable"
                    verification = {"performed": False, "ok": False, "errors": [reject_reason]}
                else:
                    verification["performed"] = True
                    try:
                        res = validate_must_cite(
                            answer_text=str(payload.get("answer", "")),
                            citations=list(payload.get("citations") or []),
                            passages=passages,
                            strict=bool(cfg.strict),
                        )
                        # expected: {ok: bool, errors: [...], normalized_citations?: [...]}
                        ok = bool(res.get("ok", False))
                        verification["ok"] = ok
                        verification["errors"] = list(res.get("errors") or [])
                        if "normalized_citations" in res:
                            payload["citations"] = res["normalized_citations"]
                        accepted = ok
                        if not ok:
                            reject_reason = "citation_verification_failed"
                    except Exception as e:
                        accepted = False
                        reject_reason = "citation_verification_exception"
                        verification["ok"] = False
                        verification["errors"] = [f"{type(e).__name__}: {e}"]
            else:
                accepted = True

        payload["accepted"] = accepted
        payload["reject_reason"] = reject_reason
        payload["verification"] = verification
        return payload


def make_pipeline(
    retriever: Optional[Retriever] = None,
    generator: Optional[Generator] = None,
    *,
    config: Optional[PipelineConfig] = None,
) -> RetrieveThenVerifyPipeline:
    return RetrieveThenVerifyPipeline(retriever=retriever, generator=generator, config=config)
