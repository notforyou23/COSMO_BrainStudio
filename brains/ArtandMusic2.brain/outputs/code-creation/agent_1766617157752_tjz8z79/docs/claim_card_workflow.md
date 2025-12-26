# Claim Card Workflow (Pilot Case Study)

This project uses **claim cards** to keep empirical statements traceable, verifiable, and auditable. Any *new empirical claim* introduced in the pilot case study must be backed by a claim card.

## Key concepts

- **Empirical claim**: A statement about the world that could be true or false (measurements, effect sizes, prevalence, causal impacts, historical facts, observed outcomes).
- **Claim card**: A standalone record (one file per claim) that captures the claim, scope, evidence type, citations, verification status, and abstention triggers.
- **Verification status**: The project’s current confidence level in the claim based on reviewed evidence (not the claim’s “importance”).
- **Abstention triggers**: Conditions under which the case study must avoid asserting the claim (or must qualify it) because evidence is weak, out of scope, or non-transferable.

## When you must create a claim card

Create (and reference) a claim card whenever the pilot case study:
1. Introduces a **new empirical claim** not already covered by an existing claim card.
2. Changes the **scope** of a previously claimed fact (different population, time window, geography, or intervention).
3. Reuses a claim in a way that implies **stronger certainty** than its current verification status supports.
4. Uses a quantitative value (rates, percentages, effect sizes) or a comparative statement (“higher than”, “reduces”, “increases”) that is not purely definitional.

Non-empirical content (definitions, normative arguments, design goals, hypotheses clearly labeled as hypotheses) does not require claim cards.

## File locations and naming

- Case study template: `templates/CASE_STUDY_TEMPLATE.md`
- Claim card template: `templates/CLAIM_CARD_TEMPLATE.md`
- Claim card files should live under a dedicated folder (recommended): `claims/`
- Use stable IDs. Recommended filename pattern:
  - `claims/CC-YYYY-NNN_short_slug.md` (example: `claims/CC-2025-001_selection_loop.md`)
- The **claim card ID** (e.g., `CC-2025-001`) is what the case study cites.

## How to write a claim card (required fields)

Use `templates/CLAIM_CARD_TEMPLATE.md` and fill in all fields:

- **Claim text**: One sentence; concrete and falsifiable.
- **Scope**: Population, setting, time window, geography, definitions/operationalization notes, and any boundary conditions.
- **Evidence type**: Select the best match for the strongest supporting evidence (e.g., RCT, quasi-experimental, observational, qualitative, meta-analysis/systematic review, benchmark/test, administrative data, expert consensus).
- **Citations/DOIs/URLs**: Provide at least one resolvable reference when evidence exists. Prefer DOI; otherwise stable URLs. Include page/figure/table pointers where applicable.
- **Verification status**: One of:
  - `unverified`: not yet checked against sources, or evidence missing/unclear.
  - `partially_verified`: some sources reviewed, but gaps remain (scope mismatch, mixed results, limited quality, or incomplete extraction).
  - `verified`: sources reviewed and extracted; claim text matches evidence *within the stated scope*.
- **Abstention triggers**: Explicitly list when to avoid asserting the claim or when it must be qualified.

## Referencing claim cards from the pilot case study

Every empirical claim in the pilot case study must be linked inline to a claim card ID. Recommended citation styles:

- Parenthetical: `(Claim card: CC-2025-001)`
- Footnote: `[^cc-2025-001]` where the footnote contains `Claim card: CC-2025-001`

Rules:
1. If a paragraph contains multiple distinct empirical claims, each claim must have its own claim card ID.
2. If a single claim is used repeatedly, reuse the same claim card ID (do not duplicate cards unless scope changes).
3. Do not cite a paper directly in the case study for an empirical claim unless it is also captured in a claim card; the claim card is the unit of accountability.

## Using verification status in writing

The case study must phrase claims in line with their verification status:

- `unverified`: do not assert as fact. Use conditional language and explicitly flag uncertainty.
  - Example: “Some reports suggest X (Claim card: CC-2025-001; unverified).”
- `partially_verified`: may state cautiously with qualifiers and scope limits; avoid strong causal wording unless supported.
  - Example: “Evidence indicates X in Y setting, though results are mixed (Claim card: CC-2025-002).”
- `verified`: may be stated as fact *within scope*; still include scope constraints when relevant.
  - Example: “In Z population during 2010–2020, X increased by ~N% (Claim card: CC-2025-003).”

Do not “upgrade” language in the case study beyond the claim card’s status. If the writing needs stronger wording, update the claim card first by adding evidence and revising status.

## Abstention triggers: how they control narrative

Abstention triggers are enforcement hooks that prevent overreach. The case study must:
- Avoid asserting the claim when any abstention trigger applies.
- Add a qualifier or scope restriction when triggers indicate partial transferability.
- Prefer abstention over speculation when evidence is thin.

Examples of abstention triggers (adapt to the claim):
- Evidence is outside the target population (e.g., adult data used for children).
- Outcome definition differs (proxy vs direct measurement).
- Confounding not addressed in observational studies when causal language is used.
- Single-source claim with no corroboration.
- Effect size depends on a context not present in the pilot setting (institutional regime, incentive structure).
- Source is non-peer-reviewed or inaccessible.

## Minimal quality bar for a “verified” claim

A claim may be marked `verified` only when:
1. The claim text matches the cited source(s) (numbers, directionality, and causal framing).
2. The scope in the claim card matches the source scope (or the claim is narrowed to match).
3. Citations include enough detail to locate the evidence (DOI/URL + where in the source).
4. Any material limitations are captured as abstention triggers.

## Workflow checklist (authoring)

1. Draft the case study section.
2. Identify each empirical claim.
3. For each claim:
   - Find an existing claim card ID, or create a new claim card from the template.
   - Set verification status conservatively.
   - Add abstention triggers that prevent misuse.
4. Insert claim card IDs next to every empirical claim in the case study.
5. Before finalizing: scan for any “naked facts” (empirical statements without a claim card ID) and fix them.
