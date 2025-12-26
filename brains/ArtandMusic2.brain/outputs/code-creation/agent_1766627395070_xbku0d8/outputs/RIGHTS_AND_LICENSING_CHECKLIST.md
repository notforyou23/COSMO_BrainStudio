# Rights & Licensing Checklist (Required for Case Study Exemplars)

This checklist must be completed for **every exemplar entry** (image, figure, chart, table, dataset, quote excerpt, screenshot, audio/video clip, brand mark, UI capture, or other third‑party material) referenced in any case study. An exemplar **may not** be used in a case study unless it has a **complete** corresponding row in `outputs/RIGHTS_LOG.csv` with all required fields populated.

## What counts as an “exemplar”
An exemplar is any non-original material included in, embedded in, linked from, or used to create a derivative in a case study, including:
- Items reproduced in full (e.g., images, charts, tables, screenshots, code snippets beyond fair use thresholds).
- Items used as inputs to analysis, redrawing, translation, or summarization where the original is identifiable.
- Items where a case study cites a URL as an example, even if not reproduced inline.

## Required rights log fields (must match `outputs/RIGHTS_LOG.csv`)
Each exemplar must have exactly one rights log entry with all fields completed:

1) **URL**
- The canonical source URL for the exemplar (or most authoritative landing page).
- If no public URL exists, use an internal reference URL or persistent identifier (e.g., DOI/handle) plus a stable archive link if available.

2) **license type**
- The specific license or legal basis for use, written precisely (examples: “CC BY 4.0”, “CC BY-SA 3.0”, “Public Domain (CC0)”, “All Rights Reserved (permission granted)”, “Fair Use (commentary/criticism)”, “Licensed via stock provider”, “Government work (jurisdiction-specific)”, “Open Data License (ODC-BY 1.0)”).
- Do not write vague values like “open” or “free”.

3) **rights holder**
- The individual/organization that owns or controls rights (creator, publisher, agency, platform account, etc.).
- If unclear, document the best-evidence rights holder (e.g., “Publisher X (per copyright notice on page)”).

4) **permission status**
- The concrete permission state for this exemplar (examples: “Not required (public domain)”, “Complies with license terms”, “Permission requested”, “Permission granted”, “Permission denied”, “Fair use rationale documented”, “Replace/remove required”).
- Must reflect current state and be consistent with the allowed uses below.

5) **allowed uses**
- The permitted scope of use for this project, stated clearly (examples: “Reproduce in case study PDF and website with attribution”, “Use only as a link; no reproduction”, “Use for internal review only”, “Use excerpt ≤200 words with citation”, “Create redraw/derivative; do not redistribute original asset”).
- Include any constraints: attribution wording, non-commercial limits, share-alike obligations, no-derivatives restrictions, geographic limits, time limits, revocability, or platform TOS constraints.

## Minimum evidence to record (must be verifiable)
For every exemplar, ensure the case study team can show evidence supporting the rights log entry:
- A visible license statement on the source page, the asset page, or an attached license file; OR
- A copy of the permission grant (email, letter, ticket, contract); OR
- A documented fair use analysis (purpose, amount, market effect, transformativity) sufficient for internal review.

## Review steps (must be completed before publication)
1) **Identify every exemplar**
- Scan the case study for: URLs, citations, embedded media, figures, tables, screenshots, brand marks, and appendices.
- Treat each distinct asset as a separate exemplar entry unless one license explicitly covers a clearly defined collection.

2) **Confirm source authenticity**
- Prefer primary sources. If using reposts, locate the original publisher/creator and log that canonical URL.

3) **Determine license type accurately**
- Record the exact license identifier and version when applicable (e.g., “CC BY 4.0” not “Creative Commons”).
- If the asset is under “All Rights Reserved,” do not assume permission.

4) **Confirm rights holder**
- Validate via copyright notice, publisher information, author attribution, or official registry.

5) **Check license obligations and restrictions**
- Attribution requirements (name, title, source link, license link, modification notice).
- Non-commercial (NC) limitations and whether project distribution qualifies.
- No-derivatives (ND) constraints (no cropping/redrawing/compositing if prohibited).
- Share-alike (SA) obligations and whether downstream outputs must be similarly licensed.
- Database/data licenses may differ from webpage content; confirm the correct layer.

6) **Set permission status**
- If permission is required, ensure it is requested and tracked; do not publish until “granted” (or asset is replaced/removed).
- If relying on fair use, ensure rationale is documented and the use is limited to what is necessary.

7) **Define allowed uses for this project**
- State exactly where the exemplar may appear (case study text, figures, slides, marketing page).
- Note whether modification is allowed (cropping, annotation, redrawing).
- Note whether redistribution is allowed (downloadable assets, repo inclusion).

8) **Record the entry in `outputs/RIGHTS_LOG.csv`**
- All five required fields must be non-empty.
- Ensure the URL matches what appears in the case study (or that the case study uses the canonical URL recorded).

9) **Publication gate**
- A case study may ship only if **every exemplar URL found** in the case study has a **complete** rights log row with acceptable permission status and allowed uses.

## Decision rules (common cases)
- **Public domain / CC0:** Allowed with citation; still record rights holder/source and allowed uses.
- **Creative Commons:** Allowed only if the planned use complies with the exact terms (BY/SA/NC/ND); record attribution and modification notes in allowed uses.
- **All Rights Reserved:** Require explicit permission unless a well-documented fair use basis applies; otherwise replace/remove.
- **Screenshots / UI / brand marks:** Often restricted by trademark/TOS; treat as All Rights Reserved unless a clear policy grants reuse; record constraints.
- **Datasets:** Confirm dataset license (not just the website’s); note redistribution rights and required notices.
- **AI-generated or composite outputs:** If any third-party exemplar is used as input or reference with identifiable content, it must be logged; also ensure model/provider terms allow the intended use.

## Completion standard (non-negotiable)
For each exemplar referenced in a case study:
- A corresponding row exists in `outputs/RIGHTS_LOG.csv`.
- The row has **URL, license type, rights holder, permission status, allowed uses** all populated.
- The permission status and allowed uses explicitly permit the exemplar’s appearance in the published case study.

If any exemplar fails this standard, the exemplar must be removed, replaced with a compliant alternative, or publication must be delayed until compliance is achieved.
