# Intake Checklist (Claim Cards)

Purpose: ensure every claim card captures **exact claim text (verbatim)** plus **context** and a **provenance anchor** so downstream validation can be strict and reproducible.

## Required fields (MUST be present)

### 1) Verbatim claim text (exact)
- **claim_text_verbatim**: the claim as stated in the source, **word-for-word**.
- Preserve original wording, qualifiers, and hedges (e.g., “may”, “could”, “up to”, “on average”).
- Do **not** summarize, paraphrase, translate, or “clean up” grammar.
- If the source is a table/figure, transcribe the claim exactly (including units/denominators).

### 2) Context (speaker + date + link)
Provide enough context to uniquely identify *who said it, when, and where*:
- **speaker**: person/organization making the claim (as labeled in the source).
- **date**: publication or spoken date (ISO preferred: YYYY-MM-DD; otherwise the most precise available).
- **source_link**: canonical URL (or stable repository link). If paywalled, include the best available public landing link.

### 3) Provenance anchor (pinpoint within the source)
Provide a **provenance_anchor** that lets a reviewer jump directly to the claim in the source:
- For web pages: section heading + paragraph quote start, or a fragment link, and (when possible) an archived link.
- For PDFs: page number(s) + surrounding quoted snippet; include document title and (if available) a stable PDF URL.
- For video/audio: timestamp range (e.g., 12:34–12:58) + platform link.
- For datasets: file name + row/column identifiers + commit/hash/version.

Minimum requirement: the anchor must be specific enough that a third party can locate the exact claim within ~30 seconds.

## Validation rules (fail/abstain conditions)

A claim card MUST be marked **ABSTAIN / INVALID** (and not used for scoring) if any of the following are true:

### Missing required fields
- claim_text_verbatim is missing/empty.
- speaker is missing/empty.
- date is missing/empty/unknown (unless the source truly contains no date; then provide best-available and explicitly note “no date in source” in the anchor).
- source_link is missing/empty.
- provenance_anchor is missing/empty.

### Not actually verbatim
- claim_text_verbatim contains paraphrase, added interpretation, merged sentences from multiple places, or inferred numbers.
- claim_text_verbatim uses brackets/ellipses that change meaning, or removes qualifiers.
- claim_text_verbatim is translated when the source is in another language (unless the source itself provides an official translation; then include the original + official translation clearly labeled).

### Context does not match the claim
- speaker/date/link correspond to a different document, a secondary citation, or a repost unless the repost is the analyzed source and is clearly identified as such.
- the card cites “someone said X” without linking to the primary occurrence (hearsay without primary source).

### Provenance anchor is not actionable
- anchor is generic (“see article”, “in the report”) without page/section/timestamp/snippet.
- anchor points to a different location than the verbatim text.
- link is unstable without any stabilizer (e.g., no archived link/identifier when feasible).

## How to record uncertainty (without breaking requirements)
- Keep verbatim text exact; uncertainty belongs in separate notes/analysis fields, not inside the verbatim claim.
- If multiple editions/versions exist, specify the exact version in provenance_anchor (date, revision, commit, or archive URL).

## Quick pre-submit checklist
- [ ] Verbatim claim copied exactly (no paraphrase; qualifiers preserved).
- [ ] Speaker identified exactly as in source.
- [ ] Date captured (or “no date in source” explicitly justified in anchor).
- [ ] Source link provided and opens to the correct item.
- [ ] Provenance anchor pinpoints the claim (page/section/timestamp/snippet).
- [ ] If any item above is missing or weak → mark ABSTAIN / INVALID and request missing details.
