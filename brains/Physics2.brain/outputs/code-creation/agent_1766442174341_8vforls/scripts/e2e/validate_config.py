#!/usr/bin/env python3
"""Validate E2E-on-failure configuration for CI.

This script is intended to run early in a job (or inside a composite action)
to fail fast with actionable diagnostics when required inputs/environment
assumptions for E2E failure artifact collection are not met.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def fail(msg: str, *, code: int = 2) -> "never":
    _eprint(f"ERROR: {msg}")
    raise SystemExit(code)


def warn(msg: str) -> None:
    _eprint(f"WARNING: {msg}")


def is_truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "y", "on"}
def validate_artifact_name(name: str) -> None:
    if not name.strip():
        fail("artifact-name is required and cannot be empty.")
    if len(name) > 128:
        fail("artifact-name must be <= 128 characters (GitHub artifact UI limit).")
    # Keep it conservative for cross-platform filesystems and upload action.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        fail(
            "artifact-name contains unsupported characters. "
            "Use only letters, numbers, '.', '_', '-' and start with a letter/number."
        )
def validate_retention_days(retention_days: int) -> None:
    if retention_days < 1 or retention_days > 90:
        fail("retention-days must be between 1 and 90 (inclusive).")
def validate_diagnostics_dir(path_str: str, workspace: Path | None) -> Path:
    if not path_str.strip():
        fail("diagnostics-dir is required and cannot be empty.")
    p = Path(path_str)
    if p.is_absolute() and workspace:
        # Absolute is okay only if it is inside workspace.
        try:
            p.relative_to(workspace)
        except ValueError:
            fail(
                f"diagnostics-dir '{p}' must be within GITHUB_WORKSPACE '{workspace}'. "
                "Use a relative path like 'e2e-diagnostics'."
            )
    if not p.is_absolute() and workspace:
        p = workspace / p

    # Ensure parent exists (collector will create the directory itself).
    parent = p.parent
    if not parent.exists():
        fail(f"Parent directory for diagnostics-dir does not exist: '{parent}'.")
    if parent.is_file():
        fail(f"Parent path for diagnostics-dir is a file, expected directory: '{parent}'.")
    return p
def validate_environment(require_github_actions: bool) -> tuple[Path | None, dict]:
    env = os.environ
    in_gha = is_truthy(env.get("GITHUB_ACTIONS"))
    if require_github_actions and not in_gha:
        fail(
            "This validator is configured to require GitHub Actions, but "
            "GITHUB_ACTIONS is not 'true'. If running locally, pass --allow-non-gha."
        )

    workspace = env.get("GITHUB_WORKSPACE")
    ws_path = Path(workspace) if workspace else None
    if in_gha:
        missing = [k for k in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_SHA") if not env.get(k)]
        if missing:
            fail(
                "Missing required GitHub Actions environment variables: "
                + ", ".join(missing)
                + ". Ensure this runs in a normal Actions job context."
            )
        if not ws_path:
            fail("GITHUB_WORKSPACE is not set; cannot safely resolve diagnostics paths.")
        if not ws_path.exists():
            fail(f"GITHUB_WORKSPACE path does not exist: '{ws_path}'.")
        if not ws_path.is_dir():
            fail(f"GITHUB_WORKSPACE is not a directory: '{ws_path}'.")

    return ws_path, {"in_github_actions": in_gha}
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--diagnostics-dir", required=True, help="Directory where diagnostics will be written.")
    ap.add_argument("--artifact-name", required=True, help="Artifact name used when uploading diagnostics.")
    ap.add_argument("--retention-days", type=int, default=7, help="Artifact retention (1-90). Default: 7.")
    ap.add_argument(
        "--allow-non-gha",
        action="store_true",
        help="Allow running outside GitHub Actions (skips GHA env checks).",
    )
    ap.add_argument(
        "--require-collector",
        default="scripts/e2e/collect_diagnostics.sh",
        help="Path (relative to workspace) to the diagnostics collector script.",
    )
    ns = ap.parse_args(argv)

    workspace, meta = validate_environment(require_github_actions=not ns.allow_non_gha)
    validate_artifact_name(ns.artifact_name)
    validate_retention_days(ns.retention_days)
    diag_dir = validate_diagnostics_dir(ns.diagnostics_dir, workspace)

    collector = Path(ns.require_collector)
    if workspace and not collector.is_absolute():
        collector = workspace / collector
    if not collector.exists():
        fail(
            f"Collector script not found at '{collector}'. "
            "Verify the repo checkout and require-collector path."
        )
    if collector.is_dir():
        fail(f"Collector path points to a directory, expected file: '{collector}'.")
    if not os.access(collector, os.X_OK):
        warn(f"Collector script is not marked executable: '{collector}'. It may still run via 'bash ...'.")

    # Helpful hints for common misconfigurations.
    if diag_dir.exists() and diag_dir.is_file():
        fail(f"diagnostics-dir already exists but is a file: '{diag_dir}'.")
    if workspace and not str(diag_dir).startswith(str(workspace)):
        warn("Resolved diagnostics-dir is not under workspace; artifact upload may not find files.")

    print("OK: configuration validated.")
    if is_truthy(os.environ.get("CI")):
        print(f"OK: diagnostics-dir-resolved={diag_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
