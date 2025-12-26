"""Deterministic policy shared by benchmark runner and comparator.

This module centralizes two pieces of determinism:
1) Seed setting across common RNGs (random / numpy / torch when available).
2) Canonical JSON serialization (stable key ordering + stable float formatting).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import random
from typing import Any, Optional, Union, Callable
def set_global_determinism(seed: int) -> None:
    """Best-effort deterministic seeding across common libraries.

    Note: PYTHONHASHSEED must be set before interpreter start to fully take
    effect. We still set it here for subprocesses and for documentation.
    """
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)

    # numpy
    try:
        import numpy as np  # type: ignore
        np.random.seed(seed)
    except Exception:
        pass

    # torch
    try:
        import torch  # type: ignore
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        # Best-effort deterministic behavior.
        try:
            torch.use_deterministic_algorithms(True)
        except Exception:
            pass
        try:
            import torch.backends.cudnn as cudnn  # type: ignore
            cudnn.deterministic = True
            cudnn.benchmark = False
        except Exception:
            pass
    except Exception:
        pass
class CanonicalJSONEncoder(json.JSONEncoder):
    """JSON encoder with stable float formatting and key ordering."""

    def __init__(
        self,
        *,
        float_format: Union[str, Callable[[float], str]] = ".12g",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._float_format = float_format

    def iterencode(self, o: Any, _one_shot: bool = False):
        # Inspired by CPython's json.encoder, but with a custom floatstr.
        if isinstance(self._float_format, str):
            def _fmt(x: float) -> str:
                # Normalize negative zero.
                if x == 0.0:
                    x = 0.0
                s = format(x, self._float_format)
                # Ensure JSON number validity (no NaN/Infinity).
                if s in {"nan", "NaN", "inf", "Inf", "-inf", "-Inf"}:
                    raise ValueError("Out of range float values are not JSON compliant")
                return s
        else:
            _fmt = self._float_format

        def floatstr(
            o: float,
            allow_nan: bool = self.allow_nan,
            _repr: Any = float.__repr__,
        ) -> str:
            # We ignore _repr and use the deterministic formatter.
            if not allow_nan and (o != o or o in (float("inf"), float("-inf"))):
                raise ValueError("Out of range float values are not JSON compliant")
            return _fmt(float(o))

        from json.encoder import _make_iterencode  # type: ignore

        _iterencode = _make_iterencode(
            markers={},
            _default=self.default,
            _encoder=json.encoder.encode_basestring_ascii if self.ensure_ascii else json.encoder.encode_basestring,
            _indent=self.indent,
            _floatstr=floatstr,
            _key_separator=self.key_separator,
            _item_separator=self.item_separator,
            _sort_keys=self.sort_keys,
            _skipkeys=self.skipkeys,
            _one_shot=_one_shot,
        )
        return _iterencode(o, 0)
def dumps_canonical(
    data: Any,
    *,
    float_format: Union[str, Callable[[float], str]] = ".12g",
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> str:
    """Serialize *data* to canonical JSON with stable formatting."""
    return json.dumps(
        data,
        cls=CanonicalJSONEncoder,
        float_format=float_format,
        sort_keys=sort_keys,
        ensure_ascii=ensure_ascii,
        separators=(",", ":"),
        allow_nan=False,
    )


def dump_canonical_bytes(
    data: Any,
    *,
    float_format: Union[str, Callable[[float], str]] = ".12g",
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> bytes:
    return dumps_canonical(
        data, float_format=float_format, sort_keys=sort_keys, ensure_ascii=ensure_ascii
    ).encode("utf-8")
@dataclass(frozen=True)
class DeterminismPolicy:
    """Single source of truth for deterministic benchmark behavior."""

    seed: int = 0
    float_format: Union[str, Callable[[float], str]] = ".12g"
    sort_keys: bool = True
    ensure_ascii: bool = False

    def apply(self) -> None:
        set_global_determinism(self.seed)

    def dumps(self, data: Any) -> str:
        return dumps_canonical(
            data,
            float_format=self.float_format,
            sort_keys=self.sort_keys,
            ensure_ascii=self.ensure_ascii,
        )

    def dump_bytes(self, data: Any) -> bytes:
        return self.dumps(data).encode("utf-8")
