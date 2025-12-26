#!/usr/bin/env bash
set -euo pipefail

# Collect E2E diagnostics (logs, screenshots, videos, reports, and environment metadata)
# into a single directory suitable for upload as a CI artifact.
#
# Usage:
#   scripts/e2e/collect_diagnostics.sh [output_dir]
#
# Environment variables (optional, colon-separated path lists):
#   E2E_LOG_PATHS        Additional log files/dirs to copy
#   E2E_REPORT_PATHS     Additional test report files/dirs to copy
#   E2E_MEDIA_PATHS      Additional media (screenshots/videos) files/dirs to copy
#   E2E_DIAG_ROOT        Root directory where diagnostics dir will be created (default: .)
#   E2E_DIAG_NAME        Directory name (default: e2e-diagnostics-<timestamp>)
#   E2E_MAX_FILE_MB      Skip copying individual files larger than this (default: 200)
#   E2E_VERBOSE          Set to 1 for more logs
log() { echo "[collect_diagnostics] $*"; }
vlog() { [[ "${E2E_VERBOSE:-0}" == "1" ]] && log "$@"; }

ts_utc() { date -u +"%Y%m%dT%H%M%SZ"; }

have() { command -v "$1" >/dev/null 2>&1; }

# Copy a path (file/dir) into a destination subdir, preserving basename.
copy_path() {
  local src="$1" dest_dir="$2" max_mb="$3"
  [[ -e "$src" ]] || return 0
  mkdir -p "$dest_dir"
  if [[ -f "$src" ]]; then
    local size_mb=0
    if have stat; then
      # GNU stat: -c, BSD stat: -f
      size_mb=$(( ( $(stat -c '%s' "$src" 2>/dev/null || stat -f '%z' "$src") + 1048575 ) / 1048576 ))
    fi
    if [[ "$size_mb" -gt "$max_mb" ]]; then
      log "Skipping large file (> ${max_mb}MB): $src (${size_mb}MB)"
      return 0
    fi
    cp -p "$src" "$dest_dir/$(basename "$src")" 2>/dev/null || cp "$src" "$dest_dir/$(basename "$src")"
  else
    # Directory
    if have rsync; then
      rsync -a --delete-excluded --exclude='.git/' "$src"/ "$dest_dir/$(basename "$src")"/ 2>/dev/null || rsync -a "$src"/ "$dest_dir/$(basename "$src")"/
    else
      cp -R "$src" "$dest_dir/" 2>/dev/null || true
    fi
  fi
}

# Expand globs safely: if glob doesn't match, nothing is copied.
copy_glob() {
  local pattern="$1" dest_dir="$2" max_mb="$3"
  shopt -s nullglob dotglob
  local matches=( $pattern )
  shopt -u nullglob dotglob
  for m in "${matches[@]}"; do copy_path "$m" "$dest_dir" "$max_mb"; done
}

split_colon_list() {
  local s="${1:-}"
  [[ -n "$s" ]] || return 0
  local IFS=":"
  read -r -a _parts <<< "$s"
  for p in "${_parts[@]}"; do [[ -n "$p" ]] && echo "$p"; done
}
OUT_ARG="${1:-}"
DIAG_ROOT="${E2E_DIAG_ROOT:-.}"
DIAG_NAME="${E2E_DIAG_NAME:-e2e-diagnostics-$(ts_utc)}"
MAX_MB="${E2E_MAX_FILE_MB:-200}"

OUT_DIR="${OUT_ARG:-$DIAG_ROOT/$DIAG_NAME}"
mkdir -p "$OUT_DIR"/{logs,reports,media,metadata}

log "Writing diagnostics to: $OUT_DIR"

# Common defaults (copy only if present)
DEFAULT_LOGS=(
  "logs"
  "**/*.log"
  "npm-debug.log"
  "yarn-error.log"
  "pnpm-debug.log"
  "playwright/.cache/ms-playwright/*.log"
)
DEFAULT_REPORTS=(
  "test-results"
  "playwright-report"
  "coverage"
  "junit.xml"
  "**/junit*.xml"
  "**/test-results*.xml"
  "**/test-report*.xml"
  "**/cypress/results*"
)
DEFAULT_MEDIA=(
  "cypress/screenshots"
  "cypress/videos"
  "playwright-report/data"
  "test-results/**/trace.zip"
  "test-results/**/video.*"
  "test-results/**/screenshot.*"
  "test-results/**/screenshots"
)

# Enable ** globs when supported (bash >=4); if not, patterns still work for non-** cases.
shopt -s globstar 2>/dev/null || true
# Copy defaults
for pat in "${DEFAULT_LOGS[@]}"; do copy_glob "$pat" "$OUT_DIR/logs" "$MAX_MB"; done
for pat in "${DEFAULT_REPORTS[@]}"; do copy_glob "$pat" "$OUT_DIR/reports" "$MAX_MB"; done
for pat in "${DEFAULT_MEDIA[@]}"; do copy_glob "$pat" "$OUT_DIR/media" "$MAX_MB"; done

# Copy additional paths from env vars
while IFS= read -r p; do vlog "Copy log path: $p"; copy_path "$p" "$OUT_DIR/logs" "$MAX_MB"; done < <(split_colon_list "${E2E_LOG_PATHS:-}")
while IFS= read -r p; do vlog "Copy report path: $p"; copy_path "$p" "$OUT_DIR/reports" "$MAX_MB"; done < <(split_colon_list "${E2E_REPORT_PATHS:-}")
while IFS= read -r p; do vlog "Copy media path: $p"; copy_path "$p" "$OUT_DIR/media" "$MAX_MB"; done < <(split_colon_list "${E2E_MEDIA_PATHS:-}")
# Metadata
{
  echo "timestamp_utc=$(ts_utc)"
  echo "pwd=$(pwd)"
  echo "user=$(id -un 2>/dev/null || true)"
  echo "uid=$(id -u 2>/dev/null || true)"
  echo "gid=$(id -g 2>/dev/null || true)"
  echo "shell=${SHELL:-}"
  echo "ci=${CI:-}"
  echo "github_run_id=${GITHUB_RUN_ID:-}"
  echo "github_job=${GITHUB_JOB:-}"
  echo "github_sha=${GITHUB_SHA:-}"
  echo "github_ref=${GITHUB_REF:-}"
  echo "runner_os=${RUNNER_OS:-}"
  echo "runner_arch=${RUNNER_ARCH:-}"
} > "$OUT_DIR/metadata/context.txt"

( uname -a || true ) > "$OUT_DIR/metadata/uname.txt" 2>&1
( df -h || true ) > "$OUT_DIR/metadata/df.txt" 2>&1
( free -h || true ) > "$OUT_DIR/metadata/memory.txt" 2>&1

# Tool versions (best-effort)
{
  have node && echo "node: $(node -v 2>/dev/null || true)"
  have npm && echo "npm: $(npm -v 2>/dev/null || true)"
  have pnpm && echo "pnpm: $(pnpm -v 2>/dev/null || true)"
  have yarn && echo "yarn: $(yarn -v 2>/dev/null || true)"
  have python && echo "python: $(python --version 2>&1 || true)"
  have python3 && echo "python3: $(python3 --version 2>&1 || true)"
  have pip && echo "pip: $(pip --version 2>&1 || true)"
  have pip3 && echo "pip3: $(pip3 --version 2>&1 || true)"
} > "$OUT_DIR/metadata/tool-versions.txt" 2>&1

# Git info (if available)
if have git && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ( git status --porcelain=v1 || true ) > "$OUT_DIR/metadata/git-status.txt" 2>&1
  ( git rev-parse HEAD || true ) > "$OUT_DIR/metadata/git-head.txt" 2>&1
  ( git log -1 --oneline --decorate || true ) > "$OUT_DIR/metadata/git-last-commit.txt" 2>&1
fi

# Full environment (sorted) can include secrets; prefer a filtered subset by default.
# If you explicitly want everything, set E2E_INCLUDE_FULL_ENV=1.
if [[ "${E2E_INCLUDE_FULL_ENV:-0}" == "1" ]]; then
  ( printenv | sort ) > "$OUT_DIR/metadata/env.full.txt" 2>/dev/null || true
else
  ( printenv | sort | grep -E '^(CI|GITHUB_|RUNNER_|NODE_|NPM_|PNPM_|YARN_|PLAYWRIGHT_|CYPRESS_|E2E_)' ) \
    > "$OUT_DIR/metadata/env.filtered.txt" 2>/dev/null || true
fi

# Inventory of collected files
if have find; then
  ( cd "$OUT_DIR" && find . -type f -maxdepth 4 -print | sort ) > "$OUT_DIR/metadata/inventory.txt" 2>/dev/null || true
fi

log "Diagnostics collection complete."
echo "$OUT_DIR"
