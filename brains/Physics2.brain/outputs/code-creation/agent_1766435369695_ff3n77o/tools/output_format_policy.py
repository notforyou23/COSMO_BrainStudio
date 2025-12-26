"""Shared benchmark output format policy.

This module is consumed by validators and CI/pre-commit hooks to:
- define which JSON output paths are accepted as benchmark outputs
- flag deprecated legacy/ad-hoc output paths for migration
- map output paths to schema versions (used to pick a JSON Schema file)

Design goals: tiny, deterministic, no I/O, and stable error messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Iterable, Optional, Sequence, Tuple
# Canonical schema version used by the repository. Validators should map versions
# to concrete schema paths (e.g. outputs/schemas/benchmark_schema.json).
DEFAULT_SCHEMA_VERSION = "v1"

# When adding a new schema version, keep the old version mapping so migration
# messaging can remain actionable.
KNOWN_SCHEMA_VERSIONS = ("v1",)
@dataclass(frozen=True)
class PathRule:
    """Policy rule for benchmark output JSON paths."""

    name: str
    glob: str  # POSIX-style glob matched against repo-relative path
    schema_version: str = DEFAULT_SCHEMA_VERSION
    deprecated: bool = False
    note: str = ""
# Allowed locations for benchmark output JSON files.
# Keep these narrow: validation should fail loudly if outputs are written
# somewhere unexpected (helps catch ad-hoc formats early).
ALLOWED_RULES: Tuple[PathRule, ...] = (
    PathRule(
        name="canonical_outputs_dir",
        glob="outputs/**/*.json",
        schema_version="v1",
        note="Canonical benchmark outputs location.",
    ),
    PathRule(
        name="benchmarks_results_dir",
        glob="benchmarks/**/results/**/*.json",
        schema_version="v1",
        note="Benchmark-specific results subdirectories.",
    ),
)

# Deprecated legacy/ad-hoc output locations that must be migrated.
DEPRECATED_RULES: Tuple[PathRule, ...] = (
    PathRule(
        name="legacy_results_root",
        glob="results/**/*.json",
        schema_version="v1",
        deprecated=True,
        note="Legacy root-level results/. Move files under outputs/.",
    ),
    PathRule(
        name="legacy_benchmark_output_json",
        glob="**/output.json",
        schema_version="v1",
        deprecated=True,
        note="Ambiguous ad-hoc output.json. Rename and move under outputs/.",
    ),
)
def _to_posix_relpath(path: str) -> str:
    # Validators may pass Windows paths; normalize to POSIX for matching.
    return path.replace("\\", "/").lstrip("./")


def _match_first(rules: Sequence[PathRule], relpath: str) -> Optional[PathRule]:
    for r in rules:
        if fnmatch(relpath, r.glob):
            return r
    return None
def classify_path(relpath: str) -> Tuple[str, Optional[PathRule]]:
    """Classify a repo-relative path.

    Returns (status, rule) where status is one of:
      - "allowed": matches an allowed rule
      - "deprecated": matches a deprecated rule
      - "unknown": matches neither
    """
    rel = _to_posix_relpath(relpath)
    rule = _match_first(ALLOWED_RULES, rel)
    if rule:
        return "allowed", rule
    rule = _match_first(DEPRECATED_RULES, rel)
    if rule:
        return "deprecated", rule
    return "unknown", None


def is_allowed_output_path(relpath: str) -> bool:
    return classify_path(relpath)[0] == "allowed"


def is_deprecated_output_path(relpath: str) -> bool:
    return classify_path(relpath)[0] == "deprecated"
def schema_version_for_output_path(relpath: str) -> Optional[str]:
    """Return schema version for a path if it is recognized (allowed/deprecated)."""
    status, rule = classify_path(relpath)
    if status in ("allowed", "deprecated") and rule:
        return rule.schema_version
    return None


def explain_path_policy(relpath: str) -> str:
    """Human-readable explanation used in actionable validator errors."""
    status, rule = classify_path(relpath)
    rel = _to_posix_relpath(relpath)
    if status == "allowed":
        return f"{rel}: allowed ({rule.name}); schema={rule.schema_version}."
    if status == "deprecated":
        note = f" {rule.note}" if rule.note else ""
        return f"{rel}: DEPRECATED ({rule.name}); schema={rule.schema_version}.{note}"
    allowed = ", ".join(r.glob for r in ALLOWED_RULES)
    return f"{rel}: not a recognized benchmark output path. Allowed globs: {allowed}."
def iter_policy_globs(include_deprecated: bool = False) -> Iterable[str]:
    """Yield globs used by discovery tooling."""
    for r in ALLOWED_RULES:
        yield r.glob
    if include_deprecated:
        for r in DEPRECATED_RULES:
            yield r.glob
