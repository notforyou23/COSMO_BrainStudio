# Release checklist (v0.1)

This checklist documents the exact, minimal steps to prepare and tag the `v0.1` release.

## 0) Preconditions

- You have push access to the canonical repository remote (assumed `origin`).
- Your local clone is up to date and on the release branch (typically `main`).
- Working tree is clean: `git status` shows no pending changes.

## 1) Prepare a clean, reproducible local environment

From the repo root:

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
```

Install *pinned* dependencies (use the repo’s pinned requirement files):

```bash
python -m pip install -r requirements.txt
# If present in this repo, also install dev/test pins:
python -m pip install -r requirements-dev.txt 2>/dev/null || true
```

## 2) Integrate agent-generated outputs into the canonical layout (if applicable)

If this repo includes the integration tooling:

```bash
python tools/integrate_agent_outputs.py --dry-run
python tools/integrate_agent_outputs.py
```

Then review and commit any resulting changes:

```bash
git status
git diff
git commit -am "Integrate agent outputs for v0.1"
```

## 3) Run the same checks as CI (locally)

Run formatting/lint hooks (mirrors CI via pre-commit if configured):

```bash
python -m pip install pre-commit
pre-commit run --all-files
```

Run the test suite:

```bash
python -m pip install pytest
pytest -q
```

## 4) Verify GitHub Actions CI is green for the release commit

1. Push the release commit to the branch used by CI (usually `main`):

```bash
git push origin HEAD:main
```

2. Confirm the workflow in `.github/workflows/ci.yml` completed successfully for that commit in GitHub Actions.

## 5) Tag and push v0.1

Ensure you are tagging the exact commit that passed CI:

```bash
git rev-parse --short HEAD
git tag -a v0.1 -m "v0.1"
git push origin v0.1
```

## 6) Final verification

- Confirm GitHub Actions CI also ran (and is green) for the `v0.1` tag.
- Confirm `git describe --tags --exact-match` returns `v0.1` on the release commit.
