"""Built-in default templates and controlled vocabularies.

These defaults support generating community-endorsed protocols (checklists,
metadata schemas) and lightweight tooling requirements for provenance-aware
primary-source psychology scholarship.
"""
from __future__ import annotations

from typing import Dict, List, Any

VERSION = "0.1.0"

STAKEHOLDER_ROLES: List[Dict[str, Any]] = [
  {"id":"primary_source_scholar","label":"Primary-source scholar","what_they_contribute":["research workflows","pain points","gold-standard examples"],"engagement_modes":["interviews","co-design workshop","pilot adoption"]},
  {"id":"digital_humanist","label":"Digital humanist / text-encoding specialist","what_they_contribute":["TEI/standards mapping","annotation practice","interoperability"],"engagement_modes":["standards review","schema alignment sprint"]},
  {"id":"librarian_archivist","label":"Librarian / archivist","what_they_contribute":["collection metadata norms","repository citation practice","persistent IDs"],"engagement_modes":["metadata clinic","repository partnerships"]},
  {"id":"publisher_editor","label":"Publisher / editor","what_they_contribute":["edition practices","page/paragraph conventions","errata handling"],"engagement_modes":["roundtable","publisher feedback cycle"]},
  {"id":"translator","label":"Translator / translation scholar","what_they_contribute":["translation provenance fields","variant wording notes","alignment practice"],"engagement_modes":["translation focus group","template review"]},
  {"id":"software_maintainer","label":"Tool maintainer (Zotero/Obsidian/Word/LaTeX/etc.)","what_they_contribute":["plugin feasibility","UI constraints","release channels"],"engagement_modes":["tech design review","beta program"]},
  {"id":"repository_operator","label":"Public-domain repository operator","what_they_contribute":["canonical URLs","API/metadata availability","citation expectations"],"engagement_modes":["integration workshop","API liaison"]},
  {"id":"open_science_org","label":"Open scholarship/standards org","what_they_contribute":["governance models","endorsement pathways","community comms"],"engagement_modes":["endorsement briefing","steering committee"]},
  {"id":"irb_ethics","label":"IRB/ethics & research integrity advisor","what_they_contribute":["survey/audit ethics","participant privacy","risk review"],"engagement_modes":["protocol review","data management plan signoff"]},
]

CHECKLIST_ITEMS: List[Dict[str, Any]] = [
  {"id":"scope_define","category":"Scope","text":"Define corpus scope (authors/works/languages/time window) and supported repositories/tools.","evidence":"written scope statement"},
  {"id":"edition_identify","category":"Provenance","text":"Identify the cited edition/printing (publisher, year, place, series/volume, ISBN/OCLC if available).","evidence":"bibliographic fields filled + scan title page if possible"},
  {"id":"translation_identify","category":"Provenance","text":"If translated: record translator, source language, translation year, and whether abridged/annotated.","evidence":"translator + translation notes"},
  {"id":"repo_capture","category":"Repository","text":"Record public-domain repository details (repository name, stable URL, access date, and repository-provided identifier).","evidence":"URL + access date + repo ID"},
  {"id":"pd_status","category":"Rights","text":"Record public-domain/risk note (jurisdiction basis or repository statement).","evidence":"PD note field completed"},
  {"id":"locators_normalize","category":"Locators","text":"Normalize locators: page range + (if present) paragraph/section markers; specify how locators map to digital text.","evidence":"locator mapping documented"},
  {"id":"variant_detect","category":"Variants","text":"Run variant checks (pagination shifts, missing pages, OCR anomalies, abridgment indicators) and annotate detected issues.","evidence":"variant report attached"},
  {"id":"quote_anchor","category":"Quotations","text":"For quotations, store a canonical anchor (page/para + short context string) to enable re-finding across editions.","evidence":"anchor fields present"},
  {"id":"citation_render","category":"Citations","text":"Render citation using repository-aware form including edition + repository URL/ID.","evidence":"citation output matches style rule"},
  {"id":"qa_doublecheck","category":"Quality assurance","text":"Second-person review of a sample (e.g., 10%) for correctness of edition/translation and locator mapping.","evidence":"audit log + error rate"},
]

CONTROLLED_VOCAB: Dict[str, List[Dict[str, str]]] = {
  "provenance_relation":[
    {"id":"same_edition","label":"Same edition","desc":"Digital artifact corresponds to the cited print edition."},
    {"id":"different_edition","label":"Different edition","desc":"Digital artifact is a different edition/printing than cited."},
    {"id":"translation_of","label":"Translation of","desc":"Artifact is a translation of a source work/edition."},
    {"id":"abridged","label":"Abridged","desc":"Artifact omits material relative to a standard/reference edition."},
    {"id":"annotated","label":"Annotated","desc":"Artifact adds editorial notes, introductions, or commentary."},
    {"id":"ocr_derived","label":"OCR-derived text","desc":"Text produced via OCR; may contain errors and layout loss."},
  ],
  "locator_system":[
    {"id":"page","label":"Page","desc":"Printed page number system."},
    {"id":"folio","label":"Folio","desc":"Front/back folio markers common in early prints."},
    {"id":"paragraph","label":"Paragraph marker","desc":"Explicit paragraph numbering/markers in edition."},
    {"id":"section","label":"Section/chapter","desc":"Hierarchical section numbering or headings."},
    {"id":"line","label":"Line number","desc":"Line references (rare; more stable in poetry/critical eds)."},
  ],
  "confidence":[
    {"id":"high","label":"High","desc":"Verified against title page/front matter or authoritative catalog."},
    {"id":"medium","label":"Medium","desc":"Inferred from repository metadata; not independently verified."},
    {"id":"low","label":"Low","desc":"Best guess; conflicting or missing evidence."},
  ],
}

METADATA_FIELDS: List[Dict[str, Any]] = [
  {"name":"work_title","type":"string","required":True,"desc":"Title of the intellectual work being cited."},
  {"name":"work_author","type":"string","required":True,"desc":"Author(s) of the work."},
  {"name":"language","type":"string","required":True,"desc":"Language of the cited artifact."},
  {"name":"edition_statement","type":"string","required":False,"desc":"Edition/printing statement as printed (e.g., '2nd ed.')."},
  {"name":"publication_year","type":"integer","required":False,"desc":"Year printed/published for the cited artifact."},
  {"name":"publisher","type":"string","required":False,"desc":"Publisher/imprint."},
  {"name":"place_of_publication","type":"string","required":False,"desc":"Place of publication."},
  {"name":"identifiers","type":"object","required":False,"desc":"Known IDs (ISBN, OCLC, LCCN, DOI, etc.).","subfields":["isbn","oclc","lccn","doi","ark","handle","other"]},
  {"name":"translation","type":"object","required":False,"desc":"Translation provenance if applicable.","subfields":["translator","source_language","source_work_ref","translation_year","is_abridged","notes"]},
  {"name":"repository","type":"object","required":True,"desc":"Public-domain repository source of the digital artifact.","subfields":["name","stable_url","access_date","repository_id","api_url","license_statement"]},
  {"name":"digital_artifact","type":"object","required":False,"desc":"Details of the digital file/text used.","subfields":["format","file_checksum","ocr_engine","ocr_confidence_note","scan_quality_note"]},
  {"name":"provenance_assertion","type":"object","required":True,"desc":"Assertion linking cited artifact to digital artifact.","subfields":["relation","confidence","evidence_note","checked_by","checked_on"]},
  {"name":"locators","type":"object","required":True,"desc":"Locator normalization and mapping for quoting/citation.","subfields":["system","page_start","page_end","page_labeling_note","paragraph_marker","section_label","anchor_text"]},
  {"name":"variant_notes","type":"array","required":False,"desc":"Detected/known variants affecting retrieval.","items":["pagination_shift","missing_pages","reflowed_text","added_preface","different_translation","other"]},
  {"name":"citation_rendered","type":"string","required":False,"desc":"Fully rendered citation string (style-dependent)."},
]

REPOSITORY_CITATION_FORMS: Dict[str, Dict[str, Any]] = {
  "general_template":{
    "required_fields":["work_author","work_title","publication_year","edition_statement","publisher","place_of_publication","repository.name","repository.stable_url","repository.access_date"],
    "pattern":"{work_author}. ({publication_year}). {work_title} ({edition_statement}). {place_of_publication}: {publisher}. Retrieved {repository.access_date}, from {repository.name}: {repository.stable_url}",
    "notes":["Always include edition/printing if known.","Prefer repository stable URL or persistent ID landing page.","If repository provides an item ID, include it in parentheses after repository name."],
  },
  "internet_archive":{
    "repository_name":"Internet Archive",
    "id_field":"repository_id",
    "id_hint":"internetarchive:identifier (e.g., 'psychologyof...')",
    "pattern":"{work_author}. ({publication_year}). {work_title} ({edition_statement}). {place_of_publication}: {publisher}. Internet Archive (Item {repository.repository_id}). Retrieved {repository.access_date}, from {repository.stable_url}",
  },
  "hathitrust":{
    "repository_name":"HathiTrust",
    "id_field":"repository_id",
    "id_hint":"HTID or record/volume identifier",
    "pattern":"{work_author}. ({publication_year}). {work_title} ({edition_statement}). HathiTrust (ID {repository.repository_id}). Retrieved {repository.access_date}, from {repository.stable_url}",
  },
  "gutenberg":{
    "repository_name":"Project Gutenberg",
    "id_field":"repository_id",
    "id_hint":"EBook number",
    "pattern":"{work_author}. ({publication_year}). {work_title}. Project Gutenberg (EBook #{repository.repository_id}). Retrieved {repository.access_date}, from {repository.stable_url}",
  },
  "wikisource":{
    "repository_name":"Wikisource",
    "id_field":"repository_id",
    "id_hint":"Page title/revision ID if stable",
    "pattern":"{work_author}. ({publication_year}). {work_title}. Wikisource ({repository.repository_id}). Retrieved {repository.access_date}, from {repository.stable_url}",
  },
}

MILESTONE_METRICS: Dict[str, Dict[str, Any]] = {
  "stakeholder_coverage":{
    "definition":"Number of distinct stakeholder roles engaged with documented feedback.",
    "unit":"roles",
    "target_by_phase":{"P1":5,"P2":7,"P3":9},
    "collection_method":"engagement log + meeting notes"},
  "protocol_endorsements":{
    "definition":"Organizations/projects publicly endorsing or adopting the protocol/checklists.",
    "unit":"endorsements",
    "target_by_phase":{"P1":2,"P2":6,"P3":12},
    "collection_method":"public statements + maintainers confirmation"},
  "tool_integrations":{
    "definition":"Working integrations (plugins/exporters) released for common tools.",
    "unit":"integrations",
    "target_by_phase":{"P1":1,"P2":3,"P3":5},
    "collection_method":"release tags + install counts"},
  "citation_completeness_rate":{
    "definition":"Percent of sampled citations containing edition/translation + repository stable URL/ID + access date.",
    "unit":"percent",
    "target_by_phase":{"P1":70,"P2":85,"P3":92},
    "collection_method":"audit study of manuscripts/bibliographies"},
  "locator_retrievability_rate":{
    "definition":"Percent of sampled quotations retrievable in the referenced digital artifact using recorded locators/anchors.",
    "unit":"percent",
    "target_by_phase":{"P1":75,"P2":88,"P3":95},
    "collection_method":"auditor re-finding task with time limit"},
  "variant_detection_precision":{
    "definition":"Precision of automated variant flags (true positives / all flagged).",
    "unit":"percent",
    "target_by_phase":{"P1":60,"P2":75,"P3":85},
    "collection_method":"manual adjudication on labeled test set"},
  "author_burden_minutes":{
    "definition":"Median additional time per cited primary source to meet protocol requirements.",
    "unit":"minutes",
    "target_by_phase":{"P1":15,"P2":10,"P3":7},
    "collection_method":"survey + timed usability sessions"},
}
