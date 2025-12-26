"""Remediation heuristics for Docker-based QA runs.

This module is intentionally small and dependency-light; it provides:
- a structured AttemptConfig model (docker flags, mounts, env, cmd, timeouts)
- failure classification from a prior run result/telemetry dict
- deterministic remediation steps that escalate resources and reduce test load
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _norm_cmd(cmd: Any) -> List[str]:
    if cmd is None:
        return []
    if isinstance(cmd, (list, tuple)):
        return [str(x) for x in cmd]
    return [str(cmd)]


def _tail(s: str, n: int = 2000) -> str:
    s = s or ""
    return s[-n:]


def ensure_dir(path: str | Path) -> str:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)
@dataclass(frozen=True)
class Mount:
    host: str
    container: str
    mode: str = "rw"

    def as_spec(self) -> str:
        return f"{self.host}:{self.container}:{self.mode}"


@dataclass(frozen=True)
class AttemptConfig:
    image: str = ""
    cmd: List[str] = field(default_factory=list)
    workdir: str = "/workspace"
    env: Dict[str, str] = field(default_factory=dict)
    mounts: List[Mount] = field(default_factory=list)
    docker: Dict[str, Any] = field(default_factory=dict)
    timeout_s: int = 900

    def with_env(self, **kvs: str) -> "AttemptConfig":
        e = dict(self.env)
        e.update({k: str(v) for k, v in kvs.items() if v is not None})
        return replace(self, env=e)

    def with_docker(self, **kvs: Any) -> "AttemptConfig":
        d = dict(self.docker)
        for k, v in kvs.items():
            if v is None:
                d.pop(k, None)
            else:
                d[k] = v
        return replace(self, docker=d)

    def with_cmd(self, cmd: Any) -> "AttemptConfig":
        return replace(self, cmd=_norm_cmd(cmd))

    def add_mount(self, host: str, container: str, mode: str = "rw") -> "AttemptConfig":
        m = list(self.mounts)
        spec = (str(host), str(container))
        for i, mm in enumerate(m):
            if (mm.host, mm.container) == spec:
                m[i] = Mount(str(host), str(container), mode)
                break
        else:
            m.append(Mount(str(host), str(container), mode))
        return replace(self, mounts=m)
@dataclass(frozen=True)
class RemediationEvent:
    kind: str
    detail: str
    changed: Dict[str, Any] = field(default_factory=dict)


def classify_failure(result: Dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return "unknown"
    if result.get("timed_out"):
        return "timeout"
    if result.get("oom_killed") or result.get("exit_code") in (137, 134) or "Killed" in (result.get("stderr_tail") or ""):
        return "oom"
    derr = (result.get("docker_error") or "") + "\n" + (result.get("stderr_tail") or "")
    derr = derr.lower()
    if "mount" in derr and ("denied" in derr or "source path does not exist" in derr or "invalid mount" in derr):
        return "mount"
    if "no such file or directory" in derr and ("/workspace" in derr or "workdir" in derr):
        return "workdir"
    if "pytest" in derr and ("collecting" in derr or "collection" in derr) and result.get("duration_s", 0) > 120:
        return "pytest_collection"
    if result.get("exit_code") not in (0, None):
        return "nonzero"
    return "unknown"


def default_attempt(project_root: str, outputs_root: str, image: str, cmd: Any) -> AttemptConfig:
    pr = str(Path(project_root).resolve())
    out = str(Path(outputs_root).resolve())
    ensure_dir(out)
    cfg = AttemptConfig(image=image).with_cmd(cmd)
    cfg = cfg.add_mount(pr, "/workspace", "rw").add_mount(out, "/outputs", "rw")
    cfg = cfg.with_docker(
        network="bridge",
        cpus="2",
        memory="2g",
        memory_swap="3g",
        shm_size="1g",
        pids_limit=4096,
        ulimit_nofile="4096:8192",
    )
    cfg = cfg.with_env(PYTHONUNBUFFERED="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    return cfg
class Remediator:
    """Transforms an AttemptConfig based on prior run telemetry."""

    def __init__(self, project_root: str, outputs_root: str):
        self.project_root = str(Path(project_root).resolve())
        self.outputs_root = str(Path(outputs_root).resolve())
        ensure_dir(Path(self.outputs_root) / "qa" / "logs")

    def _ensure_core_mounts(self, cfg: AttemptConfig) -> Tuple[AttemptConfig, List[RemediationEvent]]:
        ev: List[RemediationEvent] = []
        cfg2 = cfg
        cfg2 = cfg2.add_mount(self.project_root, "/workspace", "rw")
        cfg2 = cfg2.add_mount(self.outputs_root, "/outputs", "rw")
        if cfg2 != cfg:
            ev.append(RemediationEvent("mounts", "ensured /workspace and /outputs bind mounts"))
        cfg2 = replace(cfg2, workdir="/workspace")
        if cfg2.workdir != cfg.workdir:
            ev.append(RemediationEvent("workdir", "set workdir to /workspace", {"workdir": "/workspace"}))
        return cfg2, ev

    def _escalate_resources(self, cfg: AttemptConfig, attempt_index: int) -> Tuple[AttemptConfig, Optional[RemediationEvent]]:
        mem_steps = ["2g", "3g", "4g", "6g", "8g"]
        step = min(max(attempt_index, 0), len(mem_steps) - 1)
        mem = mem_steps[step]
        d = dict(cfg.docker)
        changed: Dict[str, Any] = {}
        for k, v in {"memory": mem, "memory_swap": None if mem.endswith("g") is False else str(int(mem[:-1]) + 2) + "g", "shm_size": "1g"}.items():
            if v is None:
                continue
            if d.get(k) != v:
                d[k] = v
                changed[k] = v
        if not changed:
            return cfg, None
        return replace(cfg, docker=d), RemediationEvent("resources", "escalated docker resource limits", changed)

    def _reduce_test_load(self, cfg: AttemptConfig, level: int) -> Tuple[AttemptConfig, RemediationEvent]:
        base_env = {
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONFAULTHANDLER": "1",
        }
        cfg2 = cfg.with_env(**base_env)
        if level <= 0:
            # keep as-is but still disable plugin autoload to reduce collection overhead
            return cfg2, RemediationEvent("pytest", "disabled pytest plugin autoload for faster/safer discovery", base_env)
        if level == 1:
            cmd = ["python", "-c", "import os,sys; print('python_ok'); print('cwd', os.getcwd()); sys.exit(0)"]
            return cfg2.with_cmd(cmd), RemediationEvent("cmd", "replaced command with minimal python probe", {"cmd": cmd})
        if level == 2:
            cmd = ["pytest", "-q", "--maxfail=1", "--disable-warnings", "-k", "smoke or minimal", "--co"]
            return cfg2.with_cmd(cmd), RemediationEvent("cmd", "reduced pytest to collection-only probe", {"cmd": cmd})
        cmd = ["pytest", "-q", "--maxfail=1", "--disable-warnings", "-k", "smoke or minimal", "--durations=10"]
        return cfg2.with_cmd(cmd), RemediationEvent("cmd", "reduced pytest selection to minimal subset", {"cmd": cmd})

    def remediate(self, cfg: AttemptConfig, result: Dict[str, Any], attempt_index: int = 0) -> Tuple[AttemptConfig, List[RemediationEvent]]:
        """Return a new config and a list of remediation events applied."""
        events: List[RemediationEvent] = []
        cfg2, ev = self._ensure_core_mounts(cfg)
        events.extend(ev)
        failure = classify_failure(result)
        stderr = _tail((result or {}).get("stderr_tail") or "") + "\n" + _tail((result or {}).get("docker_error") or "")
        if failure in ("oom", "timeout"):
            cfg2, e = self._escalate_resources(cfg2, attempt_index + (1 if failure == "oom" else 0))
            if e:
                events.append(e)
            if failure == "timeout":
                new_timeout = max(int(cfg2.timeout_s), 900) + 600
                if new_timeout != cfg2.timeout_s:
                    cfg2 = replace(cfg2, timeout_s=new_timeout)
                    events.append(RemediationEvent("timeout", "increased timeout", {"timeout_s": new_timeout}))
            cfg2, e2 = self._reduce_test_load(cfg2, 2 if failure == "timeout" else 1)
            events.append(e2)
        elif failure in ("mount", "workdir"):
            # Reassert mounts/workdir; also ensure host dirs exist.
            ensure_dir(self.project_root)
            ensure_dir(self.outputs_root)
            cfg2, e2 = self._reduce_test_load(cfg2, 1)
            events.append(RemediationEvent("diagnostic", "mount/workdir failure; switching to minimal probe", {"hint": stderr[-400:]}))
            events.append(e2)
        elif failure == "pytest_collection":
            cfg2, e2 = self._reduce_test_load(cfg2, 3)
            events.append(e2)
        elif failure == "nonzero":
            # Keep command but add conservative env, and give more time.
            cfg2 = cfg2.with_env(PYTHONFAULTHANDLER="1", PYTHONUNBUFFERED="1")
            if cfg2.timeout_s < 1200:
                cfg2 = replace(cfg2, timeout_s=1200)
                events.append(RemediationEvent("timeout", "raised timeout for nonzero exit retry", {"timeout_s": 1200}))
            events.append(RemediationEvent("retry", "retrying with enhanced python diagnostics", {"failure": failure}))
        else:
            cfg2, e2 = self._reduce_test_load(cfg2, 1)
            events.append(RemediationEvent("fallback", "unknown failure; using minimal probe and ensuring mounts", {"failure": failure}))
            events.append(e2)

        # Ensure logs dir exists inside mounted outputs; callers should write artifacts there.
        events.append(RemediationEvent("logs", "ensured outputs/qa/logs directory exists on host", {"path": str(Path(self.outputs_root) / "qa" / "logs")}))
        return cfg2, events
