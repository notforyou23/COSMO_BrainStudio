"""psyprim: primary-source scholarship workflows + lightweight detection.

This package provides:
- Standardized workflow and metadata checklist generation for primary-source scholarship in psychology.
- Lightweight citation/provenance detection utilities intended for audits and QA checks.

Public API is intentionally small and stable; advanced schemas and CLI live in submodules.
"""
from __future__ import annotations

from importlib import metadata as _metadata
from typing import Any, Dict, Iterable, Optional, Sequence, Union

__all__ = [
    "__version__",
    "generate_roadmap",
    "generate_workflow_bundle",
    "generate_metadata_checklist",
    "make_survey_instrument",
    "make_audit_study_design",
    "detect_primary_source_citations",
]
def _pkg_version() -> str:
    try:
        return _metadata.version("psyprim")
    except _metadata.PackageNotFoundError:
        return "0.0.0"


__version__ = _pkg_version()
def generate_roadmap(
    *,
    project_name: str = "psyprim_primary_source_roadmap",
    community: str = "psychology",
    outputs_dir: Optional[Union[str, "os.PathLike[str]"]] = None,
    include_detection_features: bool = True,
) -> Dict[str, Any]:
    """Return a concrete, testable roadmap spec as a JSON-serializable dict.

    Notes:
      - This is a convenience wrapper around schema builders in psyprim.schemas.
      - If schemas are unavailable (partial installs), raises ImportError.
    """
    from . import schemas as _schemas  # local import to keep import side-effects minimal

    return _schemas.build_roadmap(
        project_name=project_name,
        community=community,
        outputs_dir=str(outputs_dir) if outputs_dir is not None else None,
        include_detection_features=include_detection_features,
    )
def generate_workflow_bundle(
    *,
    scope: str = "primary_source_scholarship",
    format: str = "json",
) -> Dict[str, Any]:
    """Generate standardized workflows + checklists bundle (JSON-serializable)."""
    from . import schemas as _schemas

    return _schemas.build_workflow_bundle(scope=scope, format=format)
def generate_metadata_checklist(
    *,
    focus: str = "edition_translation_provenance",
) -> Dict[str, Any]:
    """Generate a metadata checklist template for primary-source citations."""
    from . import schemas as _schemas

    return _schemas.build_metadata_checklist(focus=focus)
def make_survey_instrument(
    *,
    audience: str = "researchers",
    mode: str = "online",
) -> Dict[str, Any]:
    """Create a survey instrument spec for workflow/metadata adoption evaluation."""
    from . import schemas as _schemas

    return _schemas.build_survey_instrument(audience=audience, mode=mode)
def make_audit_study_design(
    *,
    sampling_frame: str = "recent_psychology_articles",
    unit_of_analysis: str = "paper",
) -> Dict[str, Any]:
    """Create an audit study design spec for validating citation provenance signals."""
    from . import schemas as _schemas

    return _schemas.build_audit_study_design(
        sampling_frame=sampling_frame,
        unit_of_analysis=unit_of_analysis,
    )
def detect_primary_source_citations(
    text: Union[str, bytes],
    *,
    source_path: Optional[str] = None,
    return_spans: bool = False,
    features: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Run lightweight detection on text and return JSON-serializable results.

    The detector is intentionally lightweight and favors:
      - edition/translation provenance cues
      - variant pagination cues (roman numerals, dual pagination, plate/page)
      - repository citations (DOI, JSTOR, HathiTrust, Internet Archive, PsyArXiv, OSF)
    """
    from . import schemas as _schemas

    return _schemas.detect_primary_source_citations(
        text=text,
        source_path=source_path,
        return_spans=return_spans,
        features=list(features) if features is not None else None,
    )
