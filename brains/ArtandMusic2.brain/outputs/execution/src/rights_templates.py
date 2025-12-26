"""
rights_templates.py

Template text and constants for generating:
- outputs/rights/RIGHTS_AND_LICENSING_CHECKLIST.md
- outputs/rights/RIGHTS_LOG.csv

This module intentionally contains only static templates/schema.
"""
CSV_COLUMNS = [
    "exemplar_id",
    "title",
    "creator",
    "source_url",
    "license_type",
    "proof_url/screenshot_ref",
    "usage_decision",
    "notes",
    "date_checked",
]

CSV_HEADER = ",".join(CSV_COLUMNS)
CHECKLIST_TEMPLATE_MD = """# Rights & Licensing Checklist

Use this checklist for every asset (image, audio, video, text excerpt, dataset, chart, icon, font, code snippet, model weights, etc.) that will be used, distributed, or published.

## 0) Project metadata
- Project / deliverable name:
- Owner / requester:
- Intended distribution: internal only / public web / app / print / broadcast / other
- Jurisdictions of distribution (if known):
- Publication date (planned):
- Reviewer(s) and dates:

## 1) Asset inventory (what are we using?)
For each asset, create a row in `RIGHTS_LOG.csv` and assign a stable `exemplar_id`.

Minimum fields to capture:
- Title or short description
- Creator / author / rights holder (if known)
- Source URL (where you got it)
- License type (or status if unknown)
- Proof reference (URL, snapshot, email, contract filename, ticket link)
- Usage decision and notes

## 2) Confirm provenance and authenticity
Per asset:
- [ ] Source is the original publisher or an authoritative repository (not a re-upload) OR re-use is clearly permitted.
- [ ] The asset is not scraped from a platform whose terms prohibit reuse.
- [ ] Any required attribution/credit line is available and accurate.
- [ ] If the asset is user-generated content, confirm the uploader had the rights to grant the license.

## 3) Determine license / rights status
Select the most accurate status and record it in `license_type` with supporting proof.

Common license/status categories (examples):
- Public Domain (e.g., CC0, US federal government work, PD mark, expired copyright)
- Creative Commons: CC BY / BY-SA / BY-NC / BY-NC-SA / BY-ND / BY-NC-ND
- Open licenses (e.g., MIT/Apache-2.0 for code; OFL for fonts; Open Data licenses)
- Proprietary / All rights reserved (requires permission or purchase)
- Licensed via subscription/marketplace (requires plan/seat/terms compliance)
- Permission granted (email/contract) with explicit scope
- Fair use / fair dealing (only with documented rationale; consult counsel where applicable)
- Unknown / unclear (do not use)

Checklist:
- [ ] License text/terms are located and linked in `proof_url/screenshot_ref`.
- [ ] License version and any exceptions are recorded (e.g., CC BY 4.0).
- [ ] If the license is ambiguous, the asset is marked **Unknown** and not used until resolved.

## 4) Validate license compatibility with intended use
Per asset, validate all applicable constraints:
- [ ] Commercial use allowed? (If the project is monetized, sponsored, or promotional, treat as commercial.)
- [ ] Derivatives allowed? (editing, cropping, remix, color grading, adaptation, translation, model training)
- [ ] Share-alike obligations understood and acceptable (BY-SA, copyleft code licenses).
- [ ] No-derivatives restrictions respected (BY-ND: no adaptations; typically only verbatim use).
- [ ] Non-commercial restrictions respected (BY-NC: avoid unclear edge cases; document decision).
- [ ] Any platform-specific terms are considered (APIs, marketplaces, stock libraries).

## 5) Attribution and notice requirements
If attribution is required:
- [ ] Attribution text prepared (title, creator, license, source link where possible).
- [ ] Placement defined (caption, credits page, about screen, metadata, README).
- [ ] License notice included where required (e.g., OSS notices file).
- [ ] Modifications are disclosed if required/expected.

Recommended attribution format:
> “{Title}” by {Creator}, {License} ({License URL}), via {Source URL}. Changes: {Yes/No}.

## 6) Releases, privacy, and sensitive content (if applicable)
For photos/video/audio with identifiable people/places:
- [ ] Model release obtained when required (especially for commercial/promotional use).
- [ ] Property/location releases considered (private property, trademarks, museums, venues).
- [ ] Consent confirmed for minors or vulnerable subjects; guardian consent where required.
- [ ] Privacy review completed for personal data, faces, license plates, addresses, voices.
- [ ] If AI-generated content includes likeness of real persons, confirm permissions and local laws.

## 7) Trademarks, brands, and endorsements
- [ ] Trademarks/logos assessed; usage is nominative or licensed where needed.
- [ ] No implied endorsement or affiliation unless explicitly authorized.
- [ ] Brand guidelines followed if a brand license exists.

## 8) Decision and documentation
For each asset, set `usage_decision` to one of:
- Approved
- Approved with conditions (e.g., attribution required, no-derivatives, limited channels)
- Replace / do not use
- Pending (needs clarification)

Checklist:
- [ ] Decision recorded in `RIGHTS_LOG.csv` with date checked.
- [ ] Proof captured (URL or screenshot reference) sufficient for audit.
- [ ] Any conditions are documented in `notes`.
- [ ] If replaced, the replacement asset gets a new row with a new `exemplar_id`.

## 9) Retention and audit readiness
- [ ] Keep copies of licenses, receipts, emails, and screenshots with timestamps.
- [ ] Store proof in an internal system with stable links.
- [ ] Re-check licenses for long-lived projects (recommended: at least annually or when republishing).

---

## Quick reference: red flags (do not use until resolved)
- No clear license or rights statement.
- “Free to download” without reuse rights.
- Watermarked stock images.
- Re-uploads without attribution or licensing info.
- Conflicting license claims across pages or versions.
- Terms forbid redistribution, modification, or commercial use (when applicable).
"""
