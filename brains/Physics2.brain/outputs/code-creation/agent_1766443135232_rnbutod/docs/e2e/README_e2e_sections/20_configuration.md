## Configuration

This E2E workflow is configured via a small set of human-editable config files plus environment variables for secrets/CI overrides. The goals are:
- **Reproducibility**: configs are committed (except secrets) and can be reviewed.
- **Portability**: local and CI runs use the same schema.
- **Early failure**: configs are validated before long-running steps start.
### Configuration files (recommended layout)

Place E2E configuration under the repository’s `docs/e2e/` or project root (either works as long as you pass the path consistently):

- `e2e.config.json` (or `e2e.config.yaml`): primary runtime configuration
- `.env` (optional): local-only environment variables (do not commit secrets)

If your run scripts accept a `--config` flag, prefer it; otherwise, use the default file name expected by the scripts in this repo.
### Required keys (minimum schema)

The exact structure may vary by project, but E2E runs generally require the following **minimum** configuration fields:

- `project.name` (string): human-readable name for logs/artifacts.
- `run.mode` (string): e.g. `local` or `ci` (used to select defaults).
- `paths.work_dir` (string): writable directory for temporary files.
- `paths.artifacts_dir` (string): directory where outputs (logs/results) are stored.
- `data.input_uri` (string): path/URI to input data (local path, `s3://…`, etc.).
- `outputs.report_name` (string): name/prefix for final report artifacts.

If your pipeline talks to external services, include:
- `remote.endpoint` (string) and `remote.timeout_s` (number) for API-backed runs.
- `auth.*` fields **must not** contain secrets in committed files; use environment variables instead.
### Environment variables (secrets & overrides)

Use environment variables for secrets and for small runtime tweaks in CI. Common patterns:
- `E2E_CONFIG_PATH`: points to the config file to load.
- `E2E_WORK_DIR`, `E2E_ARTIFACTS_DIR`: override `paths.*` without editing configs.
- `E2E_LOG_LEVEL`: e.g. `DEBUG`, `INFO`, `WARNING`.
- `E2E_API_KEY`, `E2E_TOKEN`, etc.: credentials injected by your shell/CI.

Precedence recommendation (highest to lowest):
1. CLI flags (if supported)
2. Environment variables
3. Config file values
4. Script defaults
### Validation expectations

Before executing any heavy steps, the runner should validate:
- **File existence & readability**: config file loads cleanly (JSON/YAML parse).
- **Type checks**: strings vs numbers vs booleans match expected types.
- **Path checks**: `paths.work_dir` is writable; `paths.artifacts_dir` is creatable.
- **Required fields**: all minimum schema keys are present and non-empty.
- **Cross-field consistency**: e.g. if `remote.endpoint` is set, required `auth` env vars are present.
- **Fail fast**: invalid configuration should exit non-zero with actionable errors.

In CI, prefer printing the **effective (redacted)** configuration to logs to aid debugging (never print secrets).
### Example: `e2e.config.json`

```json
{
  "project": { "name": "generated_script_1766443139257" },
  "run": { "mode": "local" },
  "paths": {
    "work_dir": ".e2e/work",
    "artifacts_dir": ".e2e/artifacts"
  },
  "data": { "input_uri": "data/sample_input.jsonl" },
  "outputs": { "report_name": "e2e_report" },
  "remote": { "endpoint": "http://localhost:8080", "timeout_s": 30 }
}
```
### Example: `.env` for local development (do not commit)

```bash
# Optional: point to a non-default config file
export E2E_CONFIG_PATH=./e2e.config.json

# Secrets / credentials (local only)
export E2E_API_KEY="replace-with-real-key"

# Overrides
export E2E_LOG_LEVEL=INFO
export E2E_WORK_DIR=.e2e/work
export E2E_ARTIFACTS_DIR=.e2e/artifacts
```
### Tips

- Keep config files **small** and **stable**; push frequently changing values into env vars.
- Use relative paths in configs where possible so runs work from a clean checkout.
- Store large generated outputs only under `paths.artifacts_dir` to simplify cleanup and CI artifact collection.
