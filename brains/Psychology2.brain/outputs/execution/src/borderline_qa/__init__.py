"""borderline_qa package.

Baseline retrieve-then-verify pipeline and evaluation utilities with explicit "must-cite"
constraints (quote + URL/DOI + span mapping). Public API is exposed via lazy imports to
keep package import light and to allow partial module availability during development.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, List, Tuple

__all__ = [
    "__version__",
    "get_default_pipeline",
]

__version__ = "0.1.0"

# attr -> (module, symbol)
_LAZY_ATTRS: Dict[str, Tuple[str, str]] = {
    # citations
    "Citation": ("borderline_qa.citations", "Citation"),
    "CitationSpan": ("borderline_qa.citations", "CitationSpan"),
    "MustCite": ("borderline_qa.citations", "MustCite"),
    "MustCiteViolation": ("borderline_qa.citations", "MustCiteViolation"),
    "normalize_provenance_ref": ("borderline_qa.citations", "normalize_provenance_ref"),
    "validate_must_cite": ("borderline_qa.citations", "validate_must_cite"),
    # retrieval
    "RetrievedPassage": ("borderline_qa.retriever", "RetrievedPassage"),
    "Retriever": ("borderline_qa.retriever", "Retriever"),
    "BaselineRetriever": ("borderline_qa.retriever", "BaselineRetriever"),
    # verification
    "VerificationResult": ("borderline_qa.verifier", "VerificationResult"),
    "Verifier": ("borderline_qa.verifier", "Verifier"),
    "BaselineVerifier": ("borderline_qa.verifier", "BaselineVerifier"),
    "retrieve_then_verify": ("borderline_qa.verifier", "retrieve_then_verify"),
    # evaluation / harness (if present)
    "BorderlineQAEvaluator": ("borderline_qa.eval", "BorderlineQAEvaluator"),
    "evaluate_borderline_qa": ("borderline_qa.eval", "evaluate_borderline_qa"),
}


def __getattr__(name: str) -> Any:
    spec = _LAZY_ATTRS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod_name, sym_name = spec
    try:
        mod = import_module(mod_name)
    except Exception as e:  # pragma: no cover
        raise ImportError(f"Failed to import {mod_name!r} required for attribute {name!r}: {e}") from e
    try:
        value = getattr(mod, sym_name)
    except AttributeError as e:  # pragma: no cover
        raise ImportError(
            f"Module {mod_name!r} does not define expected symbol {sym_name!r} for attribute {name!r}"
        ) from e
    globals()[name] = value
    return value


def __dir__() -> List[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY_ATTRS.keys())))


def get_default_pipeline(*, retriever_kwargs: Dict[str, Any] | None = None, verifier_kwargs: Dict[str, Any] | None = None) -> Any:
    """Create the default retrieve-then-verify pipeline.

    Returns:
        An object with (retriever, verifier) attributes when available, otherwise raises ImportError.
    """
    retriever_kwargs = {} if retriever_kwargs is None else dict(retriever_kwargs)
    verifier_kwargs = {} if verifier_kwargs is None else dict(verifier_kwargs)

    BaselineRetriever = __getattr__("BaselineRetriever")
    BaselineVerifier = __getattr__("BaselineVerifier")

    retriever = BaselineRetriever(**retriever_kwargs)
    verifier = BaselineVerifier(**verifier_kwargs)

    class _Pipeline:
        __slots__ = ("retriever", "verifier")

        def __init__(self, retriever: Any, verifier: Any) -> None:
            self.retriever = retriever
            self.verifier = verifier

    return _Pipeline(retriever, verifier)
