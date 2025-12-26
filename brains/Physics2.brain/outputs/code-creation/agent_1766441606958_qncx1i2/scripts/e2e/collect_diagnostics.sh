#!/usr/bin/env sh
# Portable E2E diagnostics collector.
# Gathers common test artifacts (logs, screenshots, reports) and system metadata
# into a single directory suitable for CI artifact upload.
set -eu

timestamp() { date -u +"%Y%m%dT%H%M%SZ" 2>/dev/null || date; }
now="$(timestamp)"
out_dir="${1:-}"
if [ -z "${out_dir}" ]; then
  out_dir="artifacts/e2e-diagnostics-${now}"
fi

workspace="${GITHUB_WORKSPACE:-$(pwd)}"
mkdir -p "${out_dir}"

say() { printf '%s\n' "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

copy_path() {
  src="$1"
  dest="${out_dir}/$2"
  [ -e "${src}" ] || return 0
  mkdir -p "$(dirname "${dest}")"
  # Prefer tar for portability with dirs; fall back to cp.
  if have tar; then
    (cd "$(dirname "${src}")" && tar -cf - "$(basename "${src}")") | (cd "$(dirname "${dest}")" && tar -xf -) 2>/dev/null || true
  else
    cp -R "${src}" "${dest}" 2>/dev/null || true
  fi
}

copy_tree_if_exists() {
  src="$1"
  name="$2"
  [ -e "${src}" ] || return 0
  copy_path "${src}" "${name}"
}

write_file() {
  rel="$1"
  shift
  mkdir -p "$(dirname "${out_dir}/${rel}")"
  # shellcheck disable=SC2129
  : > "${out_dir}/${rel}"
  for cmd in "$@"; do
    printf '\n### %s\n' "${cmd}" >> "${out_dir}/${rel}"
    sh -c "${cmd}" >> "${out_dir}/${rel}" 2>&1 || true
  done
}
say "Collecting diagnostics into: ${out_dir}"
say "Workspace: ${workspace}"

# System + environment metadata
write_file "metadata/system.txt" \
  "date -u || date" \
  "uname -a || true" \
  "id || whoami || true" \
  "pwd" \
  "umask || true" \
  "sh --version 2>/dev/null || true" \
  "env | sort"

write_file "metadata/ci.txt" \
  "printf 'CI=%s\n' \"${CI:-}\"" \
  "printf 'GITHUB_ACTIONS=%s\n' \"${GITHUB_ACTIONS:-}\"" \
  "printf 'RUNNER_OS=%s\n' \"${RUNNER_OS:-}\"" \
  "printf 'RUNNER_ARCH=%s\n' \"${RUNNER_ARCH:-}\"" \
  "printf 'GITHUB_WORKFLOW=%s\n' \"${GITHUB_WORKFLOW:-}\"" \
  "printf 'GITHUB_RUN_ID=%s\n' \"${GITHUB_RUN_ID:-}\"" \
  "printf 'GITHUB_RUN_ATTEMPT=%s\n' \"${GITHUB_RUN_ATTEMPT:-}\"" \
  "printf 'GITHUB_SHA=%s\n' \"${GITHUB_SHA:-}\""

write_file "metadata/resources.txt" \
  "df -h || true" \
  "df -i || true" \
  "ulimit -a || true" \
  "ps -eo pid,ppid,etime,%cpu,%mem,command 2>/dev/null | head -n 200 || true"

# Toolchain versions (best effort)
write_file "metadata/versions.txt" \
  "node --version 2>/dev/null || true" \
  "npm --version 2>/dev/null || true" \
  "pnpm --version 2>/dev/null || true" \
  "yarn --version 2>/dev/null || true" \
  "python --version 2>/dev/null || true" \
  "python3 --version 2>/dev/null || true" \
  "pip --version 2>/dev/null || true" \
  "pip3 --version 2>/dev/null || true" \
  "java -version 2>&1 || true"

# Git context (if available)
if have git && [ -d "${workspace}/.git" ]; then
  (cd "${workspace}" && write_file "metadata/git.txt" \
    "git rev-parse --show-toplevel" \
    "git status --porcelain=v1 -b" \
    "git log -1 --oneline --decorate" \
    "git diff --stat || true")
fi
# Common E2E artifact locations (Playwright/Cypress/WebdriverIO/Jest/JUnit, etc.)
# Copy directories if present.
copy_tree_if_exists "${workspace}/playwright-report" "reports/playwright-report"
copy_tree_if_exists "${workspace}/test-results" "reports/test-results"
copy_tree_if_exists "${workspace}/reports" "reports/reports"
copy_tree_if_exists "${workspace}/allure-results" "reports/allure-results"
copy_tree_if_exists "${workspace}/allure-report" "reports/allure-report"
copy_tree_if_exists "${workspace}/cypress/videos" "media/cypress/videos"
copy_tree_if_exists "${workspace}/cypress/screenshots" "media/cypress/screenshots"
copy_tree_if_exists "${workspace}/screenshots" "media/screenshots"
copy_tree_if_exists "${workspace}/videos" "media/videos"
copy_tree_if_exists "${workspace}/logs" "logs/logs"

# Copy common single files if present.
copy_path "${workspace}/package.json" "metadata/package.json"
copy_path "${workspace}/package-lock.json" "metadata/package-lock.json"
copy_path "${workspace}/pnpm-lock.yaml" "metadata/pnpm-lock.yaml"
copy_path "${workspace}/yarn.lock" "metadata/yarn.lock"
copy_path "${workspace}/pytest.ini" "metadata/pytest.ini"
copy_path "${workspace}/playwright.config.ts" "metadata/playwright.config.ts"
copy_path "${workspace}/playwright.config.js" "metadata/playwright.config.js"
copy_path "${workspace}/cypress.config.ts" "metadata/cypress.config.ts"
copy_path "${workspace}/cypress.config.js" "metadata/cypress.config.js"

# Find and copy common report/log files (bounded to workspace).
# We store them under logs/found and reports/found (preserving relative paths).
if have find; then
  (cd "${workspace}" && \
    find . -type f \( \
      -name "*.log" -o -name "*debug*.log" -o -name "*trace*.zip" -o -name "*.har" -o \
      -name "junit*.xml" -o -name "*junit*.xml" -o -name "test-results*.xml" -o \
      -name "report.html" -o -name "*report*.html" -o -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \
    \) -print 2>/dev/null | while IFS= read -r p; do
      case "${p}" in
        ./node_modules/*|./.git/*) continue ;;
      esac
      ext="${p##*.}"
      dest_base="logs/found"
      case "${ext}" in
        xml|html) dest_base="reports/found" ;;
        png|jpg|jpeg) dest_base="media/found" ;;
      esac
      copy_path "${workspace}/${p#./}" "${dest_base}/${p#./}"
    done)
fi

# Runner logs that are sometimes helpful (best-effort, may not exist).
copy_tree_if_exists "/tmp/playwright" "runner/tmp/playwright"
copy_tree_if_exists "/tmp/cypress" "runner/tmp/cypress"
copy_tree_if_exists "/var/log" "runner/var-log" || true

# Summarize what we collected.
if have find; then
  write_file "metadata/manifest.txt" "cd \"${out_dir}\" && find . -type f -maxdepth 6 -print | sort"
fi

say "Diagnostics collection complete."
printf '%s\n' "${out_dir}" > "${out_dir}/ARTIFACT_ROOT.txt"
