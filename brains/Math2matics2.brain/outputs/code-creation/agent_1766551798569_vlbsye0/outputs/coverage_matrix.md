# Coverage Matrix (Stage 1)

This matrix tracks planned deliverables and how to verify them via committed code and generated artifacts.

Legend: ✅ complete | ⏳ planned
| Deliverable | Stage | Status | Verification (links) | Notes |
|---|---:|---|---|---|
| Deterministic pipeline entrypoint (end-to-end) | 1 | ✅ | Run: `scripts/run_pipeline.py` → Artifacts: [`outputs/results.json`](./results.json), [`outputs/figure.png`](./figure.png), [`outputs/run_stamp.json`](./run_stamp.json), Logs: [`outputs/logs/`](./logs/) | Fixed random seeds; stable JSON schemas; deterministic figure rendering; run-scoped log files. Also linked from `/outputs/roadmap_v1.md` as first completed deliverable. |
## Artifact expectations (for reviewers)

- `outputs/results.json`: stable keys and numeric precision (no nondeterministic ordering).
- `outputs/run_stamp.json`: includes seed(s), git/host metadata where applicable, and timestamp policy is deterministic or explicitly documented.
- `outputs/figure.png`: deterministic content/style (fixed DPI, size, font settings).
- `outputs/logs/*.log`: consistent formatting, stable header fields, and run identifier correlating to `run_stamp.json`.
