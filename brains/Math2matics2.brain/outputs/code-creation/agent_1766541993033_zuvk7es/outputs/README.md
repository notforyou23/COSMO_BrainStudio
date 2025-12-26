# /outputs

This directory contains **generated, versioned artifacts** produced by the project’s pipeline and agents. Keeping them under `/outputs` makes deliverables easy to audit: if this folder is empty, the project has produced no concrete artifacts.

## What belongs here

Artifacts in `/outputs` should be:
- **Human-readable** (typically Markdown) unless a binary is required.
- **Versioned by filename** (e.g., `*_v1.md`, `*_v2.md`) to preserve history without overwriting prior work.
- **Auditable**: the presence of files in this directory is itself evidence of progress.

Common artifact types:
- Roadmaps and delivery plans (e.g., `roadmap_v1.md`)
- Status snapshots / run reports (e.g., `run_report_YYYY-MM-DD.md`)
- Decision logs or design notes (e.g., `decisions_v1.md`)
- Evaluation summaries and consistency reviews

## How to validate deliverables exist

### Quick check (shell)
From the repository root:
```bash
ls -la outputs/
```

### Programmatic check (Python)
```python
from pathlib import Path

out_dir = Path("outputs")
files = sorted(p.name for p in out_dir.glob("*") if p.is_file())
assert files, "No deliverables found in outputs/"
print("outputs/ contains:", files)
```

### Repository audit expectation
A minimal “non-zero deliverables” state is reached when:
- `outputs/README.md` exists (this file), and
- at least one additional artifact exists (for example, `outputs/roadmap_v1.md`).

## Naming conventions

- Use lowercase with underscores: `artifact_name_vN.md`
- Prefer explicit versions over overwriting.
- Include dates in reports when useful: `report_2025-12-24.md`

## Notes

Artifacts here should be safe to commit to version control. If an artifact is large or generated frequently, consider summarizing it in Markdown and storing raw data elsewhere (or excluding it via `.gitignore` if appropriate).
