# E2E failure diagnostics (workflow + action)

This document explains how we collect and upload diagnostics **only when E2E fails** in CI, using:
- **Reusable workflow**: `.github/workflows/e2e_failure.yml`
- **Composite action**: `.github/actions/e2e-on-failure/action.yml`
- **Collector script**: `scripts/e2e/collect_diagnostics.sh` (gathers files + metadata into one directory)
- **Config validator**: `scripts/e2e/validate_config.py` (fails fast on bad inputs/assumptions)

The goal is consistent artifacts (logs/screenshots/videos/reports) across E2E jobs without bloating successful runs.
## How it works (high level)

1. Your E2E job runs tests normally.
2. A final step calls the composite action with `if: failure()` so it runs **only on failure**.
3. The action:
   - validates inputs/environment,
   - collects diagnostics into a single folder,
   - uploads that folder as a GitHub Actions artifact.

If the job succeeds, the collector/upload steps are skipped.
## Inputs (composite action)

Common inputs used by the action/workflow (names may be passed directly or via the reusable workflow):
- `name` (string): Artifact name, e.g. `e2e-diagnostics-${{ github.run_id }}`.
- `diagnostics_dir` (string): Output directory for collected diagnostics (default typically `e2e-diagnostics`).
- `workdir` (string): Working directory where your E2E project lives (monorepo-friendly).
- `paths` (multiline string): Extra paths/globs to include (optional).
- `retention_days` (number): Artifact retention period.
- `upload` (boolean): Whether to upload the artifact (useful to disable locally).

Environment variables that improve metadata (optional):
- `CI`, `GITHUB_*` (provided by Actions)
- App/test specific vars (base URLs, browser, shard index, etc.).
## Diagnostics artifact layout

The collector script produces a single directory (the value of `diagnostics_dir`) containing a predictable structure.

Typical contents (when present):
- `meta/`
  - `github_context.json` (subset of GitHub context)
  - `env.txt` (selected environment variables)
  - `system.txt` (OS/kernel/versions when available)
- `logs/` (application/server logs, playwright/cypress logs, etc.)
- `screenshots/` (failure screenshots)
- `videos/` (failure videos)
- `reports/` (JUnit/XML/HTML reports, coverage summaries if relevant)
- `raw/` (any extra files you include via `paths`)

The artifact is uploaded as a single bundle to make “download and inspect” fast.
## CI usage

### Option A: Use the reusable workflow (recommended)

In an E2E workflow, call the reusable workflow after/around your test job as designed by your repo’s standard. Example pattern:

```yaml
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run E2E
        run: npm test -- --e2e

      - name: Upload diagnostics on failure
        if: failure()
        uses: ./.github/actions/e2e-on-failure
        with:
          name: e2e-diagnostics-${{ github.run_id }}
          workdir: .
          diagnostics_dir: e2e-diagnostics
          retention_days: 14
```

Your repo may alternatively centralize this logic by `uses: ./.github/workflows/e2e_failure.yml` (workflow_call),
so multiple E2E pipelines share the same failure-handling behavior.
### Option B: Call the composite action directly

Use this when you want per-job customization without the reusable workflow:

- Add the action at the end of the job.
- Guard it with `if: failure()` (or `if: cancelled() || failure()` if desired).
- Pass `paths` for framework-specific locations (Playwright, Cypress, Selenium, etc.).
## Local usage (developer machine)

You can run the collector locally to package diagnostics after a failed run:

```bash
# From repo root (or set WORKDIR accordingly)
bash scripts/e2e/collect_diagnostics.sh   --workdir .   --out e2e-diagnostics   --paths "playwright-report"   --paths "test-results"   --paths "logs"
```

Notes:
- Local runs typically skip the “upload artifact” step; the output directory is still useful to attach to bug reports.
- If the validator is used in your scripts, run it first to catch missing directories/commands early:
  `python scripts/e2e/validate_config.py --workdir . --diagnostics-dir e2e-diagnostics`.
## Troubleshooting

- **No artifact uploaded**: confirm the step is gated with `if: failure()` and that the job actually failed (not skipped).
- **Artifact is empty**: ensure your E2E framework is configured to write reports/screenshots/videos to disk and that those paths are included.
- **Permission/path issues**: set `workdir` to the directory where the test output exists (common in monorepos).
- **Large artifacts**: reduce included paths or disable video capture except on failure in your test runner configuration.
