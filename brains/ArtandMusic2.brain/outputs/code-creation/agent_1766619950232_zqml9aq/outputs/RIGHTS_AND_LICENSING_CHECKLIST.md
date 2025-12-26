# Rights & Licensing Checklist (Outputs)

Purpose: verify permissions, attribution, and licensing requirements for any third-party assets referenced in `/outputs`.

**Recordkeeping:** Log every third-party asset in `outputs/RIGHTS_LOG.csv` (one row per asset). This checklist is complete only when every referenced asset has a corresponding log entry and the evidence is stored or linked.

## 1) Scope: What counts as a “third-party asset”
Check all that apply (if yes, log it):
- Images, illustrations, icons, screenshots, figures, charts (even if edited).
- Tables, datasets, excerpts, quotes beyond fair-use comfort.
- Audio/video clips, transcripts, still frames.
- Code snippets copied/adapted from external sources.
- Brand assets (logos, trademarks), product UI screenshots.
- AI-generated content **trained on / prompted with** third-party material (log both the model/tool license + any included third-party inputs/outputs if applicable).

## 2) For each asset: required fields (must be in RIGHTS_LOG.csv)
Confirm each logged asset includes:
- Asset ID (stable), title/description, file/path or URL, where used (report section/page).
- Source/author/owner (person/org) and source URL.
- License type + license URL/text (e.g., CC BY 4.0, CC0, MIT, proprietary, “permission granted”).
- Usage rights: allowed uses (commercial? derivative? redistribution?), territory, term/expiration.
- Attribution requirements (exact wording if specified).
- Modifications made (cropped, recolored, translated, redrawn, summarized, etc.).
- Evidence link/location (email, invoice, terms screenshot, repository LICENSE, written permission).
- Reviewer + date verified.

## 3) License/permission verification steps
For each asset, verify and note in the log:
1. **Identify the rights holder** (uploader may not be owner).
2. **Read the actual license** (not just a badge); store a link or copy.
3. **Confirm compatibility with intended use**:
   - Distribution: internal only vs public release.
   - Commercial/non-commercial constraints.
   - Derivatives allowed? (NoDerivatives blocks edits and many adaptations.)
   - Share-alike obligations (may “infect” the combined work if not separable).
4. **Check sublicensing/redistribution rules** (can you include the asset in this repo/package?).
5. **Check attribution format** (where it must appear; hyperlink requirements).
6. **Check moral rights/privacy/publicity** where applicable (people’s likeness, private property).
7. **Confirm no additional restrictions** (terms of service, paywalled content, “editorial use only”).

## 4) Common asset types: special checks
### Images / screenshots
- If screenshot includes UI, trademarks, or copyrighted content: confirm permitted use and context (commentary/analysis vs promotional).
- If faces/identifiable persons: confirm model release or lawful basis; avoid minors without explicit consent.
- For maps: verify map tile/provider terms (many prohibit reproduction without attribution or require specific credits).

### Datasets
- Verify dataset license and whether it allows redistribution/derivatives.
- Check privacy/PII: ensure anonymization and lawful basis; document any aggregations.
- Confirm citation requirements.

### Quotes and excerpts
- Prefer short excerpts; include citation (author, title, publication, date, URL/DOI).
- If substantial excerpting, obtain permission and log it.

### Code snippets
- Record license (MIT/Apache/GPL/etc.) and attribution/notice requirements.
- Ensure any copyleft obligations are acceptable for this project’s distribution.

## 5) Attribution block requirements (when applicable)
Before release, ensure:
- Every asset requiring credit has a visible attribution near the asset or in a dedicated acknowledgements section.
- Attribution includes: Author/Owner, Title, Source link, License (and link), and modification note if required.
- The project-level acknowledgements references `outputs/RIGHTS_LOG.csv` as the authoritative inventory.

Suggested attribution format:
“Title” by Author (Source URL), licensed under License (License URL). Modified: yes/no.

## 6) Final pre-publication gate (must all be true)
- All third-party assets used in `/outputs` are logged in `outputs/RIGHTS_LOG.csv`.
- Evidence for each asset is available (link or stored artifact) and review date is current.
- No asset has unknown license/owner.
- Any restricted assets (NC/ND/editorial-only) are either removed, replaced, or cleared for the intended release.
- All required attributions are present and accurate.
- Any share-alike/copyright notice requirements are satisfied in the distributed materials.

## 7) Escalation / remediation
If any check fails:
- Replace with original work or public-domain/compatible-licensed alternative; or
- Obtain written permission specifying scope (use, term, territory, distribution); or
- Remove the asset and update outputs accordingly; then update `RIGHTS_LOG.csv` to reflect the change.

## 8) Where this checklist is referenced
- Inventory and evidence tracking: `outputs/RIGHTS_LOG.csv`
- Related scaffold artifacts (for consistency of citations/metadata across outputs):
  - `outputs/REPORT_OUTLINE.md`
  - `outputs/CASE_STUDY_TEMPLATE.md`
  - `outputs/METADATA_SCHEMA.json` (or equivalent schema file)
