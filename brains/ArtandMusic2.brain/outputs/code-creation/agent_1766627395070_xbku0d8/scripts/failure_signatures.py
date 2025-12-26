from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Pattern, Sequence, Tuple


@dataclass(frozen=True)
class FailureSignature:
    name: str
    pattern: Pattern[str]
    reason: str
    retry: bool = True
    env_dump: bool = True

    def matches(self, text: str) -> bool:
        return bool(self.pattern.search(text or ""))


def _rx(p: str) -> Pattern[str]:
    return re.compile(p, re.IGNORECASE | re.MULTILINE)


# Catalog of known unstable/unsupported-environment signatures.
# These are intended to trigger automatic retry + environment dump in QA automation.
SIGNATURES: Tuple[FailureSignature, ...] = (
    FailureSignature(
        name="docker_not_found",
        pattern=_rx(r"\b(docker:\s*command not found|no such file or directory: ['\"]?docker\b)\b"),
        reason="Docker CLI not available in PATH or not installed.",
        retry=False,
        env_dump=True,
    ),
    FailureSignature(
        name="docker_daemon_unreachable",
        pattern=_rx(r"(cannot connect to the docker daemon|is the docker daemon running\?|error during connect: this error may indicate that the docker daemon is not running)"),
        reason="Docker daemon not running or not reachable from this environment.",
        retry=True,
        env_dump=True,
    ),
    FailureSignature(
        name="docker_permission_denied",
        pattern=_rx(r"(permission denied.*docker|got permission denied while trying to connect to the docker daemon socket)"),
        reason="Insufficient permissions to access Docker socket.",
        retry=False,
        env_dump=True,
    ),
    FailureSignature(
        name="docker_desktop_starting",
        pattern=_rx(r"(docker is starting|starting docker|waiting for docker)"),
        reason="Docker Desktop/daemon is still starting; transient.",
        retry=True,
        env_dump=True,
    ),
    FailureSignature(
        name="registry_tls_or_dns",
        pattern=_rx(r"(tls handshake timeout|x509: certificate|certificate signed by unknown authority|temporary failure in name resolution|could not resolve host|no such host)"),
        reason="Transient network/DNS/TLS problems pulling images or contacting registries.",
        retry=True,
        env_dump=True,
    ),
    FailureSignature(
        name="rate_limited",
        pattern=_rx(r"(toomanyrequests:|rate limit exceeded|429 too many requests)"),
        reason="Registry rate limiting; often transient.",
        retry=True,
        env_dump=True,
    ),
    FailureSignature(
        name="no_space_left",
        pattern=_rx(r"(no space left on device|disk quota exceeded|not enough space)"),
        reason="Insufficient disk space; usually not solved by retry.",
        retry=False,
        env_dump=True,
    ),
    FailureSignature(
        name="out_of_memory",
        pattern=_rx(r"(oomkilled|killed process \d+|out of memory|cannot allocate memory|memoryerror)"),
        reason="Process/container killed or failing due to memory pressure.",
        retry=True,
        env_dump=True,
    ),
    FailureSignature(
        name="segfault_or_illegal_instruction",
        pattern=_rx(r"(segmentation fault|sigsegv|illegal instruction|sigill)"),
        reason="Binary incompatibility or unstable runtime; retry may or may not help.",
        retry=True,
        env_dump=True,
    ),
    FailureSignature(
        name="exec_format_error",
        pattern=_rx(r"(exec format error|wrong architecture|platform mismatch)"),
        reason="Binary/image architecture mismatch (e.g., amd64 vs arm64).",
        retry=False,
        env_dump=True,
    ),
    FailureSignature(
        name="glibc_or_loader_missing",
        pattern=_rx(r"(version `glibc_|glibc\.so|ld-linux|not found.*ld\.so|cannot open shared object file)"),
        reason="Missing/unsupported system libraries in runtime.",
        retry=False,
        env_dump=True,
    ),
    FailureSignature(
        name="file_lock_or_resource_busy",
        pattern=_rx(r"(text file busy|resource busy|device or resource busy|unable to acquire lock|deadlock detected)"),
        reason="Transient file lock/resource contention.",
        retry=True,
        env_dump=True,
    ),
    FailureSignature(
        name="interrupted_or_timeout",
        pattern=_rx(r"(timed out|timeout exceeded|context deadline exceeded|read: connection reset by peer|connection reset by peer|broken pipe)"),
        reason="Transient timeout/connection interruption.",
        retry=True,
        env_dump=True,
    ),
)


def find_failure_signatures(text: str, signatures: Sequence[FailureSignature] = SIGNATURES) -> List[FailureSignature]:
    t = text or ""
    return [s for s in signatures if s.matches(t)]


def classify_failure(text: str, signatures: Sequence[FailureSignature] = SIGNATURES) -> Optional[dict]:
    matches = find_failure_signatures(text, signatures)
    if not matches:
        return None
    retry = any(s.retry for s in matches)
    env_dump = any(s.env_dump for s in matches)
    return {
        "retry": bool(retry),
        "env_dump": bool(env_dump),
        "matches": [
            {"name": s.name, "reason": s.reason, "retry": bool(s.retry), "env_dump": bool(s.env_dump)}
            for s in matches
        ],
    }


def should_retry(text: str, signatures: Sequence[FailureSignature] = SIGNATURES) -> bool:
    info = classify_failure(text, signatures)
    return bool(info and info.get("retry"))


def should_env_dump(text: str, signatures: Sequence[FailureSignature] = SIGNATURES) -> bool:
    info = classify_failure(text, signatures)
    return bool(info and info.get("env_dump"))


def summarize_matches(text: str, signatures: Sequence[FailureSignature] = SIGNATURES) -> str:
    info = classify_failure(text, signatures)
    if not info:
        return ""
    parts = []
    for m in info["matches"]:
        parts.append(f'{m["name"]}: {m["reason"]}')
    return "; ".join(parts)
