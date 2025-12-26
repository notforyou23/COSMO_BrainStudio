"""I/O helpers for qg_bench.

This module focuses on deterministic, stable serialization so benchmark outputs
can be compared and hashed reliably across environments.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union
PathLike = Union[str, Path]


def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent
def load_schema(path: Optional[PathLike] = None) -> Dict[str, Any]:
    """Load the benchmark results schema.json.

    If *path* is None, loads qg_bench/schema.json bundled with the package.
    """
    schema_path = Path(path) if path is not None else _pkg_dir() / "schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))
def iter_jsonl(path: PathLike) -> Iterator[Dict[str, Any]]:
    """Yield records from a JSONL file.

    Empty/whitespace-only lines are skipped. Raises ValueError with line context
    on invalid JSON.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {i} of {p}: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"Expected object on line {i} of {p}, got {type(obj).__name__}")
            yield obj
def read_jsonl(path: PathLike, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Read a JSONL dataset into memory."""
    out: List[Dict[str, Any]] = []
    for rec in iter_jsonl(path):
        out.append(rec)
        if limit is not None and len(out) >= limit:
            break
    return out
def canonical_dumps(obj: Any) -> str:
    """Deterministic JSON serialization used for hashing and output.

    Notes:
      - sort_keys=True ensures stable key ordering
      - separators removes whitespace differences
      - ensure_ascii=False preserves UTF-8 (hash is over UTF-8 bytes)
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def _hash_payload(payload: Any) -> str:
    return sha256(canonical_dumps(payload).encode("utf-8")).hexdigest()
@dataclass(frozen=True)
class HashBlock:
    algorithm: str
    value: str
    canonicalization: str = "json/sort_keys,separators=(',',':'),utf-8"

    def to_dict(self) -> Dict[str, str]:
        return {
            "algorithm": self.algorithm,
            "value": self.value,
            "canonicalization": self.canonicalization,
        }
def write_results_json(
    path: PathLike,
    results_obj: Dict[str, Any],
    *,
    extra_metadata: Optional[Dict[str, Any]] = None,
    include_hash: bool = True,
) -> Dict[str, Any]:
    """Write standardized results JSON with stable ordering and a hash block.

    The returned dict is the exact object written to disk.

    Hashing rule:
      - The hash is computed over the full output object *excluding* the "hash"
        field itself (if present), using canonical_dumps().
    """
    out: Dict[str, Any] = dict(results_obj)
    if extra_metadata:
        md = dict(out.get("metadata") or {})
        md.update(extra_metadata)
        out["metadata"] = md

    if include_hash:
        to_hash = dict(out)
        to_hash.pop("hash", None)
        out["hash"] = HashBlock(algorithm="sha256", value=_hash_payload(to_hash)).to_dict()

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(canonical_dumps(out) + "\n", encoding="utf-8")
    return out
