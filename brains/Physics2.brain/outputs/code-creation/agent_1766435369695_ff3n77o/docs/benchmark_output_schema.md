# Benchmark output schema (v1)

This repository standardizes benchmark outputs as JSON validated by a single canonical JSON Schema (`outputs/schemas/benchmark_schema.json`).
Any benchmark output JSON committed to the repo **must** conform to this schema; legacy/ad-hoc formats are deprecated and will fail validation.

## Where benchmark outputs may live (path policy)

Benchmark output JSON files are recognized only in these locations:

- **Allowed (canonical)**:
  - `outputs/**/*.json`
  - `benchmarks/**/results/**/*.json`
- **Deprecated** (must migrate):
  - `results/**/*.json`
  - `**/output.json` (and other ambiguous generic filenames like `results.json`, `metrics.json`, `eval.json`)

Rationale: keeping outputs in predictable locations makes discovery/validation reliable and prevents format drift.

## Top-level shape

A benchmark output is a single JSON object with the following required top-level keys:

| Field | Type | Required | Notes |
|---|---:|:---:|---|
| `$schema` | string | yes | URI/path to the JSON Schema used to validate this file. |
| `schema_version` | string | yes | Schema version identifier (currently `v1`). |
| `metadata` | object | yes | Identifies *what* was run (benchmark/model/dataset) and *how* it was produced. |
| `results` | object | yes | The measured outcomes (metrics), plus optional per-case details. |

All other top-level keys are reserved for future schema versions.

## `metadata` (required)

`metadata` is an object with the following required keys:

| Field | Type | Required | Notes |
|---|---:|:---:|---|
| `benchmark` | object | yes | Benchmark identity (name and optional suite/version). |
| `model` | object | yes | Model identity (name/provider and optional parameters). |
| `run` | object | yes | Run identity and provenance (time, git commit, command, environment). |

Recommended (optional) keys:
- `tags` (array of strings): freeform labels for filtering/grouping.
- `notes` (string): human-friendly context (kept short; large logs belong in artifacts).

### `metadata.benchmark` (required)
Required:
- `name` (string): benchmark name (e.g. `"mmlu"`, `"swe-bench"`, `"custom_eval"`)

Optional:
- `suite` (string): benchmark suite/grouping
- `version` (string): benchmark version or config id
- `task` (string): task name/subset (if applicable)

### `metadata.model` (required)
Required:
- `name` (string): model identifier (e.g. `"gpt-4.1-mini"`, `"llama-3.1-8b-instruct"`)
- `provider` (string): model provider or runtime (e.g. `"openai"`, `"vllm"`, `"hf"`)

Optional:
- `parameters` (object): stable, JSON-serializable settings (temperature, max_tokens, etc.)
- `revision` (string): checkpoint/revision hash/tag if applicable

### `metadata.run` (required)
Required:
- `id` (string): unique run id within the repo (recommend UUID or timestamp-based id)
- `started_at` (string): ISO-8601 timestamp
Optional but strongly recommended:
- `finished_at` (string): ISO-8601 timestamp
- `git` (object): `{ "commit": "...", "dirty": false }`
- `command` (string): command line used to produce the output
- `host` (object): `{ "os": "...", "python": "...", "hostname": "..." }`

## `results` (required)

`results` is an object with the following required keys:

| Field | Type | Required | Notes |
|---|---:|:---:|---|
| `status` | string | yes | `"ok"` or `"error"`. |
| `metrics` | object | yes | Map of metric name → numeric value. |

Optional keys:
- `error` (object): present when `status` is `"error"`; include `message` and optional `type`/`traceback`.
- `details` (object): structured, schema-stable aggregates (confusion matrices, per-split metrics, etc.).
- `cases` (array): per-item results (keep minimal; large payloads should be stored separately and referenced).
- `artifacts` (array): references to external files (paths/URIs + role).

### Metric naming guidance
Use short, stable keys (snake_case), e.g. `accuracy`, `f1`, `pass_at_1`, `latency_ms_p50`.
Prefer units in the name when needed (e.g. `latency_ms_p95`).

## Minimal valid example (v1)

```json
{
  "$schema": "outputs/schemas/benchmark_schema.json",
  "schema_version": "v1",
  "metadata": {
    "benchmark": { "name": "mmlu", "task": "all" },
    "model": { "name": "gpt-4.1-mini", "provider": "openai" },
    "run": { "id": "2025-12-22T18:00:00Z_001", "started_at": "2025-12-22T18:00:00Z" }
  },
  "results": {
    "status": "ok",
    "metrics": { "accuracy": 0.712 }
  }
}
```

## Example with per-split details and artifacts

```json
{
  "$schema": "outputs/schemas/benchmark_schema.json",
  "schema_version": "v1",
  "metadata": {
    "benchmark": { "name": "custom_eval", "suite": "regression", "version": "2025.12" },
    "model": {
      "name": "llama-3.1-8b-instruct",
      "provider": "vllm",
      "parameters": { "temperature": 0.2, "max_tokens": 512 }
    },
    "run": {
      "id": "f6a3e3b3-6ac2-4ab8-9fd2-1d2d6f7d4c2a",
      "started_at": "2025-12-22T18:00:00Z",
      "finished_at": "2025-12-22T18:08:31Z",
      "git": { "commit": "abc1234", "dirty": false },
      "command": "python -m benchmarks.run --suite regression"
    },
    "tags": ["nightly", "cpu"]
  },
  "results": {
    "status": "ok",
    "metrics": { "pass_at_1": 0.43, "latency_ms_p50": 120.5 },
    "details": {
      "by_split": {
        "easy": { "pass_at_1": 0.61 },
        "hard": { "pass_at_1": 0.22 }
      }
    },
    "artifacts": [
      { "role": "raw_predictions", "path": "outputs/artifacts/f6a3e3b3/preds.jsonl" }
    ]
  }
}
```

## Migration notes (deprecated ad-hoc formats)

The validator intentionally flags common ad-hoc outputs such as `output.json`/`results.json` and legacy shapes like:
- `{ "config": ..., "results": ... }`
- `{ "metrics": ..., "metadata": ... }`
- `{ "scores": ..., "details": ... }`

To migrate:
1. **Move/rename the file** to a canonical location (prefer `outputs/<benchmark>/<run_id>.json`).
2. **Add** top-level `$schema` and `schema_version: "v1"`.
3. **Map metadata**:
   - old `config.*` → `metadata.*` (benchmark/model/run parameters)
   - old `metadata.*` → `metadata.*` (ensure `benchmark`, `model`, `run` exist)
4. **Map results**:
   - old `metrics`/`scores` → `results.metrics`
   - old `details` → `results.details`
   - failures/errors → `results.status="error"` and `results.error.message`

CI/pre-commit will fail if deprecated locations or non-conforming JSON are committed, ensuring the schema remains the single source of truth.
