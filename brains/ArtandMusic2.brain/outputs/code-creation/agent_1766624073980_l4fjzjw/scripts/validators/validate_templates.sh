#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUTS_DIR="${OUTPUTS_DIR:-$ROOT_DIR/outputs}"
TEMPLATES_DIR="${TEMPLATES_DIR:-$OUTPUTS_DIR/templates}"

ts() { date +"%Y-%m-%dT%H:%M:%S%z"; }
info() { printf "[%s] INFO  %s\n" "$(ts)" "$*" >&2; }
warn() { printf "[%s] WARN  %s\n" "$(ts)" "$*" >&2; }
err()  { printf "[%s] ERROR %s\n" "$(ts)" "$*" >&2; }
die()  { err "$*"; exit 2; }

DEFAULT_REQUIRED_TEMPLATES=(
  "REPORT.md.j2"
  "SECTION.md.j2"
  "TABLE.md.j2"
)

read_required_templates() {
  local -a req=()
  local manifest="$TEMPLATES_DIR/manifest.json"
  local listfile="${REQUIRED_TEMPLATES_FILE:-}"

  if [[ -n "${REQUIRED_TEMPLATES:-}" ]]; then
    # shellcheck disable=SC2206
    req+=(${REQUIRED_TEMPLATES})
    printf "%s\n" "${req[@]}"
    return 0
  fi

  if [[ -n "$listfile" && -f "$listfile" ]]; then
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      [[ "$line" =~ ^[[:space:]]*# ]] && continue
      req+=("$line")
    done < "$listfile"
    if (( ${#req[@]} > 0 )); then
      printf "%s\n" "${req[@]}"
      return 0
    fi
  fi

  if [[ -f "$manifest" ]] && command -v python3 >/dev/null 2>&1; then
    mapfile -t req < <(python3 - <<'PY' 2>/dev/null || true
import json, sys
p = sys.argv[1]
try:
  with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)
  req = data.get("required") or data.get("required_templates") or []
  if isinstance(req, list):
    for x in req:
      if isinstance(x, str) and x.strip():
        print(x.strip())
except Exception:
  pass
PY
"$manifest")
    if (( ${#req[@]} > 0 )); then
      printf "%s\n" "${req[@]}"
      return 0
    fi
  fi

  printf "%s\n" "${DEFAULT_REQUIRED_TEMPLATES[@]}"
}

main() {
  if [[ ! -d "$OUTPUTS_DIR" ]]; then
    die "Outputs directory not found: $OUTPUTS_DIR (set OUTPUTS_DIR to override)."
  fi
  if [[ ! -d "$TEMPLATES_DIR" ]]; then
    die "Templates directory not found: $TEMPLATES_DIR (expected under outputs)."
  fi

  mapfile -t required < <(read_required_templates)
  if (( ${#required[@]} == 0 )); then
    die "No required templates defined. Set REQUIRED_TEMPLATES or create $TEMPLATES_DIR/manifest.json with {\"required\": [...]}."
  fi

  local -a missing=() empty=() ok=()
  local t path
  for t in "${required[@]}"; do
    t="${t#./}"
    path="$TEMPLATES_DIR/$t"
    if [[ ! -e "$path" ]]; then
      missing+=("$t")
      continue
    fi
    if [[ ! -f "$path" ]]; then
      missing+=("$t (not a file)")
      continue
    fi
    if [[ ! -s "$path" ]]; then
      empty+=("$t")
      continue
    fi
    ok+=("$t")
  done

  if (( ${#missing[@]} > 0 || ${#empty[@]} > 0 )); then
    err "Template validation failed for $TEMPLATES_DIR"
    if (( ${#missing[@]} > 0 )); then
      err "Missing required template files:"
      for t in "${missing[@]}"; do err "  - $t"; done
    fi
    if (( ${#empty[@]} > 0 )); then
      err "Empty required template files (must be non-empty):"
      for t in "${empty[@]}"; do err "  - $t"; done
    fi
    err "Define required templates via REQUIRED_TEMPLATES (space-separated) or REQUIRED_TEMPLATES_FILE, or by creating $TEMPLATES_DIR/manifest.json."
    exit 2
  fi

  info "Template validation passed (${#ok[@]} files)."
}

main "$@"
