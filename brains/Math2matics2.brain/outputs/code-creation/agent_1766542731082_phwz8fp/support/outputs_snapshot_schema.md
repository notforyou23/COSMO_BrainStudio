# Outputs snapshot schema (on-disk change detection)

This document defines the snapshot format used to compare `/outputs` (or its writable fallback) across research cycles, and how the enforcement logic decides whether a cycle “added/updated at least one output file”.

## Scope and assumptions

- Snapshots cover **regular files only** in the chosen outputs directory (no directories, symlinks, or special files).
- Paths are stored as **POSIX-style relative paths** from the outputs root.
- A “research cycle” captures a **before** snapshot at cycle start and an **after** snapshot at cycle end, then compares them.

## Snapshot file format

A snapshot is a UTF-8 JSON document (typically written to a temporary path during a run) with this structure:

```json
{
  "schema_version": 1,
  "root": "outputs",
  "created_at_utc": "2025-12-24T01:29:38Z",
  "files": {
    "README.md": {
      "size_bytes": 1234,
      "mtime_ns": 1735000000000000000,
      "sha256": "…optional hex…"
    },
    "core_findings.md": {
      "size_bytes": 4321,
      "mtime_ns": 1735000001000000000,
      "sha256": "…optional hex…"
    }
  }
}
```

### Field definitions

- `schema_version` (int): Must be `1` for this schema.
- `root` (str): Label for the outputs root used for the snapshot (e.g., `"outputs"` or `"outputs_fallback"`). This is informational; comparisons are based on relative paths.
- `created_at_utc` (str): ISO-8601 timestamp in UTC (seconds precision is sufficient).
- `files` (object): Mapping of `relative_path -> file_record`.

Each `file_record` contains:

- `size_bytes` (int): Size from `stat().st_size`.
- `mtime_ns` (int): Modification time in nanoseconds from `stat().st_mtime_ns`.
- `sha256` (str, optional): Hex digest of file contents. When present, it is the strongest change signal.

## Change classification

Given `before.files` and `after.files`:

- **Added**: path exists in `after` but not in `before`.
- **Deleted**: path exists in `before` but not in `after` (tracked for reporting, not sufficient to satisfy the policy).
- **Updated**: path exists in both and the file is considered different.

A file is considered **different** using the following precedence (strongest-first):

1. If both records have `sha256`: `sha256` differs ⇒ updated.
2. Else: `(size_bytes, mtime_ns)` differs ⇒ updated.

This allows a fast default (stat-based) and an integrity option (hash-based) when needed.

## Enforcement rule (“at least one added/updated output per cycle”)

A cycle **passes** the outputs policy if:

- `len(added_paths) + len(updated_paths) >= 1`

Notes:
- Deletions do **not** count toward compliance.
- Renames appear as a deletion + addition and therefore **do** count (via the addition).

## Writable outputs selection (portability)

Because `/outputs` may be unwritable in some environments, the pipeline selects an outputs root in this order:

1. Prefer the configured `outputs/` directory if it exists or can be created and a small write test succeeds.
2. Otherwise, use a **portable fallback** (e.g., a project-local directory under the working tree or a temp directory) and record that choice (e.g., `root: "outputs_fallback"`).

Snapshots always use the **actual** chosen root, ensuring the policy can be enforced even when the default outputs directory cannot be written.

## Determinism and stability

- Snapshot comparisons are path-based and do not depend on directory traversal order.
- Using `sha256` yields stable detection even on filesystems with coarse timestamp resolution; using `mtime_ns` is usually sufficient in CI-like environments.
