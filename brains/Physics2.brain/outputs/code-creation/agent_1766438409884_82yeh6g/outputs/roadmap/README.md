# Roadmap Deliverables Index (12-page pack)

This folder is the authoritative index for the **planned 12-page roadmap deliverable**. Each “page” below is a standalone Markdown file (one file per page) intended to be assembled into a single roadmap packet (PDF/slide-deck conversion optional).

## Where each page file belongs

Create the following files under:

- `outputs/roadmap/pages/` (recommended location for page markdown files)
- Keep filenames stable; use version control history for iteration.

| Page | File path (planned) | Title | What it contains (scope) |
|---:|---|---|---|
| 1 | `outputs/roadmap/pages/01-executive-summary.md` | Executive Summary | One-page narrative: goals, outcomes, timeline headline, and ask/decision. |
| 2 | `outputs/roadmap/pages/02-context-and-problem.md` | Context & Problem | Current state, pain points, constraints, and why now; problem statement. |
| 3 | `outputs/roadmap/pages/03-vision-and-principles.md` | Vision & Principles | Target vision, guiding principles, non-goals, and success definition. |
| 4 | `outputs/roadmap/pages/04-scope-and-assumptions.md` | Scope & Assumptions | In-scope / out-of-scope, dependencies, key assumptions, and constraints. |
| 5 | `outputs/roadmap/pages/05-user-and-stakeholders.md` | Users & Stakeholders | Personas, stakeholders, needs map, and prioritization of audiences. |
| 6 | `outputs/roadmap/pages/06-objectives-and-kpis.md` | Objectives & KPIs | Measurable objectives, KPI tree, baseline/targets, measurement approach. |
| 7 | `outputs/roadmap/pages/07-initiatives-portfolio.md` | Initiative Portfolio | Initiative list, value hypothesis, effort sizing, and prioritization rationale. |
| 8 | `outputs/roadmap/pages/08-timeline-and-milestones.md` | Timeline & Milestones | Quarter-by-quarter (or sprint/phase) plan, milestone dates, releases. |
| 9 | `outputs/roadmap/pages/09-resourcing-and-budget.md` | Resourcing & Budget | Roles/teams, capacity plan, budget ranges, build/buy decisions. |
| 10 | `outputs/roadmap/pages/10-risks-and-mitigations.md` | Risks & Mitigations | Top risks, probability/impact, mitigations, owners, and triggers. |
| 11 | `outputs/roadmap/pages/11-governance-and-operating-model.md` | Governance & Operating Model | Decision cadence, RACI, intake/change control, reporting, comms plan. |
| 12 | `outputs/roadmap/pages/12-appendix.md` | Appendix | Glossary, references, assumptions log, sizing notes, and supporting tables. |

## Assembly conventions (for consistent page-to-pack flow)

- Each page file should start with an H1 matching the **Title** column above.
- Keep “page” content concise (aim: 350–700 words equivalent per file).
- Prefer tables/bullets for comparability (KPIs, initiatives, risks, milestones).
- Use relative links when referencing other pages, e.g. `./pages/07-initiatives-portfolio.md`.

## Versioning notes

- Treat this folder as the distribution-ready artifact source for roadmap documentation.
- When the outline changes, update this index first, then adjust the `pages/*` set to match.
