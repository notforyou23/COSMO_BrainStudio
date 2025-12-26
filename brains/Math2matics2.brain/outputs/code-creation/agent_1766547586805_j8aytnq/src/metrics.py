"""Utility metrics for stability checks.

- Canonical JSON serialization + SHA256 checksum for deterministic results.json
- Lightweight perceptual/pixel hash for PNG with Hamming-distance tolerance
"""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any, Union
import hashlib
import json
def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (set, frozenset, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    return obj


def canonical_json_dumps(obj: Any) -> str:
    obj = _to_jsonable(obj)
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def json_checksum(obj_or_path: Union[Any, str, Path]) -> str:
    if isinstance(obj_or_path, (str, Path)) and Path(obj_or_path).exists():
        text = Path(obj_or_path).read_text(encoding="utf-8")
        try:
            loaded = json.loads(text)
            payload = canonical_json_dumps(loaded)
        except Exception:
            payload = text
    else:
        payload = canonical_json_dumps(obj_or_path)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
def _load_png_grayscale(path: Union[str, Path]):
    try:
        from PIL import Image  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("PIL/Pillow is required for PNG hashing") from e
    img = Image.open(path)
    try:
        img = img.convert("L")
    finally:
        try:
            img.close()
        except Exception:
            pass
    img = Image.open(path).convert("L")
    return img


def png_ahash_hex(path: Union[str, Path], hash_size: int = 8) -> str:
    """Average-hash of an image; robust to small rendering differences.

    Returns lowercase hex string representing hash_size*hash_size bits.
    """
    if hash_size <= 0:
        raise ValueError("hash_size must be > 0")
    img = _load_png_grayscale(path)
    try:
        # Use a resampling filter that is available across Pillow versions
        try:
            resample = getattr(__import__("PIL.Image", fromlist=["Resampling"]).Image, "Resampling", None)
            if resample is not None:
                filt = resample.LANCZOS
            else:  # pragma: no cover
                filt = 1
        except Exception:  # pragma: no cover
            filt = 1  # Image.LANCZOS/ANTIALIAS numeric fallback
        small = img.resize((hash_size, hash_size), resample=filt)
        pixels = list(small.getdata())
    finally:
        try:
            img.close()
        except Exception:
            pass
    mean = sum(pixels) / float(len(pixels))
    bits = 0
    for p in pixels:
        bits = (bits << 1) | (1 if p >= mean else 0)
    width = (hash_size * hash_size + 3) // 4
    return f"{bits:0{width}x}"


def hamming_distance_hex(a_hex: str, b_hex: str) -> int:
    a = int(a_hex, 16)
    b = int(b_hex, 16)
    return (a ^ b).bit_count()


def png_hash_matches(path: Union[str, Path], baseline_hex: str, max_hamming: int = 0, hash_size: int = 8) -> bool:
    current = png_ahash_hex(path, hash_size=hash_size)
    return hamming_distance_hex(current, baseline_hex) <= int(max_hamming)
