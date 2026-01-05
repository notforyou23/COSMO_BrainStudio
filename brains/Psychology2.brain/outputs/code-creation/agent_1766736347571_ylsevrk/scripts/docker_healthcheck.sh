#!/usr/bin/env sh
set -eu

log() { printf '%s\n' "$*" >&2; }
fail() { log "HEALTHCHECK_FAIL: $*"; exit 1; }

need_cmd() {
  cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    fail "missing required command: $cmd"
  fi
}

check_write_dir() {
  d="$1"
  [ -d "$d" ] || fail "directory missing: $d"
  f="$d/.healthcheck_write_$$"
  ( : >"$f" ) 2>/dev/null || fail "not writable: $d"
  rm -f "$f" 2>/dev/null || true
}

http_get() {
  url="$1"
  timeout_s="${2:-5}"

  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time "$timeout_s" "$url" >/dev/null
    return $?
  fi

  if command -v wget >/dev/null 2>&1; then
    wget -q -T "$timeout_s" -O /dev/null "$url" >/dev/null 2>&1
    return $?
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$url" "$timeout_s" <<'PY' >/dev/null
import sys, urllib.request, socket
url = sys.argv[1]; timeout = float(sys.argv[2])
req = urllib.request.Request(url, headers={"User-Agent":"docker-healthcheck"})
with urllib.request.urlopen(req, timeout=timeout) as r:
    if getattr(r, "status", 200) >= 400:
        raise SystemExit(2)
PY
    return $?
  fi

  fail "no http client available (need curl/wget/python3) for URL check: $url"
}

log "HEALTHCHECK_START"

need_cmd sh
need_cmd ls
need_cmd uname
need_cmd df
need_cmd awk
need_cmd sed
need_cmd grep

if command -v bash >/dev/null 2>&1; then :; else log "WARN: bash not found (ok for POSIX sh-only images)"; fi
if command -v python3 >/dev/null 2>&1; then :; else log "WARN: python3 not found"; fi

check_write_dir "${TMPDIR:-/tmp}"
check_write_dir "${WORKDIR:-$(pwd)}"

df_out="$(df -P "${WORKDIR:-$(pwd)}" 2>/dev/null | awk 'NR==2{print $4}')"
[ -n "${df_out:-}" ] || log "WARN: unable to read free disk blocks for workdir"

if [ -r /proc/meminfo ]; then
  mem_kb="$(awk '/MemAvailable:/{print $2}' /proc/meminfo 2>/dev/null || true)"
  [ -n "${mem_kb:-}" ] || mem_kb="$(awk '/MemFree:/{print $2}' /proc/meminfo 2>/dev/null || true)"
  [ -n "${mem_kb:-}" ] || log "WARN: unable to read memory info"
fi

if [ "${HEALTHCHECK_URLS:-}" != "" ]; then
  IFS=','; set -- $HEALTHCHECK_URLS; unset IFS
  for url in "$@"; do
    url="$(printf '%s' "$url" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
    [ -n "$url" ] || continue
    log "CHECK_URL: $url"
    http_get "$url" "${HEALTHCHECK_URL_TIMEOUT_S:-5}" || fail "url check failed: $url"
  done
fi

if [ "${HEALTHCHECK_EXTRA_CMD:-}" != "" ]; then
  log "RUN_EXTRA_CMD"
  sh -lc "$HEALTHCHECK_EXTRA_CMD" >/dev/null 2>&1 || fail "extra cmd failed"
fi

log "HEALTHCHECK_OK"
exit 0
