# RESULTS.json Stable Schema (v1)

This project writes a single machine-readable results file at: `outputs/results.json`.
This document defines the **stable schema**, **versioning policy**, and **determinism guarantees** (seed + plotting defaults) required for reproducible outputs.

## 1) Versioning policy

- `schema_version` uses **SemVer**: `MAJOR.MINOR.PATCH` (string).
- **MAJOR** increments for breaking schema changes (removed/renamed fields, type changes, meaning changes).
- **MINOR** increments for backward-compatible additions (new optional fields).
- **PATCH** increments for clarifications or tightening validation without changing meaning.
- Parsers MUST:
  - Reject unknown `schema_version` MAJOR versions.
  - Allow additional top-level keys only if explicitly documented as optional for the current MAJOR.

Current schema version: **1.0.0**.

## 2) Top-level object (required)

`results.json` MUST be a single JSON object with these required fields:

- `schema_version` (string): `"1.0.0"`
- `run` (object): required run metadata (see §3)
- `determinism` (object): required determinism metadata (see §4)
- `results` (object): required domain results (see §5)
- `artifacts` (array): required list of output files (may be empty) (see §6)

Recommended encoding for stable diffs: UTF-8, `json.dumps(..., sort_keys=True, indent=2)`.

## 3) `run` object (required)

`run` MUST include:

- `id` (string): unique run identifier (e.g., UUID or timestamp-based); stable within the run.
- `created_utc` (string): RFC3339/ISO-8601 UTC timestamp, e.g. `"2025-01-01T12:34:56Z"`.
- `project` (string): project/repo name (e.g., `"generated_script_1766547587406"`).
- `command` (string): entrypoint command line or equivalent description.
- `git` (object): source state
  - `commit` (string): git SHA or `"UNKNOWN"` if not available.
  - `dirty` (boolean): true if working tree had uncommitted changes.
- `environment` (object):
  - `python_version` (string)
  - `platform` (string) (e.g., `platform.platform()`)
  - `packages` (object, optional): map of selected package versions (strings).

## 4) `determinism` object (required)

`determinism` MUST include:

- `seed` (integer): the single canonical seed used for the run.
- `python_hash_seed` (integer): value used for `PYTHONHASHSEED` (should equal `seed` when possible).
- `random` (object):
  - `module` (string): e.g., `"random"`
  - `seeded` (boolean)
- `numpy` (object, optional if numpy absent):
  - `seeded` (boolean)
  - `bit_generator` (string): e.g., `"PCG64"` (record actual generator)
- `torch` (object, optional if torch absent):
  - `seeded` (boolean)
  - `deterministic_algorithms` (boolean): `torch.use_deterministic_algorithms(True)` status
  - `cudnn_deterministic` (boolean, optional)
  - `cudnn_benchmark` (boolean, optional)
- `matplotlib` (object, optional if matplotlib absent):
  - `backend` (string): SHOULD be `"Agg"` for headless determinism
  - `rcparams` (object): a curated snapshot of rcParams that affect output (see §7)

## 5) `results` object (required)

`results` contains the experiment outputs and MUST include:

- `status` (string): `"success"` or `"error"`.
- `metrics` (object): string keys to JSON-serializable scalars/arrays/objects (no NaN/Infinity).
- `summary` (string, optional): short human-readable summary.
- `error` (object, required only when `status="error"`):
  - `type` (string)
  - `message` (string)
  - `traceback` (string, optional)

Rules:
- All numbers MUST be finite (no NaN/Infinity). Serialize with coercion or error.
- Use stable key ordering when writing JSON (`sort_keys=True`).
- If multiple experiments are run, `metrics` may contain nested objects keyed by experiment name.

## 6) `artifacts` array (required)

`artifacts` is an array of objects describing files written under `outputs/` (and subdirs). It MAY be empty.

Each artifact object MUST include:

- `path` (string): POSIX-like relative path from project root or from `outputs/` (choose one convention and keep it consistent).
- `kind` (string): e.g., `"figure"`, `"table"`, `"data"`, `"log"`, `"other"`.
- `sha256` (string): lowercase hex SHA-256 of the file bytes.
- `bytes` (integer): file size in bytes.

Optional fields:
- `description` (string)
- `content_type` (string): e.g., `"image/png"`, `"application/json"`.

Artifacts MUST be listed in a stable order (lexicographic by `path`).

## 7) Plot determinism guarantees (matplotlib)

To ensure deterministic figures across runs on the same platform, the pipeline MUST:
- Use a non-interactive backend: `matplotlib.use("Agg")` before importing `pyplot`.
- Pin rcParams that affect rendering and file output. At minimum record and set:
  - `figure.dpi`, `savefig.dpi`
  - `figure.figsize`
  - `savefig.bbox`, `savefig.pad_inches`
  - `font.family`, `font.size`
  - `axes.titlesize`, `axes.labelsize`
  - `lines.linewidth`, `lines.markersize`
  - `image.interpolation`
  - `path.simplify`, `path.simplify_threshold`
  - `text.usetex` (SHOULD be `False` unless explicitly required)

File writing MUST:
- Use explicit `dpi` on `savefig` when applicable.
- Prefer PNG for bitmap determinism; if using SVG/PDF, note that embedded metadata/fonts can vary.

## 8) Randomness determinism guarantees (seeding)

The pipeline MUST set a single canonical seed and apply it consistently:
- Set `PYTHONHASHSEED` to the chosen seed (best effort; environment-level).
- Seed Python `random.seed(seed)`.
- If numpy is present: `numpy.random.seed(seed)` OR use a pinned `Generator(PCG64(seed))` and record `bit_generator`.
- If torch is present:
  - `torch.manual_seed(seed)` and, if CUDA, `torch.cuda.manual_seed_all(seed)`.
  - Enable deterministic algorithms when feasible and record the flags.
- Any library-specific RNGs (e.g., sklearn, scipy) MUST be driven by the canonical seed via explicit parameters where applicable.

## 9) Example (illustrative)

Top-level shape (not exhaustive):

- schema_version: "1.0.0"
- run: {id, created_utc, project, command, git, environment}
- determinism: {seed, python_hash_seed, random, numpy?, torch?, matplotlib?}
- results: {status, metrics, summary?, error?}
- artifacts: [{path, kind, sha256, bytes, ...}, ...]
