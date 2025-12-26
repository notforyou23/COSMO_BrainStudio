#!/usr/bin/env bash
set -euo pipefail

TAG="v0.1.0"
REMOTE="${REMOTE:-origin}"
PUSH_TAG="${PUSH_TAG:-0}"
SIGN_TAG="${SIGN_TAG:-0}"
SKIP_CI_CHECK="${SKIP_CI_CHECK:-0}"

die() { echo "error: $*" >&2; exit 1; }
info() { echo "==> $*" >&2; }

command -v git >/dev/null 2>&1 || die "git not found"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository"

# Ensure clean working tree (no staged/unstaged/untracked changes)
git update-index -q --refresh || true
git diff --quiet || die "working tree has unstaged changes"
git diff --cached --quiet || die "index has staged but uncommitted changes"
if [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
  die "working tree has untracked files"
fi

SHA="$(git rev-parse HEAD)"
info "HEAD commit: ${SHA}"

# Verify CI checks for HEAD using GitHub CLI (unless skipped)
if [[ "${SKIP_CI_CHECK}" != "1" ]]; then
  if command -v gh >/dev/null 2>&1; then
    info "Checking GitHub CI status for ${SHA}"
    REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
    [[ -n "${REPO}" ]] || die "unable to determine GitHub repo (try: gh auth login, or set SKIP_CI_CHECK=1)"

    # Combined status must be success (covers many CI providers)
    COMBINED_STATE="$(gh api "repos/${REPO}/commits/${SHA}/status" -q .state 2>/dev/null || true)"
    [[ -n "${COMBINED_STATE}" ]] || die "unable to fetch combined status for ${SHA}"
    [[ "${COMBINED_STATE}" == "success" ]] || die "combined status is '${COMBINED_STATE}' (expected success)"

    # Check runs (GitHub Actions, etc.): all completed; conclusions success/neutral/skipped
    bad="$(gh api -H "Accept: application/vnd.github+json" "repos/${REPO}/commits/${SHA}/check-runs" \
      -q '.check_runs[]
          | select(.status!="completed")
          | "\(.name):status=\(.status)"' 2>/dev/null || true)"
    [[ -z "${bad}" ]] || die "some check-runs are not completed: ${bad}"

    bad="$(gh api -H "Accept: application/vnd.github+json" "repos/${REPO}/commits/${SHA}/check-runs" \
      -q '.check_runs[]
          | select(.conclusion!=null)
          | select(.conclusion!="success" and .conclusion!="neutral" and .conclusion!="skipped")
          | "\(.name):conclusion=\(.conclusion)"' 2>/dev/null || true)"
    [[ -z "${bad}" ]] || die "some check-runs did not succeed: ${bad}"

    info "CI checks passed for ${SHA}"
  else
    die "gh (GitHub CLI) not found; install it or set SKIP_CI_CHECK=1"
  fi
else
  info "SKIP_CI_CHECK=1 set; skipping CI verification"
fi

# Ensure tag is not already pointing elsewhere
if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
  existing="$(git rev-list -n 1 "${TAG}")"
  [[ "${existing}" == "${SHA}" ]] || die "tag ${TAG} already exists and points to ${existing}, not ${SHA}"
  info "tag ${TAG} already exists at ${SHA}; verifying"
else
  msg="Reproducible release ${TAG}

Commit: ${SHA}
Created: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [[ "${SIGN_TAG}" == "1" ]]; then
    info "Creating signed annotated tag ${TAG}"
    git tag -s -m "${msg}" "${TAG}" "${SHA}"
  else
    info "Creating annotated tag ${TAG}"
    git tag -a -m "${msg}" "${TAG}" "${SHA}"
  fi
fi

# Verify tag is exact at HEAD and has an annotation (lightweight tags are disallowed)
git describe --exact-match --tags "${SHA}" 2>/dev/null | grep -qx "${TAG}" || die "tag ${TAG} is not an exact match for HEAD"
tag_type="$(git cat-file -t "${TAG}")"
[[ "${tag_type}" == "tag" ]] || die "${TAG} is not an annotated tag (type=${tag_type})"
info "Verified ${TAG} is an annotated tag on HEAD"

if [[ "${PUSH_TAG}" == "1" ]]; then
  info "Pushing tag ${TAG} to ${REMOTE}"
  git push "${REMOTE}" "refs/tags/${TAG}"
  info "Pushed ${TAG}"
fi

info "Release tag ready: ${TAG} -> ${SHA}"
