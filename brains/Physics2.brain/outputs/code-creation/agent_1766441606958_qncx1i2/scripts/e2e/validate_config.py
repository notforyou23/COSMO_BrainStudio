#!/usr/bin/env python3
\"\"\"Validate that modularized e2e workflow components stay in sync.

Checks:
- Expected workflow/action/doc paths exist.
- Composite action inputs match workflow `with:` usage (no unknown keys; required keys present).
- Basic CI env vars are present when running in GitHub Actions.

Usage:
  python scripts/e2e/validate_config.py [--repo-root PATH] [--strict]
\"\"\"
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None
EXPECTED_PATHS = [
    ".github/workflows/e2e_failure.yml",
    ".github/actions/e2e-common/action.yml",
    ".github/actions/e2e-on-failure/action.yml",
    "docs/e2e/README_e2e.md",
]

CI_REQUIRED_ENV = ["GITHUB_ACTIONS", "GITHUB_WORKSPACE", "GITHUB_RUN_ID", "GITHUB_SHA"]
def _find_repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / ".github").is_dir() or (p / ".git").exists():
            return p
    return start


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise SystemExit("PyYAML is required for validate_config.py (missing dependency 'yaml').")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a mapping.")
    return data
def _action_inputs(action_yml: Path) -> Tuple[Dict[str, Any], List[str]]:
    data = _load_yaml(action_yml)
    inputs = data.get("inputs") or {}
    if not isinstance(inputs, dict):
        raise ValueError(f"{action_yml}: 'inputs' must be a mapping.")
    required = []
    for k, v in inputs.items():
        if isinstance(v, dict) and v.get("required") is True:
            required.append(str(k))
    return {str(k): v for k, v in inputs.items()}, required


def _workflow_with_keys(workflow_yml: Path, uses_suffix: str) -> List[Tuple[int, str]]:
    \"\"\"Extract `with:` keys for steps that use a given action path suffix.

    This uses YAML when available; as a fallback it uses a conservative regex scan.
    \"\"\"
    try:
        data = _load_yaml(workflow_yml)
        jobs = data.get("jobs") or {}
        keys: List[Tuple[int, str]] = []
        for job in (jobs.values() if isinstance(jobs, dict) else []):
            steps = (job or {}).get("steps") if isinstance(job, dict) else None
            if not isinstance(steps, list):
                continue
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                uses = str(step.get("uses") or "")
                if uses.endswith(uses_suffix):
                    with_map = step.get("with") or {}
                    if isinstance(with_map, dict):
                        keys.extend((i, str(k)) for k in with_map.keys())
        return keys
    except Exception:
        txt = workflow_yml.read_text(encoding="utf-8")
        pattern = re.compile(rf\"uses:\\s*{re.escape(uses_suffix)}\\s*\\n\\s*with:\\s*\\n(?P<body>(\\s+\\w[^\\n]*\\n)+)\")
        keys = []
        for m in pattern.finditer(txt):
            for line in m.group(\"body\").splitlines():
                if \":\" in line:
                    keys.append((0, line.strip().split(\":\", 1)[0]))
        return keys
def _check_paths(repo_root: Path) -> List[str]:
    problems = []
    for rel in EXPECTED_PATHS:
        p = repo_root / rel
        if not p.exists():
            problems.append(f\"Missing expected path: {rel}\")
    return problems


def _check_ci_env() -> List[str]:
    if os.environ.get(\"GITHUB_ACTIONS\", \"\").lower() != \"true\":
        return []
    missing = [k for k in CI_REQUIRED_ENV if not os.environ.get(k)]
    return [f\"Missing required CI env var: {k}\" for k in missing]
def _check_action_vs_workflow(repo_root: Path) -> List[str]:
    problems: List[str] = []
    wf = repo_root / \".github/workflows/e2e_failure.yml\"
    common = repo_root / \".github/actions/e2e-common/action.yml\"
    failure = repo_root / \".github/actions/e2e-on-failure/action.yml\"
    if not (wf.exists() and common.exists() and failure.exists()):
        return problems

    def validate(action_yml: Path, uses_suffix: str) -> None:
        inputs, required = _action_inputs(action_yml)
        used_keys = [k for _, k in _workflow_with_keys(wf, uses_suffix)]
        for k in used_keys:
            if k not in inputs:
                problems.append(f\"{wf.name}: unknown input '{k}' for action {uses_suffix}\")
        for k in required:
            if k not in used_keys:
                problems.append(f\"{wf.name}: missing required input '{k}' for action {uses_suffix}\")

    validate(common, \"./.github/actions/e2e-common\")
    validate(failure, \"./.github/actions/e2e-on-failure\")
    return problems
def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(\"--repo-root\", type=Path, default=None, help=\"Override repository root.\")
    ap.add_argument(\"--strict\", action=\"store_true\", help=\"Treat warnings as errors.\")
    ns = ap.parse_args(list(argv) if argv is not None else None)

    repo_root = ns.repo_root.resolve() if ns.repo_root else _find_repo_root(Path(__file__).resolve())
    problems = []
    problems += _check_paths(repo_root)
    problems += _check_ci_env()
    problems += _check_action_vs_workflow(repo_root)

    if problems:
        for p in problems:
            print(f\"CONFIG_VALIDATE_ERROR: {p}\", file=sys.stderr)
        return 2
    print(\"CONFIG_VALIDATE_OK\")
    return 0


if __name__ == \"__main__\":
    raise SystemExit(main())
