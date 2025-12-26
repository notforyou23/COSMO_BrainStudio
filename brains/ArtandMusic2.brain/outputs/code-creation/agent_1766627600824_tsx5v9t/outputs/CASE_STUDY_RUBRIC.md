# Case Study Rubric (Inclusion/Exclusion, Scoring, and Tagging)

**Purpose:** Standardize intake and evaluation of case studies so that selection is consistent, auditable, and aligned to the project taxonomy. This rubric is designed for a schema-driven workflow (shared templates + a single intake index) and emphasizes (1) impact, (2) thematic relevance, (3) authoritative media URLs, and (4) rights clarity.
## 1) Definitions

- **Case study:** A bounded, describable real-world instance (event, program, policy, product, decision, incident, dataset release, court case, investigation) with verifiable evidence and clear stakeholders.
- **Authoritative media URL:** A stable URL to a primary source or high-quality secondary source (e.g., official report, court record, academic paper, regulator filing, reputable newsroom investigation, institutional dataset page). Social posts are not authoritative unless they link to primary sources.
- **Rights clarity:** Documentation that indicates what can be used (license/permission) and any constraints (copyright, embargo, privacy, terms of use).
## 2) Inclusion Criteria (must meet all)

1. **Verifiability:** The narrative is supported by evidence (documents, reports, filings, peer-reviewed research, reputable investigative journalism, official statements, or reproducible data).
2. **Specificity:** Clear *who/what/when/where*; not purely speculative or generalized commentary.
3. **Material linkage to at least one project theme** (see Section 5) with an identifiable mechanism (e.g., measurement design, selection loop, incentive structure, allocation/triage, surveillance, ranking).
4. **Minimum sourcing bar:** At least **1 authoritative media URL** and at least **1 corroborating source** (can be the same type if independent, e.g., two independent reputable outlets).
5. **Ethics & safety:** Does not require publishing sensitive personal data; any sensitive elements are describable in aggregate or with redaction.
6. **Usability:** Sufficient detail to write a short abstract (3–6 sentences) and identify stakeholders, harms/benefits, and outcomes.
## 3) Exclusion Criteria (any triggers exclusion)

- **Unverifiable/rumor:** No evidence beyond hearsay, single anonymous post, or non-corroborated claim.
- **Not a case:** Pure opinion, generic trend summary, or an example with no bounded instance.
- **Irreducibly sensitive:** Publishing would materially increase risk (e.g., doxxing, identifiable minors, medical records) and cannot be safely summarized.
- **Rights-prohibited:** Clear restrictions that forbid use/republication for the project’s needs and no acceptable alternative sources.
- **Duplicate:** Substantively the same as an existing entry without meaningful new evidence or a distinct angle/mechanism.
## 4) Scoring Rubric (0–5 per dimension; weighted total = 100)

### 4.1 Dimensions and weights
- **Impact (40%)**: Magnitude and breadth of consequences; clarity of outcomes.
- **Relevance to Themes (30%)**: Directness and depth of linkage to project themes/mechanisms.
- **Authoritative Media URLs (20%)**: Availability, stability, and quality of primary/credible sources.
- **Rights Clarity (10%)**: Licensing/permission/terms clarity for included media and quoted materials.

### 4.2 Scoring anchors (0–5)
| Score | Impact (40%) | Relevance (30%) | Authoritative Media URLs (20%) | Rights Clarity (10%) |
|---:|---|---|---|---|
| 0 | No discernible real-world effect | No thematic link | No credible URLs | Unknown/unsafe; cannot assess |
| 1 | Minimal/local, short-lived | Tangential mention | One weak/unstable source | Vague; likely restricted |
| 2 | Limited but concrete; small population | Partial alignment; unclear mechanism | 1 authoritative OR 2 decent sources | Some info; constraints unclear |
| 3 | Moderate; clear stakeholders and outcomes | Clear link to a theme; mechanism identifiable | ≥2 authoritative or 1 primary + 1 strong secondary | ToS/license partly documented |
| 4 | High; multi-site/multi-stakeholder; policy/org change | Strong alignment; multiple thematic touchpoints | Primary documentation + multiple corroborations | Clear license/permission or fair-use rationale documented |
| 5 | Systemic; large-scale; enduring precedent/standard | Central exemplar of key mechanisms; teaches generalizable lessons | Primary sources (official/court/peer-reviewed) + strong investigations | Explicit reuse license/permission and privacy-compliant handling |

### 4.3 Weighted score calculation
Compute:
- impact_pts = (impact/5)*40
- relevance_pts = (relevance/5)*30
- media_pts = (media/5)*20
- rights_pts = (rights/5)*10
- **total = impact_pts + relevance_pts + media_pts + rights_pts**

**Decision guidance**
- **80–100:** Include (priority)
- **60–79:** Include (standard)
- **40–59:** Hold (needs better sources or clearer rights; revise)
- **0–39:** Exclude
## 5) Theme Alignment (what “relevance” means)

A case study should map to one or more of the following theme clusters and explicitly state the mechanism:

1. **Measurement design as an equity lever (and risk)**  
   - Mechanisms: proxy targets, test design, performance metrics, rubric/threshold choice, label bias, missingness, aggregation.
2. **Self-reinforcing selection loops**  
   - Mechanisms: ranking → access → outcomes → retraining/feedback; gatekeeping; “winner-take-more” dynamics.
3. **Institutional incentives and cheap signals**  
   - Mechanisms: cost-saving automation, compliance theater, reputational risk management, metric gaming.
4. **Allocation and triage under constraint**  
   - Mechanisms: resource allocation, eligibility screening, prioritization models, queueing, scoring systems.
5. **Accountability and governance**  
   - Mechanisms: audits, transparency, contestability, due process, documentation, procurement controls, impact assessments.

**Minimum relevance bar:** At least one theme + mechanism must be stated in the abstract and supported by evidence in sources.
## 6) Evidence & Source Requirements (media URLs)

### 6.1 Required URL set
For inclusion, provide:
- **Primary** (preferred): official report, court filing/judgment, regulator decision, peer-reviewed paper, dataset documentation, procurement docs.
- **Secondary** (required if primary unavailable): reputable newsroom investigation, established NGO report, academic working paper with methods.

### 6.2 Authoritativeness checklist (score media dimension)
- URL is stable (permalink, DOI, official PDF, archived page)
- Publisher credibility (court, agency, university, major outlet, NGO with methods)
- Date and authorship clear
- Cites underlying documents/data
- Not paywalled if avoidable (or provide an accessible alternative/archived copy)

### 6.3 Handling social media
Social links may be included **only** as pointers, never as sole evidence. They do not count toward the authoritative URL minimum unless they directly host the primary document (e.g., a government PDF) and are verifiable elsewhere.
## 7) Rights Clarity Rules

**Goal:** Ensure we can store links, quote short excerpts, and include media references without violating rights.

### 7.1 Acceptable rights evidence (any one sufficient to score ≥3)
- Explicit license (e.g., CC BY, CC BY-SA, public domain, Open Government License)
- Publisher terms allowing non-commercial quoting/linking with attribution
- Written permission (email or documented approval)
- Court documents/government publications where reuse is permitted (jurisdiction-dependent; document assumptions)

### 7.2 Rights red flags (cap rights score at 2 unless resolved)
- “All rights reserved” with explicit prohibition on reuse of text/media beyond linking
- Unclear provenance for images/video
- Personal data/privacy constraints not addressable by summarization
- Dataset terms that forbid redistribution of derived artifacts

### 7.3 Practical rule
If rights are unclear, default to **linking only** and quoting minimally (short excerpts with attribution) until clarified.
## 8) Tagging Rules (taxonomy-mapped)

### 8.1 Tag format and naming
- Tags are **lowercase snake_case**.
- Multi-word tags use underscores (e.g., `selection_loop`, `measurement_bias`).
- Use only approved categories below; add new tags only via a controlled taxonomy update.

### 8.2 Required tag categories (minimum set per case study)
1. **theme:** one or more  
2. **mechanism:** one or more  
3. **sector:** one primary  
4. **geography:** one primary (country/region)  
5. **population:** one or more (who is affected)  
6. **evidence_type:** one primary  
7. **media_type:** one or more  
8. **rights_status:** one primary

### 8.3 Approved taxonomy (v1)
**theme** (choose ≥1)
- `measurement_equity`
- `selection_loops`
- `institutional_incentives`
- `allocation_triage`
- `accountability_governance`

**mechanism** (choose ≥1)
- `proxy_metric`
- `thresholding`
- `ranking_scoring`
- `feedback_loop`
- `automation_bias`
- `metric_gaming`
- `data_missingness`
- `label_bias`
- `access_gatekeeping`
- `procurement_failure`
- `audit_failure`
- `due_process_gap`

**sector** (choose 1)
- `education`
- `employment`
- `health`
- `housing`
- `finance`
- `criminal_justice`
- `public_benefits`
- `immigration`
- `technology_platforms`
- `cross_sector`

**geography** (choose 1; ISO-like where possible)
- `us`, `uk`, `eu`, `ca`, `au`, `in`, `br`, `za`, `global`, `other`

**population** (choose ≥1)
- `students`
- `job_seekers`
- `patients`
- `tenants`
- `borrowers`
- `defendants`
- `benefit_applicants`
- `migrants`
- `workers`
- `general_public`

**evidence_type** (choose 1)
- `court_record`
- `regulatory_action`
- `official_report`
- `peer_reviewed_research`
- `investigative_journalism`
- `ngo_report`
- `dataset_documentation`
- `first_person_account` (allowed only with corroboration)

**media_type** (choose ≥1)
- `pdf_report`
- `web_article`
- `dataset_portal`
- `court_opinion`
- `video`
- `audio`
- `code_repository`

**rights_status** (choose 1)
- `public_domain`
- `open_license`
- `permission_granted`
- `fair_use_quote_only`
- `link_only_unclear`
- `restricted_no_use`

### 8.4 Tagging decision rules
- Every case must have **at least 8 tags**: 1 sector + 1 geography + 1 evidence_type + 1 rights_status + (≥1 theme, ≥1 mechanism, ≥1 population, ≥1 media_type).
- If multiple sectors apply, pick the primary and add `cross_sector` only when no single sector is clearly primary.
- Prefer the most specific mechanism tags; avoid tagging both broad and narrow unless both are meaningfully present (e.g., `ranking_scoring` + `feedback_loop`).
- Rights status must reflect the **most restrictive** material referenced (e.g., if images are restricted but text is open, use `fair_use_quote_only` or `link_only_unclear`).

### 8.5 Worked tagging example (template)
- theme: `measurement_equity`, `selection_loops`
- mechanism: `proxy_metric`, `feedback_loop`
- sector: `education`
- geography: `us`
- population: `students`
- evidence_type: `official_report`
- media_type: `pdf_report`, `web_article`
- rights_status: `fair_use_quote_only`
## 9) Intake Quality Gates (recommended workflow)

1. **Intake completeness:** title, date range, geography, sector, 2–6 sentence abstract, stakeholders, outcomes, and minimum URLs.
2. **Rubric scoring:** score all four dimensions; compute weighted total; record decision.
3. **Tagging:** apply required tags per Section 8; validate naming (snake_case) and category compliance.
4. **Publication readiness:** confirm sensitive details are summarized safely; ensure rights status is correct; link to authoritative sources.

**Recordkeeping:** Store the score breakdown, decision, and tag set alongside the case study entry so selection can be audited later.
