"""claims_audit

Public package API for:
- atomic-claim schema + labels
- curated reference corpus loading/search views
- retrieval + auditing utilities
- tiered false-accept / abstain metrics

This module re-exports the main user-facing types and functions so that downstream
code can import from `claims_audit` directly.

The implementation is intentionally import-tolerant: if optional submodules are
not present in a minimal installation, attribute access will fail with an
informative ImportError originating from the missing module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "__version__",
    # schema
    "ClaimLabel",
    "AtomicClaim",
    "ClaimFieldNormalization",
    "ClaimSchemaVersion",
    "ClaimAuditResult",
    # corpus
    "ReferenceDocument",
    "ReferenceEvidenceSpan",
    "ReferenceCorpus",
    # retrieval
    "RetrievedEvidence",
    "Retriever",
    "TfidfRetriever",
    # auditing
    "audit_claims",
    "audit_claim",
    # metrics
    "TieredAuditMetrics",
    "compute_tiered_metrics",
]

__version__ = "0.1.0"

if TYPE_CHECKING:
    # schema
    from .schema import (
        AtomicClaim,
        ClaimAuditResult,
        ClaimFieldNormalization,
        ClaimLabel,
        ClaimSchemaVersion,
    )

    # corpus
    from .corpus import ReferenceCorpus, ReferenceDocument, ReferenceEvidenceSpan

    # retrieval
    from .retrieval import RetrievedEvidence, Retriever, TfidfRetriever

    # auditing
    from .audit import audit_claim, audit_claims

    # metrics
    from .metrics import TieredAuditMetrics, compute_tiered_metrics


def __getattr__(name: str):
    # Lazy attribute resolution for a clean top-level API.
    if name in {
        "ClaimLabel",
        "AtomicClaim",
        "ClaimFieldNormalization",
        "ClaimSchemaVersion",
        "ClaimAuditResult",
    }:
        from . import schema as _schema

        return getattr(_schema, name)

    if name in {"ReferenceDocument", "ReferenceEvidenceSpan", "ReferenceCorpus"}:
        from . import corpus as _corpus

        return getattr(_corpus, name)

    if name in {"RetrievedEvidence", "Retriever", "TfidfRetriever"}:
        from . import retrieval as _retrieval

        return getattr(_retrieval, name)

    if name in {"audit_claims", "audit_claim"}:
        from . import audit as _audit

        return getattr(_audit, name)

    if name in {"TieredAuditMetrics", "compute_tiered_metrics"}:
        from . import metrics as _metrics

        return getattr(_metrics, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
