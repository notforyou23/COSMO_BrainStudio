"""Deterministic-run policy for benchmarks.

Sets fixed RNG seeds across common frameworks and provides a context manager
to enforce/restore deterministic settings for reproducible CI runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional
import os
import random
def _maybe_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None
def _set_env_if_unset(key: str, value: str) -> None:
    if os.environ.get(key) is None:
        os.environ[key] = value
@dataclass(frozen=True)
class DeterminismPolicy:
    seed: int = 0
    enforce_torch_determinism: bool = True
    enforce_tf_determinism: bool = True
    strict: bool = True

    def apply(self) -> None:
        """Apply deterministic settings for this process."""
        random.seed(self.seed)
        np = _maybe_import("numpy")
        if np is not None:
            np.random.seed(self.seed)

        # Best-effort env vars; some must be set before import/initialization.
        _set_env_if_unset("PYTHONHASHSEED", str(self.seed))
        _set_env_if_unset("CUBLAS_WORKSPACE_CONFIG", ":4096:8")  # for some CUDA libs
        if self.enforce_tf_determinism:
            _set_env_if_unset("TF_DETERMINISTIC_OPS", "1")

        torch = _maybe_import("torch")
        if torch is not None:
            try:
                torch.manual_seed(self.seed)
                if hasattr(torch, "cuda") and torch.cuda.is_available():
                    torch.cuda.manual_seed_all(self.seed)
                if self.enforce_torch_determinism and hasattr(torch, "use_deterministic_algorithms"):
                    torch.use_deterministic_algorithms(True)
                if hasattr(torch, "backends") and hasattr(torch.backends, "cudnn"):
                    torch.backends.cudnn.deterministic = True
                    torch.backends.cudnn.benchmark = False
            except Exception:
                if self.strict:
                    raise

        tf = _maybe_import("tensorflow")
        if tf is not None:
            try:
                tf.random.set_seed(self.seed)
                if self.enforce_tf_determinism and hasattr(tf.config.experimental, "enable_op_determinism"):
                    tf.config.experimental.enable_op_determinism()
            except Exception:
                if self.strict:
                    raise

    def validate(self) -> None:
        """Validate that key RNGs are seeded as expected."""
        errors = []
        # python/random
        probe = random.Random(self.seed).randint(0, 2**31 - 1)
        got = random.randint(0, 2**31 - 1)
        if got != probe:
            errors.append(f"random mismatch: expected {probe}, got {got}")

        # numpy
        np = _maybe_import("numpy")
        if np is not None:
            try:
                exp = np.random.RandomState(self.seed).randint(0, 2**31 - 1)
                got_np = np.random.randint(0, 2**31 - 1)
                if int(got_np) != int(exp):
                    errors.append(f"numpy mismatch: expected {exp}, got {got_np}")
            except Exception as e:
                errors.append(f"numpy validate error: {e}")

        if errors:
            msg = "DeterminismPolicy validation failed:\n" + "\n".join(errors)
            if self.strict:
                raise RuntimeError(msg)
            else:
                print(msg)
@contextmanager
def deterministic_run(seed: int = 0, strict: bool = True) -> Iterator[DeterminismPolicy]:
    """Context manager that applies determinism and restores RNG states."""
    np = _maybe_import("numpy")
    torch = _maybe_import("torch")

    py_state = random.getstate()
    np_state = np.random.get_state() if np is not None else None
    torch_cpu = torch.get_rng_state() if torch is not None else None
    torch_cuda = None
    if torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available():
        try:
            torch_cuda = torch.cuda.get_rng_state_all()
        except Exception:
            torch_cuda = None

    policy = DeterminismPolicy(seed=seed, strict=strict)
    policy.apply()
    policy.validate()
    try:
        yield policy
    finally:
        random.setstate(py_state)
        if np is not None and np_state is not None:
            np.random.set_state(np_state)
        if torch is not None and torch_cpu is not None:
            try:
                torch.set_rng_state(torch_cpu)
                if torch_cuda is not None and hasattr(torch, "cuda") and torch.cuda.is_available():
                    torch.cuda.set_rng_state_all(torch_cuda)
            except Exception:
                if strict:
                    raise
def snapshot_determinism() -> Dict[str, Any]:
    """Return a small snapshot useful for debug logs/CI reports."""
    out: Dict[str, Any] = {"PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED")}
    np = _maybe_import("numpy")
    if np is not None:
        out["numpy_version"] = getattr(np, "__version__", None)
    torch = _maybe_import("torch")
    if torch is not None:
        out["torch_version"] = getattr(torch, "__version__", None)
        try:
            out["torch_cuda_available"] = bool(torch.cuda.is_available())
        except Exception:
            out["torch_cuda_available"] = None
    tf = _maybe_import("tensorflow")
    if tf is not None:
        out["tensorflow_version"] = getattr(tf, "__version__", None)
    return out
