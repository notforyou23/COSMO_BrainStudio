# Evaluation Loop (5-cycle cadence)

Purpose: Maintain a continuously improving Mathematics content set by reviewing coverage, connectivity, and quality on a fixed cadence and making explicit produce/retire decisions.

## Definitions

- **Domain**: Top-level Mathematics area (e.g., Algebra, Geometry).
- **Subtopic**: A specific skill/concept within a domain (e.g., quadratic factoring).
- **Artifact**: A tracked instructional/assessment unit (e.g., lesson note, worked example, quiz).
- **Cross-link**: A documented dependency/reference from one artifact to another (prerequisite, extension, alternative method, related proof).
- **Coverage gap**: A domain–subtopic row in the coverage matrix lacking required artifacts or having weak connectivity/quality.

## Cadence overview (repeat every cycle)

Each cycle is one review pass of all domains, executed in five sequential phases. The phases are designed so that every cycle ends with an actionable backlog and a commit to produce/retire items next cycle.

1. **Inventory & snapshot (Day 1)**
2. **Coverage audit (Day 2)**
3. **Connectivity audit (Day 3)**
4. **Quality sampling (Day 4)**
5. **Decision & planning (Day 5)**

## Metrics to record (every cycle)

Record these metrics once per cycle (global + per domain). The intent is to make drift and progress visible.

### A. Artifact counts

- `artifact_count_total`
- `artifact_count_by_type` (e.g., note/example/problemset/quiz/proof/worksheet)
- `artifact_count_by_domain`
- `artifact_count_by_domain_subtopic` (optional if the matrix is granular)

### B. Cross-link metrics

- `crosslinks_total` (sum of all links)
- `crosslinks_per_artifact_avg` = crosslinks_total / artifact_count_total
- `crosslinks_bidirectional_rate` = (# pairs with A↔B) / (# linked pairs)
- `isolated_artifacts_count` = artifacts with 0 cross-links
- `orphan_subtopics_count` = subtopics whose artifacts have < 2 inbound/outbound links combined

### C. Coverage gap metrics

- `subtopics_total`
- `subtopics_covered` (meeting minimum artifact requirements below)
- `coverage_rate` = subtopics_covered / subtopics_total
- `gap_count` = subtopics_total - subtopics_covered
- `gaps_by_domain` (ranked list)

### D. Quality sampling metrics (lightweight)

Sample at least 10% of artifacts per domain (minimum 3). Record:
- `sample_size`
- `clarity_score_avg` (1–5)
- `correctness_issues_count`
- `notation_consistency_issues_count`
- `difficulty_alignment_issues_count`

## Minimum coverage requirements (to mark a subtopic "covered")

A subtopic is considered **covered** when it has, at minimum:
- 1 **concept/lesson note** (definition, properties, common pitfalls)
- 1 **worked example** (step-by-step)
- 1 **practice set** (>= 5 problems or equivalent)
- 1 **assessment item** (quiz question or check-for-understanding)

Plus connectivity:
- At least 1 prerequisite cross-link (inbound) and 1 extension/related cross-link (outbound), unless the subtopic is explicitly tagged as foundational or terminal.

## Cycle phases (what to do and what to write down)

### Phase 1 — Inventory & snapshot (Day 1)

Actions:
- Export current coverage matrix snapshot (domains, subtopics, artifact types, status).
- Enumerate artifacts and their metadata (domain, subtopic, type, difficulty, last_updated).
- Extract cross-links graph (edges list).

Outputs:
- Cycle header in the review log (date, commit hash/version if applicable).
- Metrics section populated for A and B (counts + cross-links).

### Phase 2 — Coverage audit (Day 2)

Actions:
- For each domain, compute coverage per subtopic against the minimum requirements.
- Identify missing artifact types and missing subtopic rows.
- Confirm that each domain has at least one example row fully populated (guard against empty domains).

Outputs:
- Metrics section populated for C (coverage + gaps).
- Ranked gap list: top 10 missing/weak subtopics per domain.

### Phase 3 — Connectivity audit (Day 3)

Actions:
- Flag isolated artifacts and orphan subtopics.
- Check for link hygiene: broken links, duplicate links, circular prereq chains.
- Ensure each domain has at least one cross-domain link where appropriate (e.g., Algebra ↔ Functions).

Outputs:
- Updated B metrics (isolated/orphan counts, bidirectional rate).
- A short "connectivity fixes" list (add/remove links).

### Phase 4 — Quality sampling (Day 4)

Actions:
- Randomly sample artifacts per domain (>=10% or min 3).
- Evaluate clarity, correctness, notation, and difficulty alignment using a simple rubric.
- Triage issues into: critical (blocks usage), major (misleading), minor (style).

Outputs:
- Metrics section populated for D.
- Issue list with severity and recommended action (patch, rewrite, retire).

### Phase 5 — Decision & planning (Day 5)

Actions:
- Apply decision rules (below).
- Produce next-cycle backlog with owners and expected artifact types.
- Retire or merge redundant artifacts; update cross-links accordingly.

Outputs:
- "Decisions" table: Produce / Patch / Retire / Merge / Defer.
- Next-cycle backlog (ordered by expected learning impact).

## Decision rules (produce / patch / retire)

Apply in this order; stop when a rule triggers.

### 1) Produce (create new artifacts) when any are true

- A subtopic fails minimum coverage requirements (missing any required type).
- `coverage_rate` < 0.90 globally or < 0.85 for any domain.
- A high-prerequisite subtopic (many inbound links) has `clarity_score_avg` < 3.5.
- A domain has `orphan_subtopics_count` > 10% of its subtopics.

**What to produce next (priority order):**
1. Fill missing required types for the largest prerequisite hubs.
2. Create bridging artifacts that connect domains (reduce isolation).
3. Add assessments for subtopics with high practice usage.

### 2) Patch (edit existing artifacts) when any are true

- Any correctness issue is found in sampling (`correctness_issues_count` > 0).
- Notation inconsistency repeats across artifacts in a domain (>= 3 occurrences).
- Difficulty alignment issues exceed 20% of sampled artifacts.

Patch SLA:
- Critical: fix within the same cycle before next release.
- Major: fix within 1 cycle.
- Minor: batch within 2 cycles.

### 3) Retire (remove or archive) when any are true

- Artifact is redundant (>= 80% overlap with a better artifact) AND has low linkage (<= 1 cross-link).
- Artifact has recurring correctness issues (>= 2 cycles) and a rewrite is cheaper than patching.
- Artifact is unreferenced for 2 consecutive cycles (no inbound links and not a root/foundational item).

Retirement procedure:
- Replace inbound links to the best remaining artifact.
- Mark as archived with a retirement reason and date (do not silently delete if history matters).

### 4) Merge (consolidate) when any are true

- Two artifacts serve the same subtopic and type but differ only stylistically.
- Cross-link graph shows a tight cluster where one canonical artifact would reduce confusion.

### 5) Defer (explicitly postpone) only when all are true

- The gap is in a low-traffic subtopic (few inbound links) AND
- Quality scores are stable AND
- There is a clear, dated rationale (e.g., awaiting upstream prerequisites rewrite).

## End-of-cycle checklist

A cycle is "complete" only if:
- All metrics (A–D) are recorded.
- A ranked gap list exists per domain.
- At least one action is taken: produce/patch/retire/merge.
- The next-cycle backlog is written with a top-5 priority list.
