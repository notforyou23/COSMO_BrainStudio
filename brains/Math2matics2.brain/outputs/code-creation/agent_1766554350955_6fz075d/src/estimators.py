from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Union

import numpy as np


RNG = np.random.Generator
SeedLike = Union[None, int, np.integer, RNG]


def as_rng(rng: SeedLike = None) -> RNG:
    """Return a numpy Generator with deterministic behavior by default.

    - rng is a Generator: returned as-is.
    - rng is an int-like seed: default_rng(seed).
    - rng is None: default_rng(0) (deterministic default).
    """
    if isinstance(rng, np.random.Generator):
        return rng
    if rng is None:
        return np.random.default_rng(0)
    return np.random.default_rng(int(rng))


def sample_mean(x: Sequence[float]) -> float:
    """Standard sample mean estimator."""
    arr = np.asarray(x, dtype=float)
    if arr.size == 0:
        raise ValueError("sample_mean: empty input")
    return float(np.mean(arr))


def _block_slices(n: int, n_blocks: int) -> list[tuple[int, int]]:
    if n_blocks <= 0:
        raise ValueError("n_blocks must be >= 1")
    n_blocks = min(int(n_blocks), n)
    base = n // n_blocks
    rem = n % n_blocks
    out: list[tuple[int, int]] = []
    start = 0
    for b in range(n_blocks):
        size = base + (1 if b < rem else 0)
        end = start + size
        out.append((start, end))
        start = end
    return out


def block_means(
    x: Sequence[float],
    n_blocks: int = 10,
    rng: SeedLike = None,
    shuffle: bool = True,
) -> np.ndarray:
    """Compute per-block means after (optional) deterministic shuffling."""
    arr = np.asarray(x, dtype=float)
    n = int(arr.size)
    if n == 0:
        raise ValueError("block_means: empty input")
    if n_blocks <= 1:
        return np.asarray([np.mean(arr)], dtype=float)

    idx = np.arange(n)
    if shuffle:
        r = as_rng(rng)
        r.shuffle(idx)
    arr = arr[idx]

    means = []
    for s, e in _block_slices(n, n_blocks):
        means.append(float(np.mean(arr[s:e])))
    return np.asarray(means, dtype=float)


def median_of_means(
    x: Sequence[float],
    n_blocks: int = 10,
    rng: SeedLike = None,
    shuffle: bool = True,
) -> float:
    """Median-of-means estimator (robust to heavy tails/outliers).

    Partitions data into n_blocks blocks (as evenly as possible),
    takes the mean within each block, and returns the median of block means.

    Determinism:
      - If shuffle=True, pass an explicit seed/rng for reproducibility.
      - If rng is None, a fixed seed (0) is used by default.
    """
    means = block_means(x, n_blocks=n_blocks, rng=rng, shuffle=shuffle)
    return float(np.median(means))


@dataclass(frozen=True)
class EstimatorSpec:
    """Lightweight descriptor for experiment configuration."""
    name: str
    n_blocks: int = 1
    shuffle: bool = True

    def estimate(self, x: Sequence[float], rng: SeedLike = None) -> float:
        if self.name in {"mean", "sample_mean"}:
            return sample_mean(x)
        if self.name in {"mom", "median_of_means"}:
            return median_of_means(x, n_blocks=self.n_blocks, rng=rng, shuffle=self.shuffle)
        raise ValueError(f"Unknown estimator name: {self.name}")
