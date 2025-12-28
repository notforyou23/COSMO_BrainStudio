"""psyprov.uiux_requirements

Machine-readable UI/UX requirement specs for authoring plugins and journal submission/review systems
supporting edition/translation provenance, variant page/paragraph locations, and public-domain
repository citations for primary-source scholarship in psychology.

Design intent: low-friction defaults, progressive disclosure, strong validation, reviewer visibility.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

UIUX_REQUIREMENTS: Dict[str, Any] = {
    "spec_name": "psyprov-uiux",
    "spec_version": "1.0.0",
    "principles": [
        "Minimize author burden with sensible defaults and autofill; keep overrides available.",
        "Prefer structured fields over free text; always show a human-readable citation preview.",
        "Make uncertainty explicit (e.g., 'approximate page' or 'inferred edition') and reviewable.",
        "Fail loud for contradictions; warn for incompleteness; never silently drop provenance.",
        "Support accessibility (WCAG 2.1 AA) and internationalization (Unicode, locale-aware dates).",
    ],
    "entities": {
        "Work": "Underlying intellectual work (e.g., Freud 1900).",
        "Manifestation": "Edition/translation/repository source used by author.",
        "Location": "Page/paragraph/section anchors tied to the manifestation.",
        "RepositoryCitation": "Public-domain repository + stable identifier + access date.",
    },
    "integration_targets": {
        "authoring_plugins": [
            "Word (Office Add-in)",
            "Google Docs (Apps Script/Workspace Add-on)",
            "Zotero/Juris-M translator/extension (optional)",
        ],
        "submission_systems": [
            "Editorial Manager / Aries-like",
            "ScholarOne-like",
            "Open Journal Systems (OJS) plugin",
            "Custom journal portals via iframe/widget",
        ],
        "reviewer_portal": ["Built-in submission UI reviewer view", "PDF/HTML proof overlay (optional)"],
    },
    "ui_components": {
        "provenance_panel": {
            "purpose": "Collect and validate edition/translation/repository metadata for each primary-source citation.",
            "placement": "Right sidebar panel (plugins) / dedicated step (submission systems).",
            "progressive_disclosure": {
                "collapsed_by_default": ["advanced_location_mapping", "ocr_quality", "scan_source_details"],
                "expand_when": ["validation_error", "user_selects('More details')"],
            },
            "citation_preview": {
                "required": True,
                "format": ["human_readable", "machine_json"],
                "updates": "Live as fields change; highlight invalid/missing components.",
            },
        },
        "inline_anchor_tool": {
            "purpose": "Attach a Location record to an in-text citation/quote.",
            "trigger": ["Select text -> 'Add Primary Source Anchor'", "Citation manager insert -> prompt for location"],
            "outputs": ["Location object id", "embedded lightweight marker for export"],
        },
        "reviewer_provenance_card": {
            "purpose": "Show reviewer a compact, auditable summary of provenance & locations per primary-source citation.",
            "must_show": [
                "edition/translation label used",
                "repository (if PD) + identifier + access date",
                "location scheme(s) and any mapping/inference flags",
                "validation warnings/errors at submission time",
            ],
        },
    },
    "forms": {
        "primary_source_record": {
            "title": "Primary Source Provenance",
            "record_key": "psyprov.primary_source",
            "required_when": ["manuscript_contains_primary_source_citations == true"],
            "field_groups": [
                {
                    "group_id": "work_identity",
                    "label": "Work identity",
                    "fields": [
                        {"id": "work_title", "type": "text", "required": True, "max_len": 512},
                        {"id": "work_author", "type": "text", "required": True, "max_len": 256},
                        {"id": "work_date_original", "type": "date_or_year", "required": False},
                        {"id": "work_language_original", "type": "language_code", "required": False, "default": "und"},
                        {"id": "work_standard_id", "type": "identifier", "required": False, "help": "e.g., VIAF/ISNI/DOI/URN."},
                    ],
                },
                {
                    "group_id": "manifestation",
                    "label": "Edition / translation used",
                    "fields": [
                        {"id": "edition_title", "type": "text", "required": True},
                        {"id": "edition_publisher", "type": "text", "required": False},
                        {"id": "edition_year", "type": "year", "required": False},
                        {"id": "translation_language", "type": "language_code", "required": False},
                        {"id": "translator", "type": "text", "required": False},
                        {"id": "editor", "type": "text", "required": False},
                        {"id": "isbn_issn", "type": "identifier", "required": False},
                        {"id": "edition_confidence", "type": "enum", "required": True, "default": "confirmed",
                         "choices": ["confirmed", "inferred_from_context", "unknown"]},
                    ],
                },
                {
                    "group_id": "repository",
                    "label": "Public-domain repository source (if applicable)",
                    "fields": [
                        {"id": "is_public_domain_copy_used", "type": "bool", "required": True, "default": False},
                        {"id": "repository_name", "type": "enum_or_text", "required_if": "is_public_domain_copy_used",
                         "choices": ["Internet Archive", "HathiTrust", "Google Books", "Wikisource", "Project Gutenberg", "Other"]},
                        {"id": "repository_item_id", "type": "text", "required_if": "is_public_domain_copy_used",
                         "help": "Stable identifier (e.g., IA item, Hathi record id, Gutenberg ebook id)."},
                        {"id": "repository_url", "type": "url", "required_if": "is_public_domain_copy_used"},
                        {"id": "access_date", "type": "date", "required_if": "is_public_domain_copy_used"},
                        {"id": "source_file_type", "type": "enum", "required": False, "default": "unknown",
                         "choices": ["pdf", "djvu", "epub", "html", "images", "unknown"]},
                        {"id": "ocr_used", "type": "enum", "required": False, "default": "unknown",
                         "choices": ["yes", "no", "unknown"]},
                    ],
                },
            ],
        },
        "location_record": {
            "title": "Passage Location",
            "record_key": "psyprov.location",
            "required_when": ["primary_source_citation_inserted == true"],
            "fields": [
                {"id": "location_scheme", "type": "enum", "required": True, "default": "page",
                 "choices": ["page", "page_range", "paragraph", "section", "chapter", "folio", "none"]},
                {"id": "page_label", "type": "text", "required_if": "location_scheme in ['page','page_range']",
                 "help": "As printed (supports Roman numerals, prefixes like 'S. 12')."},
                {"id": "page_start", "type": "int", "required_if": "location_scheme == 'page_range'"},
                {"id": "page_end", "type": "int", "required_if": "location_scheme == 'page_range'"},
                {"id": "paragraph_number", "type": "int", "required_if": "location_scheme == 'paragraph'"},
                {"id": "section_label", "type": "text", "required_if": "location_scheme in ['section','chapter']"},
                {"id": "quote_text", "type": "text", "required": False, "max_len": 5000,
                 "help": "Optional excerpt to support matching/audit; stored with privacy controls."},
                {"id": "location_precision", "type": "enum", "required": True, "default": "exact",
                 "choices": ["exact", "approximate", "inferred"]},
                {"id": "variant_mapping", "type": "object", "required": False,
                 "help": "Optional mapping to alternate edition/scan page/paragraph numbering."},
            ],
        },
    },
    "defaults_and_choice_architecture": {
        "default_repository": "Internet Archive",
        "default_access_date": "today_on_first_fill",
        "default_location_scheme": "page",
        "smart_prompts": [
            "If URL matches known repository patterns, pre-fill repository_name and repository_item_id.",
            "If author selects 'translation_language', prompt for translator (optional) and show warning if missing.",
            "If page_label includes Roman numerals, allow 'front matter' hint for mapping.",
        ],
        "reducing_errors": [
            "Hide advanced fields until needed; show inline examples under inputs.",
            "Prefer dropdowns for repositories/languages; allow 'Other' with free text.",
            "Always show a 'Copy formatted provenance note' button for manuscript methods/notes.",
        ],
    },
    "validation_and_error_states": {
        "severity_levels": ["error", "warning", "info"],
        "error_codes": {
            "E_REQUIRED": "Missing required field.",
            "E_BAD_URL": "URL invalid or unsupported scheme.",
            "E_ID_MISMATCH": "Repository id does not match URL pattern.",
            "E_RANGE": "Numeric range invalid (e.g., page_end < page_start).",
            "E_CONTRADICTION": "Conflicting fields (e.g., PD copy used but no repository fields).",
        },
        "examples": [
            {"code": "E_ID_MISMATCH", "when": "repository_name=='Internet Archive' and url not containing '/details/{item_id}'"},
            {"code": "E_RANGE", "when": "location_scheme=='page_range' and page_end < page_start"},
            {"code": "E_CONTRADICTION", "when": "is_public_domain_copy_used==true and repository_url is empty"},
        ],
        "display_rules": {
            "inline": "Show below field with concise fix; link 'Why we ask' tooltip.",
            "panel_summary": "Top-of-panel banner with count by severity; click to scroll to fields.",
            "submission_gate": "Block submission on any 'error'; allow submit with warnings but require acknowledgement checkbox.",
        },
    },
    "reviewer_facing_display": {
        "where": ["reviewer_portal", "exported_review_packet_json", "optional PDF appendix"],
        "card_layout": [
            "Work (author, title, original year/language)",
            "Edition/translation used (publisher/year/translator/editor; confidence)",
            "Repository citation (name, id, URL, access date) if PD copy used",
            "Locations cited (scheme + values; precision; variant mapping flags)",
            "Auto-detection flags (e.g., 'URL recognized', 'edition inferred')",
        ],
        "reviewer_actions": [
            "Open repository URL (new tab)",
            "Copy citation preview",
            "Flag inconsistency (creates query to authors)",
        ],
        "redaction": {"quote_text": "hidden_by_default", "show_on_request": True},
    },
    "export_requirements": {
        "formats": ["JSON (psyprov schema)", "CSL fields (best-effort)", "plain text provenance note"],
        "must_include": ["spec_version", "record_keys", "validation_outcomes", "created_at", "tool_name/tool_version"],
    },
}

def get_uiux_requirements() -> Dict[str, Any]:
    """Return a deep-copied requirements dict safe for mutation."""
    return deepcopy(UIUX_REQUIREMENTS)

def to_json(indent: int = 2, sort_keys: bool = True) -> str:
    return json.dumps(UIUX_REQUIREMENTS, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
