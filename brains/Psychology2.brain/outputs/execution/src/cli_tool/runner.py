from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Union


Json = Union[None, bool, int, float, str, List["Json"], Dict[str, "Json"]]


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v.lower() in {"1", "true", "t", "yes", "y"}:
            return True
        if v.lower() in {"0", "false", "f", "no", "n"}:
            return False
    raise TypeError(f"Expected bool-like value, got {type(v).__name__}: {v!r}")


def _ensure_float01(x: Any, name: str) -> float:
    try:
        f = float(x)
    except Exception as e:
        raise TypeError(f"{name} must be a float in [0,1], got {x!r}") from e
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"{name} must be in [0,1], got {f!r}")
    return f


@dataclass(frozen=True)
class RunnerConfig:
    risk_threshold: float = 0.5
    decompose_claims: bool = True
    seed: int = 0
    goal: Optional[str] = None
    extra: Dict[str, Json] = field(default_factory=dict)

    def normalized(self) -> Dict[str, Json]:
        base: Dict[str, Json] = {
            "risk_threshold": _ensure_float01(self.risk_threshold, "risk_threshold"),
            "decompose_claims": _as_bool(self.decompose_claims),
            "seed": int(self.seed),
            "goal": self.goal,
            "extra": self.extra or {},
        }
        return base

    def config_hash(self) -> str:
        return _sha256_hex(_canonical_json(self.normalized()))

    def run_id(self) -> str:
        return self.config_hash()[:12]


@dataclass
class RunResult:
    run_id: str
    build_dir: Path
    config_hash: str
    ok: bool
    outputs: Dict[str, Json] = field(default_factory=dict)
    error: Optional[str] = None
    duration_s: float = 0.0


class ArtifactWriter:
    def __init__(self, build_dir: Path):
        self.build_dir = build_dir
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self.build_dir / "run.log"

    def log(self, msg: str) -> None:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        line = f"{ts} {msg}".rstrip() + "\n"
        self._log_path.open("a", encoding="utf-8").write(line)

    def write_manifest(self, manifest: Mapping[str, Json]) -> Path:
        p = self.build_dir / "manifest.json"
        p.write_text(_canonical_json(manifest) + "\n", encoding="utf-8")
        return p

    def write_decisions(self, decisions: Iterable[Mapping[str, Json]]) -> Path:
        p = self.build_dir / "decision_traces.jsonl"
        with p.open("w", encoding="utf-8") as f:
            for d in decisions:
                f.write(_canonical_json(d) + "\n")
        return p

    def write_outputs(self, outputs: Mapping[str, Json]) -> Path:
        p = self.build_dir / "outputs.json"
        p.write_text(_canonical_json(dict(outputs)) + "\n", encoding="utf-8")
        return p


def _project_root_from_file(file_path: Path) -> Path:
    return file_path.resolve().parents[2]


def _build_root(project_root: Path) -> Path:
    return project_root / "runtime" / "_build"


def _preflight(config: RunnerConfig) -> Dict[str, Json]:
    os.environ.setdefault("PYTHONHASHSEED", str(int(config.seed)))
    random.seed(int(config.seed))
    try:
        import numpy as np  # type: ignore
        np.random.seed(int(config.seed))
    except Exception:
        pass
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "py_hash_seed": os.environ.get("PYTHONHASHSEED"),
    }


def run_pipeline(
    pipeline: Callable[[RunnerConfig, Path, ArtifactWriter], Tuple[Mapping[str, Json], Iterable[Mapping[str, Json]]]],
    config: RunnerConfig,
    project_root: Optional[Path] = None,
) -> RunResult:
    project_root = project_root or _project_root_from_file(Path(__file__))
    b_root = _build_root(project_root)
    b_root.mkdir(parents=True, exist_ok=True)

    cfg_n = config.normalized()
    cfg_hash = config.config_hash()
    run_id = config.run_id()
    build_dir = (b_root / run_id).resolve()

    if b_root.resolve() not in build_dir.parents and build_dir != b_root.resolve():
        raise RuntimeError("Build dir must be within runtime/_build")

    env_info = _preflight(config)
    aw = ArtifactWriter(build_dir)
    aw.log(f"run_id={run_id} config_hash={cfg_hash}")

    started = time.time()
    ok = True
    err = None
    outputs: Dict[str, Json] = {}
    decisions: List[Mapping[str, Json]] = []
    try:
        out_map, decision_iter = pipeline(config, build_dir, aw)
        outputs = dict(out_map)
        decisions = list(decision_iter)
    except Exception as e:
        ok = False
        err = f"{type(e).__name__}: {e}"
        aw.log(f"ERROR {err}")

    duration = time.time() - started
    manifest: Dict[str, Json] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "config_hash": cfg_hash,
        "config": cfg_n,
        "build_dir": str(build_dir),
        "env": env_info,
        "ok": ok,
        "error": err,
        "duration_s": round(duration, 6),
        "artifacts": {
            "log": "run.log",
            "manifest": "manifest.json",
            "decision_traces": "decision_traces.jsonl",
            "outputs": "outputs.json",
        },
    }
    aw.write_outputs(outputs)
    aw.write_decisions(decisions)
    aw.write_manifest(manifest)
    aw.log(f"done ok={ok} duration_s={manifest['duration_s']}")

    return RunResult(
        run_id=run_id,
        build_dir=build_dir,
        config_hash=cfg_hash,
        ok=ok,
        outputs=outputs,
        error=err,
        duration_s=float(manifest["duration_s"]),
    )
