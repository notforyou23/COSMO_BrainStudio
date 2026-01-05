"""psyprov.checklists

Structured, testable checklist specifications for authors, archivists, and journals.
Includes required metadata, validation rules, and escalation paths.
"""
@dataclass(frozen=True)
class ChecklistItem:
    id: str
    label: str
    required: bool = True
    severity: str = "error"  # error|warn
    help: str = ""
    fields: Tuple[str, ...] = ()

@dataclass(frozen=True)
class EscalationPath:
    id: str
    when: str  # machine-readable condition summary
    action: str
    contact: str = ""

@dataclass(frozen=True)
class ChecklistSpec:
    role: str  # author|archivist|journal
    version: str
    items: Tuple[ChecklistItem, ...]
    escalations: Tuple[EscalationPath, ...] = ()
    notes: str = ""

def _get(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur

def _is_nonempty(v: Any) -> bool:
    return v is not None and (not isinstance(v, str) or v.strip() != "")

_DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.I)
_ISBN_RE = re.compile(r"^(?:97[89])?\d{9}[\dX]$", re.I)
_URL_RE = re.compile(r"^https?://", re.I)

def _norm_isbn(x: str) -> str:
    return re.sub(r"[^0-9X]", "", x.upper())

def _validate_field(path: str, v: Any) -> List[str]:
    errs: List[str] = []
    if path.endswith("doi") and _is_nonempty(v):
        if not isinstance(v, str) or not _DOI_RE.match(v.strip()):
            errs.append(f"invalid DOI format: {path}")
    if path.endswith("isbn") and _is_nonempty(v):
        if not isinstance(v, str) or not _ISBN_RE.match(_norm_isbn(v)):
            errs.append(f"invalid ISBN format: {path}")
    if any(path.endswith(s) for s in ("url", "permalink", "landing_page")) and _is_nonempty(v):
        if not isinstance(v, str) or not _URL_RE.match(v.strip()):
            errs.append(f"invalid URL format: {path}")
    return errs

def validate_metadata(spec: ChecklistSpec, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Return a testable validation report for the given spec and metadata."""
    errors: List[str] = []
    warnings: List[str] = []
    missing_required: List[str] = []
    for it in spec.items:
        for f in it.fields:
            val = _get(metadata, f)
            if it.required and not _is_nonempty(val):
                missing_required.append(f)
                (errors if it.severity == "error" else warnings).append(f"missing {f} ({it.id})")
            else:
                for e in _validate_field(f, val):
                    (errors if it.severity == "error" else warnings).append(f"{e} ({it.id})")
    triggers: List[str] = []
    for esc in spec.escalations:
        if esc.id == "ESC_TRANSLATION_UNVERIFIED":
            if _get(metadata, "provenance.translation.is_translation") is True and not _is_nonempty(_get(metadata, "provenance.translation.translator")):
                triggers.append(esc.action)
        if esc.id == "ESC_PD_STATUS_UNCLEAR":
            if _is_nonempty(_get(metadata, "repository.source_url")) and _get(metadata, "repository.public_domain") is None:
                triggers.append(esc.action)
        if esc.id == "ESC_PAGE_MAPPING_MISMATCH":
            if _is_nonempty(_get(metadata, "citation.locator")) and _get(metadata, "variants.page_mapping") in ("unknown", None):
                triggers.append(esc.action)
    return {
        "role": spec.role,
        "version": spec.version,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "missing_required": sorted(set(missing_required)),
        "escalations": triggers,
    }
AUTHOR_CHECKLIST = ChecklistSpec(
    role="author",
    version="1.0",
    notes="Author-facing minimum viable provenance + locator + repository citation requirements.",
    items=(
        ChecklistItem(
            id="A1",
            label="Identify exact edition/translation used",
            fields=("provenance.edition.title", "provenance.edition.publisher", "provenance.edition.year"),
            help="Cite the edition actually consulted; include publisher and year to disambiguate reprints.",
        ),
        ChecklistItem(
            id="A2",
            label="Record translation provenance when applicable",
            required=False,
            severity="warn",
            fields=("provenance.translation.is_translation", "provenance.translation.translator", "provenance.translation.year"),
            help="If using a translation, provide translator and translation year; include source language if known.",
        ),
        ChecklistItem(
            id="A3",
            label="Provide stable repository citation for public-domain or scanned sources",
            fields=("repository.name", "repository.source_url", "repository.accessed", "repository.public_domain"),
            help="Include repository name, stable URL/permalink, access date, and PD/rights statement if available.",
        ),
        ChecklistItem(
            id="A4",
            label="Provide precise in-text locator (page/paragraph/section)",
            fields=("citation.locator",),
            help="Use pages when stable; otherwise paragraph/section identifiers; include range if quoting.",
        ),
        ChecklistItem(
            id="A5",
            label="Declare variant pagination/paragraph mapping approach",
            required=False,
            severity="warn",
            fields=("variants.page_mapping", "variants.paragraph_scheme"),
            help="If multiple editions differ, state mapping method (e.g., PDF page + print page, or paragraph IDs).",
        ),
        ChecklistItem(
            id="A6",
            label="Include identifiers when available (ISBN/DOI)",
            required=False,
            severity="warn",
            fields=("provenance.edition.isbn", "provenance.edition.doi"),
            help="Provide ISBN for books and DOI for digital editions where applicable.",
        ),
    ),
    escalations=(
        EscalationPath(
            id="ESC_TRANSLATION_UNVERIFIED",
            when="is_translation==true AND translator missing",
            action="Ask author to supply translator info or mark translation provenance as unknown with justification.",
            contact="journal_editorial_office",
        ),
        EscalationPath(
            id="ESC_PD_STATUS_UNCLEAR",
            when="repository.source_url present AND repository.public_domain is null",
            action="Request repository rights/PD statement or add a rights uncertainty note in methods/appendix.",
            contact="journal_editorial_office",
        ),
        EscalationPath(
            id="ESC_PAGE_MAPPING_MISMATCH",
            when="locator present AND variants.page_mapping unknown",
            action="Require a locator strategy note (e.g., cite PDF page and print page, or provide paragraph IDs).",
            contact="journal_editorial_office",
        ),
    ),
)
ARCHIVIST_CHECKLIST = ChecklistSpec(
    role="archivist",
    version="1.0",
    notes="Repository/curation checklist for generating high-quality provenance metadata and stable citations.",
    items=(
        ChecklistItem(
            id="R1",
            label="Provide stable, citable landing page/permalink",
            fields=("repository.permalink",),
            help="Permalink should be long-lived and resolve without authentication where possible.",
        ),
        ChecklistItem(
            id="R2",
            label="Capture source bibliographic metadata",
            fields=("provenance.edition.title", "provenance.edition.publisher", "provenance.edition.year"),
            help="Use cataloging standards where available; prefer transcribed title page data.",
        ),
        ChecklistItem(
            id="R3",
            label="Record scan/digitization details",
            required=False,
            severity="warn",
            fields=("repository.digitization.scanner", "repository.digitization.date", "repository.digitization.operator"),
            help="Optional but improves auditability and future QC.",
        ),
        ChecklistItem(
            id="R4",
            label="Expose rights/public-domain statement",
            fields=("repository.public_domain", "repository.rights_statement"),
            help="Provide explicit PD boolean and a human-readable rights statement or link.",
        ),
        ChecklistItem(
            id="R5",
            label="Support page/paragraph addressability",
            required=False,
            severity="warn",
            fields=("variants.page_anchors", "variants.paragraph_scheme"),
            help="If possible, provide page image indices and/or paragraph IDs for stable quotation location.",
        ),
    ),
    escalations=(
        EscalationPath(
            id="ESC_PD_STATUS_UNCLEAR",
            when="public_domain null",
            action="Route item to rights review workflow; publish interim 'rights unknown' flag if unresolved.",
            contact="repository_rights_team",
        ),
    ),
)
JOURNAL_CHECKLIST = ChecklistSpec(
    role="journal",
    version="1.0",
    notes="Editorial policy checklist for enforcing provenance and locator reproducibility.",
    items=(
        ChecklistItem(
            id="J1",
            label="Require provenance metadata in submission",
            fields=("provenance.edition.title", "provenance.edition.publisher", "provenance.edition.year", "citation.locator"),
            help="Submission must include edition and a precise locator for every primary-source quote/claim.",
        ),
        ChecklistItem(
            id="J2",
            label="Require repository citations for digital/PD sources",
            required=False,
            severity="warn",
            fields=("repository.name", "repository.source_url", "repository.accessed"),
            help="If authors used scans/PD texts, require repository citation and access date.",
        ),
        ChecklistItem(
            id="J3",
            label="Require disclosure of translation/edition differences when materially relevant",
            required=False,
            severity="warn",
            fields=("provenance.translation.is_translation", "variants.material_differences"),
            help="If interpretation depends on wording, require note on translation/edition differences.",
        ),
        ChecklistItem(
            id="J4",
            label="Policy: locator robustness for reflowable texts",
            required=False,
            severity="warn",
            fields=("variants.paragraph_scheme", "variants.page_mapping"),
            help="For EPUB/HTML, require paragraph/section scheme or canonical anchors, not just device pages.",
        ),
    ),
    escalations=(
        EscalationPath(
            id="ESC_TRANSLATION_UNVERIFIED",
            when="translation flagged but translator missing",
            action="Editorial query: require translator/source edition details or add limitation statement.",
            contact="handling_editor",
        ),
        EscalationPath(
            id="ESC_PAGE_MAPPING_MISMATCH",
            when="locator present but mapping unknown",
            action="Require addendum describing how locators were derived and how readers can reproduce them.",
            contact="handling_editor",
        ),
    ),
)
CHECKLISTS: Dict[str, ChecklistSpec] = {
    "author": AUTHOR_CHECKLIST,
    "archivist": ARCHIVIST_CHECKLIST,
    "journal": JOURNAL_CHECKLIST,
}

def get_checklist(role: str) -> ChecklistSpec:
    if role not in CHECKLISTS:
        raise KeyError(f"unknown role: {role}")
    return CHECKLISTS[role]

def checklist_to_dict(spec: ChecklistSpec) -> Dict[str, Any]:
    return {
        "role": spec.role,
        "version": spec.version,
        "notes": spec.notes,
        "items": [
            {"id": i.id, "label": i.label, "required": i.required, "severity": i.severity, "help": i.help, "fields": list(i.fields)}
            for i in spec.items
        ],
        "escalations": [
            {"id": e.id, "when": e.when, "action": e.action, "contact": e.contact}
            for e in spec.escalations
        ],
    }
