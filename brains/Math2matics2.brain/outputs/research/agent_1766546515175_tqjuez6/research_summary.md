# Research Summary

**Agent:** agent_1766546515175_tqjuez6
**Mission:** QA found borderline confidence - research agent should verify claims
**Completed:** 2025-12-24T03:23:09.503Z

## Summary

The research converges on a practical verification playbook: trace any scientific or statistical claim back to its primary source, validate what was actually measured and reported (methods/results alignment, effect sizes, uncertainty), and then run integrity checks (corrections/retractions) plus triangulation (replications, critiques, re-analyses). This emphasizes that “what the claim says” is less important than “what the original study/data actually did,” and that reliability improves when evidence is transparent (shared data/code) and independently corroborated.

For quantitative fact-checking, the most actionable approach is to use the original producer of the statistic (e.g., World Bank/IMF/OECD for global macro; Census/BLS for U.S.) and then corroborate through reputable aggregators that preserve metadata (e.g., Our World in Data; FRED/ALFRED for U.S. time series and vintages). For AI/LLM confidence, the research distinguishes between raw uncertainty signals (e.g., token logprobs/entropy) and whether those signals are calibrated, recommending calibration audits and modern uncertainty quantification methods (notably conformal prediction) to produce decision-grade confidence/coverage guarantees.

## Key Findings

1. Primary-source verification: To verify a scientific claim, locate and read the original research output (journal article/preprint/registry/dataset), prioritize the Methods section to assess design, outcomes, and analysis plan, then confirm the Results match prespecified outcomes and report effect sizes with uncertainty (e.g., confidence intervals).

2. Integrity checks are mandatory: Before treating a claim as reliable, check for linked corrections, expressions of concern, or retractions; publication-status signals can materially change whether results should be trusted and are part of standard scholarly record-keeping guidance (e.g., COPE/ICMJE norms).

3. Triangulation improves confidence: Search for independent replications, re-analyses, and later citing literature (including critiques), and prefer studies with transparent practices such as shared data/code or clearly documented investigative outcomes.

4. Statistical fact-checking databases: For macro/development indicators, start with World Bank Open Data (WDI), IMF Data/WEO, and OECD Data; corroborate with Our World in Data for quick sanity checks and reproducible charts, while confirming definitions/metadata (rates vs counts; nominal vs real; PPP vs FX).

5. AI confidence should be calibrated: Token logprobs (and derived measures like entropy or margin) can provide usable uncertainty signals for LLM outputs, but teams should evaluate calibration and groundedness; conformal prediction (e.g., via MAPIE) and calibration tooling (e.g., Uncertainty Toolbox, Venn–Abers) support actionable uncertainty estimates and coverage guarantees.

## Research Queries

1. How to verify scientific claims using primary sources
2. Best databases for fact-checking statistical claims 2024-2025
3. Tools and methods for assessing AI model confidence

## Sources

Total sources consulted: 83

See `bibliography.bib` for citation-ready BibTeX entries.
