"""Deterministic hashing utilities.

This module provides small helpers used by the CLI to compute stable SHA-256
hashes for inputs (schema/dataset/config) and for the produced results, and to
assemble a metadata block that can be embedded in the standardized output JSON.

Design goals:
- deterministic across runs given identical inputs
- no wall-clock timestamps or random values
- stable JSON canonicalization (sorted keys, compact separators)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from typing import Any, Dict, Mapping, Optional, Union
def _normalize_newlines(data: bytes) -> bytes:
    """Normalize CRLF/CR newlines to LF to improve cross-platform stability."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_bytes(data: bytes) -> str:
    """Return a lowercase hex SHA-256 digest for *data*."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str, *, encoding: str = "utf-8") -> str:
    """Hash text after encoding with *encoding*."""
    return sha256_bytes(text.encode(encoding))
def canonical_json_dumps(obj: Any) -> str:
    """Deterministically serialize *obj* as JSON.

    Uses sorted keys and compact separators. This is sufficient for stable
    hashing within this project. (If you need RFC 8785 JCS, extend here.)
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def hash_json_obj(obj: Any) -> str:
    """Hash a JSON-serializable object via canonical JSON."""
    return sha256_text(canonical_json_dumps(obj))
def hash_file(path: Union[str, Path]) -> str:
    """Hash a file's bytes with normalized newlines."""
    p = Path(path)
    data = _normalize_newlines(p.read_bytes())
    return sha256_bytes(data)


def hash_text_file(path: Union[str, Path], *, encoding: str = "utf-8") -> str:
    """Hash a text file after newline normalization and decoding/encoding."""
    p = Path(path)
    raw = _normalize_newlines(p.read_bytes())
    return sha256_text(raw.decode(encoding), encoding=encoding)
@dataclass(frozen=True)
class Hashes:
    """Container for commonly used hashes in the benchmark output."""

    schema_sha256: str
    dataset_sha256: str
    config_sha256: str
    results_sha256: str

    def asdict(self) -> Dict[str, str]:
        return {
            "schema_sha256": self.schema_sha256,
            "dataset_sha256": self.dataset_sha256,
            "config_sha256": self.config_sha256,
            "results_sha256": self.results_sha256,
        }
def compute_hashes(
    *,
    schema_path: Union[str, Path],
    dataset_path: Union[str, Path],
    config: Optional[Mapping[str, Any]] = None,
    results_obj: Optional[Mapping[str, Any]] = None,
) -> Hashes:
    """Compute SHA-256 hashes for schema/dataset/config/results.

    - schema: hashed as normalized text (JSON schema file)
    - dataset: hashed as normalized bytes (e.g., JSONL)
    - config/results: hashed via canonical JSON serialization
    """
    schema_h = hash_text_file(schema_path)
    dataset_h = hash_file(dataset_path)
    config_h = hash_json_obj(config or {})
    results_h = hash_json_obj(results_obj or {})
    return Hashes(schema_h, dataset_h, config_h, results_h)
def build_metadata(
    *,
    schema_path: Union[str, Path],
    dataset_path: Union[str, Path],
    config: Optional[Mapping[str, Any]] = None,
    results_obj: Optional[Mapping[str, Any]] = None,
    tool: str = "qg_bench",
    tool_version: str = "0.0.0",
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble a deterministic metadata block for benchmark outputs."""
    hashes = compute_hashes(
        schema_path=schema_path,
        dataset_path=dataset_path,
        config=config,
        results_obj=results_obj,
    )
    meta: Dict[str, Any] = {
        "tool": {"name": tool, "version": tool_version},
        "hashing": {
            "algorithm": "sha256",
            "newline_normalization": "crlf/cr->lf",
            "json_canonicalization": "sort_keys,compact_separators,utf8",
        },
        "hashes": hashes.asdict(),
        "inputs": {
            "schema_path": str(Path(schema_path)),
            "dataset_path": str(Path(dataset_path)),
        },
    }
    if extra:
        # Merge in a deterministic way: values are included as provided;
        # callers should ensure *extra* contains only stable data.
        meta["extra"] = json.loads(canonical_json_dumps(dict(extra)))
    return meta
