"""dgpipe.protocols

Lightweight, typed protocols (structural interfaces) used across dgpipe.

These protocols define the minimal contracts for stages, pipelines, runners,
and IO backends so that user extensions can plug in without inheriting from
framework base classes.
"""
from __future__ import annotations

from typing import (
    Any,
    Callable,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
    runtime_checkable,
)

InT = TypeVar("InT")
OutT = TypeVar("OutT")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
@runtime_checkable
class ArtifactStore(Protocol):
    """Minimal IO abstraction for reading/writing pipeline artifacts.

    Implementations may map keys to files, object storage, databases, etc.
    Keys are treated as opaque identifiers (often a relative path).
    """

    def read_bytes(self, key: str) -> bytes: ...
    def write_bytes(self, key: str, data: bytes) -> None: ...
    def exists(self, key: str) -> bool: ...
    def list(self, prefix: str = "") -> Iterable[str]: ...
@runtime_checkable
class Logger(Protocol):
    """Structured-logging compatible callable."""

    def __call__(self, message: str, /, **fields: Any) -> None: ...
@runtime_checkable
class StageContext(Protocol):
    """Context passed to stages.

    The context is intentionally small: stages can use the artifact store for IO,
    a logger for diagnostics, and arbitrary config values.
    """

    artifacts: ArtifactStore
    log: Logger
    config: Mapping[str, Any]
@runtime_checkable
class Stage(Protocol[InT, OutT]):
    """Synchronous stage contract."""

    name: str

    def run(self, ctx: StageContext, data: InT) -> OutT: ...
@runtime_checkable
class AsyncStage(Protocol[InT, OutT]):
    """Asynchronous stage contract."""

    name: str

    async def arun(self, ctx: StageContext, data: InT) -> OutT: ...
@runtime_checkable
class Pipeline(Protocol[InT, OutT]):
    """A pipeline is an executable composition of one or more stages."""

    name: str
    stages: Sequence[object]

    def run(self, ctx: StageContext, data: InT) -> OutT: ...
@runtime_checkable
class Runner(Protocol):
    """Executes pipelines, providing common concerns (retries, metrics, etc.)."""

    def run(self, pipeline: Pipeline[Any, Any], ctx: StageContext, data: Any) -> Any: ...
@runtime_checkable
class Serializer(Protocol[T_contra]):
    """Converts a value into bytes (for ArtifactStore)."""

    content_type: str

    def dumps(self, value: T_contra) -> bytes: ...
@runtime_checkable
class Deserializer(Protocol[T_co]):
    """Converts bytes into a value (from ArtifactStore)."""

    content_type: str

    def loads(self, data: bytes) -> T_co: ...
@runtime_checkable
class Codec(Serializer[T_contra], Deserializer[T_co], Protocol[T_contra, T_co]):
    """Bidirectional serialization protocol."""
@runtime_checkable
class Callback(Protocol):
    """Hook for observing lifecycle events without coupling to implementations."""

    def on_stage_start(self, stage_name: str, *, ctx: StageContext) -> None: ...
    def on_stage_end(self, stage_name: str, *, ctx: StageContext, result: Any) -> None: ...
    def on_stage_error(self, stage_name: str, *, ctx: StageContext, error: BaseException) -> None: ...
def null_logger() -> Logger:
    """Return a no-op logger that matches the Logger protocol."""

    def _log(message: str, /, **fields: Any) -> None:
        return None

    return _log
