# Bibliography

Curated sources (external references and internal project artifacts) consulted or cited by this project and its agents. Entries include a short note describing how the source is used.
## External references

1. **Keep a Changelog** — https://keepachangelog.com/en/1.1.0/  
   **Use:** Conventions for maintaining human-readable changelogs; informs update cadence guidance in `/outputs/` artifacts.

2. **Semantic Versioning 2.0.0** — https://semver.org/  
   **Use:** Versioning scheme reference for deterministic artifact revisions (when applicable).

3. **GitHub Actions Documentation** — https://docs.github.com/actions  
   **Use:** CI/CD primitives (workflows, jobs, caching, artifacts) referenced when defining checks that validate `/outputs/` consistency.

4. **GitHub: `actions/cache`** — https://github.com/actions/cache  
   **Use:** Canonical caching action details for deterministic and faster CI runs.

5. **Python 3 `pathlib` module** — https://docs.python.org/3/library/pathlib.html  
   **Use:** Path-safe, cross-platform filesystem operations used by the generator scripts.

6. **Python 3 `json` module** — https://docs.python.org/3/library/json.html  
   **Use:** Stable serialization used for directory state reporting and deterministic outputs.

7. **CommonMark Specification** — https://spec.commonmark.org/  
   **Use:** Baseline Markdown behavior assumptions for portability of generated `.md` artifacts across renderers.

8. **The Twelve-Factor App (Build, release, run; Dev/prod parity)** — https://12factor.net/  
   **Use:** General guidance for reproducible builds and environment parity in CI/CD pipelines.
## Internal project sources (local artifacts)

1. **[AGENT] agent_1766538161484_b5yh91f — Cycle 1 consistency review (divergence 0.97)**  
   **Use:** Early consistency assessment referenced when standardizing artifact structure and terminology.

2. **[AGENT] agent_1766538470010_nvdr7ld — Cycle 4 consistency review (divergence 0.96)**  
   **Use:** Later consistency assessment used to validate that artifact conventions remain compatible across branches.

3. **[AGENT INSIGHT] agent_1766540049061_an5rb16 — “Computational execution plan”**  
   **Use:** Guidance for deterministic `/outputs/` artifact generation and update cadence.

4. **[INTROSPECTION] `2025-12-24T01-29-38-707Z_scripts_run_pipeline_py_stage1_attempt1_prompt.txt`**  
   **Use:** Record of prompt/intent that informs the required initial artifacts (roadmap, bibliography, coverage matrix) and deterministic generation constraints.

5. **[CONSOLIDATED] Reproducible workflow note (coverage matrix, cadence, stable artifacts)**  
   **Use:** Consolidated requirements shaping the `/outputs/README.md` conventions and the initial pipeline artifact set.
## Citation and link-handling notes

- **Link stability:** External URLs are recorded at the most canonical landing page available; when versioned docs exist (e.g., SemVer, Keep a Changelog), the versioned URL is preferred.
- **Determinism:** This bibliography is intended to be append-only within a cycle; ordering is stable and human-auditable.
- **Scope:** Internal sources are listed to preserve provenance even when they are not publicly accessible; they are treated as project-local citations.
