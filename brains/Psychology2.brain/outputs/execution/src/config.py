from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _env_str(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def _env_int(key: str, default: int) -> int:
    v = _env_str(key, None)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    v = _env_str(key, None)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    v = _env_str(key, None)
    if v is None:
        return default
    return v.lower() in {"1", "true", "t", "yes", "y", "on"}


def _default_output_dir() -> Path:
    base = Path(_env_str("CITATION_MVP_OUTPUT_DIR", "") or Path.cwd())
    return base / "outputs"


@dataclass(frozen=True)
class Settings:
    # Identity / contact (used by polite APIs)
    contact_email: str = "opensource@example.com"
    user_agent: str = "citation-mvp/0.1 (+https://example.com; mailto:opensource@example.com)"

    # Provider configuration
    unpaywall_email: str = "opensource@example.com"
    openalex_email: str = "opensource@example.com"
    crossref_mailto: str = "opensource@example.com"
    ncbi_tool: str = "citation-mvp"
    ncbi_email: str = "opensource@example.com"
    ncbi_api_key: Optional[str] = None

    # Networking / retries
    timeout_s: float = 20.0
    connect_timeout_s: float = 10.0
    read_timeout_s: float = 20.0
    max_retries: int = 3
    backoff_s: float = 0.8

    # Concurrency / rate limiting
    concurrency: int = 8
    per_host_concurrency: int = 4
    min_interval_s: float = 0.0

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"

    # Output
    output_dir: Path = _default_output_dir()

    @staticmethod
    def from_env() -> "Settings":
        contact_email = _env_str("CONTACT_EMAIL", None) or _env_str("EMAIL", None) or "opensource@example.com"
        ua = _env_str("USER_AGENT", None) or f"citation-mvp/0.1 (mailto:{contact_email})"
        out_dir = Path(_env_str("OUTPUT_DIR", None) or str(_default_output_dir()))
        out_dir.mkdir(parents=True, exist_ok=True)

        return Settings(
            contact_email=contact_email,
            user_agent=ua,
            unpaywall_email=_env_str("UNPAYWALL_EMAIL", contact_email) or contact_email,
            openalex_email=_env_str("OPENALEX_EMAIL", contact_email) or contact_email,
            crossref_mailto=_env_str("CROSSREF_MAILTO", contact_email) or contact_email,
            ncbi_tool=_env_str("NCBI_TOOL", "citation-mvp") or "citation-mvp",
            ncbi_email=_env_str("NCBI_EMAIL", contact_email) or contact_email,
            ncbi_api_key=_env_str("NCBI_API_KEY", None),
            timeout_s=_env_float("HTTP_TIMEOUT_S", 20.0),
            connect_timeout_s=_env_float("HTTP_CONNECT_TIMEOUT_S", 10.0),
            read_timeout_s=_env_float("HTTP_READ_TIMEOUT_S", 20.0),
            max_retries=_env_int("HTTP_MAX_RETRIES", 3),
            backoff_s=_env_float("HTTP_BACKOFF_S", 0.8),
            concurrency=_env_int("CONCURRENCY", 8),
            per_host_concurrency=_env_int("PER_HOST_CONCURRENCY", 4),
            min_interval_s=_env_float("MIN_INTERVAL_S", 0.0),
            host=_env_str("HOST", "127.0.0.1") or "127.0.0.1",
            port=_env_int("PORT", 8000),
            log_level=_env_str("LOG_LEVEL", "info") or "info",
            output_dir=out_dir,
        )


def get_settings() -> Settings:
    return Settings.from_env()
