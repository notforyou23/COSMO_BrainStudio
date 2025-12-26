"""Centralized rubric context/constants used to generate CASE_STUDY_RUBRIC.md.
Designed to be deterministic and schema-driven for downstream rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
@dataclass(frozen=True)
class ScoreBand:
    min_score: int
    max_score: int
    label: str
    guidance: str
PROJECT_NAME = "CASE_STUDY_RUBRIC"
RUBRIC_VERSION = "1.0.0"

# High-level themes used to assess relevance; keep stable for deterministic scoring.
THEMES: Tuple[str, ...] = (
    "measurement_design_equity",
    "selection_loops_and_feedback",
    "evaluation_and_accountability",
    "access_and_inclusion",
    "policy_and_institutional_practice",
    "data_practices_and_transparency",
)

# Consolidated workflow intent: schema-driven intake, single index, standardized templates.
WORKFLOW_PRINCIPLES: Tuple[str, ...] = (
    "Schema-driven collection (consistent fields; machine-checkable).",
    "Single intake index to avoid duplicates and hidden partials.",
    "Every claim traceable to authoritative sources via URLs.",
    "Rights and reuse clarity recorded at intake (license/permission status).",
    "Deterministic tagging aligned to a controlled taxonomy.",
)

# Agent insight distilled: measurement design can be an equity lever; cheap signals create selection loops.
AGENT_INSIGHTS: Tuple[str, ...] = (
    "Measurement design choices can encode or amplify inequity; treat metrics as a risk surface.",
    "Self-reinforcing selection loops emerge when institutions rely on cheap, high-volume signals.",
)

INCLUSION_CRITERIA: Tuple[str, ...] = (
    "Clear, verifiable real-world case (org/program/policy/product/research deployment).",
    "Direct relevance to at least one theme in THEMES.",
    "At least one authoritative source URL supporting the core facts.",
    "Sufficient specificity: who/what/when/where; outcomes or observed effects described.",
    "Rights status for any media assets is stated (public domain/CC/licensed/permission/unknown).",
)

EXCLUSION_CRITERIA: Tuple[str, ...] = (
    "Pure opinion/thinkpiece without verifiable underlying case facts.",
    "No authoritative sources available for the central claims.",
    "Duplicate of an existing case study without new evidence or materially new angle.",
    "Case is primarily fictional/speculative or lacks concrete actors/time/place.",
    "Media assets required but rights are explicitly prohibited or cannot be clarified at all.",
)
# Scoring dimensions: each 0-5; weighted to produce a 0-100 total.
SCORING_DIMENSIONS: Tuple[str, ...] = (
    "impact",
    "relevance_to_themes",
    "authoritative_media_urls",
    "rights_clarity",
)

SCORING_WEIGHTS: Dict[str, int] = {
    "impact": 35,
    "relevance_to_themes": 30,
    "authoritative_media_urls": 20,
    "rights_clarity": 15,
}

# Shared 0-5 anchors: used by markdown generator to render concise guidance.
SCORE_ANCHORS: Dict[str, List[Tuple[int, str]]] = {
    "impact": [
        (0, "No discernible outcomes; purely speculative."),
        (1, "Anecdotal impact; unclear beneficiaries or scale."),
        (2, "Small/localized impact with limited evidence."),
        (3, "Moderate impact; credible evidence or clear mechanism."),
        (4, "High impact across org/community; multiple indicators or replication."),
        (5, "Transformational/systemic impact; strong evidence and clear counterfactual framing."),
    ],
    "relevance_to_themes": [
        (0, "No thematic alignment."),
        (1, "Loose mention of a theme without analysis."),
        (2, "One theme is present but peripheral."),
        (3, "One theme is central OR multiple themes are credibly connected."),
        (4, "Multiple themes are central with clear causal story."),
        (5, "Deep engagement with themes, including tradeoffs/risks (e.g., equity lever, selection loop)."),
    ],
    "authoritative_media_urls": [
        (0, "No URLs."),
        (1, "Only secondary commentary; weak provenance."),
        (2, "At least one credible secondary source or partial primary."),
        (3, "At least one authoritative primary source (institution, journal, dataset, filing)."),
        (4, "Multiple authoritative sources with cross-validation."),
        (5, "Authoritative sources plus stable identifiers (DOI, official report IDs) and archived copies."),
    ],
    "rights_clarity": [
        (0, "Rights unknown and cannot be reasonably determined."),
        (1, "Rights unclear; no license info; high risk."),
        (2, "Some license cues but incomplete (e.g., platform terms only)."),
        (3, "Clear rights for key assets (e.g., CC license or explicit permission)."),
        (4, "Clear rights plus documented attribution requirements and allowed derivatives."),
        (5, "Clear rights for all assets; reusable in target channels with documented provenance."),
    ],
}

SCORE_BANDS: Tuple[ScoreBand, ...] = (
    ScoreBand(0, 39, "Reject", "Fails inclusion criteria or too weak/unsafe to publish."),
    ScoreBand(40, 59, "Needs work", "Collect better sources, clarify rights, improve specificity."),
    ScoreBand(60, 79, "Acceptable", "Publishable with light editing; ensure tags and citations."),
    ScoreBand(80, 100, "Strong", "High-value case; ready for featured placement."),
)

# Authoritative source heuristics (used for deterministic rubric language).
AUTHORITATIVE_SOURCE_CLASSES: Tuple[str, ...] = (
    "official_institution_site",
    "peer_reviewed_journal_or_conference",
    "government_or_regulatory",
    "court_filing_or_legal_record",
    "dataset_repository_or_standard_body",
    "original_creator_or_org_press_release_with_supporting_detail",
)

DISCOURAGED_SOURCE_CLASSES: Tuple[str, ...] = (
    "unsourced_social_post",
    "content_farm",
    "scraped_repost",
    "unverifiable_blog",
)
# Tagging rules: designed to map cleanly onto taxonomy helpers in src/taxonomy.py.
# Convention: tags are lower_snake_case; no spaces; stable prefixes for facets.
TAGGING_RULES: Tuple[str, ...] = (
    "Assign at least 1 theme tag: theme/<one_of_THEMES>.",
    "Assign 1-3 domain tags capturing setting (e.g., domain/education, domain/hiring, domain/health).",
    "Assign mechanism tags when present (e.g., mechanism/selection_loop, mechanism/metric_design).",
    "Assign evidence tags based on source type (e.g., evidence/primary, evidence/peer_reviewed).",
    "Assign risk tags for harms/inequity vectors (e.g., risk/bias, risk/exclusion, risk/privacy).",
    "Assign rights tags for media reuse (rights/public_domain, rights/cc, rights/licensed, rights/unknown).",
    "Do not invent new top-level prefixes; use taxonomy-approved categories only.",
)

# Canonical tag suggestions for rubric examples (kept minimal and stable).
CANONICAL_TAGS: Dict[str, Tuple[str, ...]] = {
    "theme": tuple(f"theme/{t}" for t in THEMES),
    "mechanism": ("mechanism/selection_loop", "mechanism/metric_design", "mechanism/incentives"),
    "evidence": ("evidence/primary", "evidence/secondary", "evidence/peer_reviewed"),
    "rights": ("rights/public_domain", "rights/cc", "rights/licensed", "rights/permission", "rights/unknown"),
    "risk": ("risk/bias", "risk/exclusion", "risk/privacy", "risk/feedback_loop"),
}

# Minimal schema for a case-study intake record used by rubric generation copy.
INTAKE_FIELDS: Tuple[str, ...] = (
    "title",
    "summary",
    "actors",
    "geography",
    "timeframe",
    "themes",
    "tags",
    "claims",
    "evidence_urls",
    "media_urls",
    "rights_status",
    "notes",
)
