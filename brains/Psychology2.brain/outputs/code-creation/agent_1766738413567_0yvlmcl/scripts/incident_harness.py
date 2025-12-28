from __future__ import annotations
import hashlib, json, os, platform, shlex, subprocess, sys, time, uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

def utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _safe_text(b: Union[bytes, str, None]) -> str:
    if b is None: return ""
    if isinstance(b, str): return b
    try: return b.decode("utf-8", "replace")
    except Exception: return repr(b)

def _sha256_short(s: str, n: int = 16) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:n]

def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def _write_text(path: Path, text: str) -> None:
    _ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")

def _write_json(path: Path, obj: Any) -> None:
    _write_text(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")

def run_cmd(cmd: Union[str, Sequence[str]], *, timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    if isinstance(cmd, str):
        argv = shlex.split(cmd)
    else:
        argv = list(cmd)
    t0 = time.time()
    try:
        cp = subprocess.run(argv, capture_output=True, text=False, timeout=timeout, env=env)
        out, err, rc = _safe_text(cp.stdout), _safe_text(cp.stderr), int(cp.returncode)
    except subprocess.TimeoutExpired as e:
        out, err, rc = _safe_text(getattr(e, "stdout", b"")), _safe_text(getattr(e, "stderr", b"")), 124
    except FileNotFoundError as e:
        out, err, rc = "", f"{type(e).__name__}: {e}", 127
    dt = time.time() - t0
    return {"ts_utc": utc_ts(), "cmd": argv, "seconds": round(dt, 6), "returncode": rc, "stdout": out, "stderr": err}

@dataclass
class IncidentResult:
    signature: str
    incident_dir: Path
    returncode: Optional[int] = None
    note: str = ""

class IncidentHarness:
    def __init__(self, root: Union[str, Path] = "runtime/_build/incident_reports", *, prefix: str = "incident") -> None:
        base = Path(root)
        if not base.is_absolute():
            base = (Path.cwd() / base).resolve()
        self.root = _ensure_dir(base)
        self.incident_id = f"{prefix}_{time.strftime('%Y%m%d_%H%M%S', time.gmtime())}Z_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        self.dir = _ensure_dir(self.root / self.incident_id)
        self.artifacts = _ensure_dir(self.dir / "artifacts")
        self._events: List[Dict[str, Any]] = []
        self._write_meta()

    def _write_meta(self) -> None:
        _write_json(self.dir / "meta.json", {"created_utc": utc_ts(), "incident_id": self.incident_id, "cwd": str(Path.cwd())})

    def log_event(self, kind: str, **fields: Any) -> None:
        ev = {"ts_utc": utc_ts(), "kind": kind, **fields}
        self._events.append(ev)
        _write_json(self.dir / "events.json", self._events)

    def write_artifact(self, rel: str, text: str) -> Path:
        p = self.artifacts / rel
        _write_text(p, text)
        return p

    def write_artifact_json(self, rel: str, obj: Any) -> Path:
        p = self.artifacts / rel
        _write_json(p, obj)
        return p

    def record_env(self) -> None:
        env = dict(os.environ)
        for k in list(env.keys()):
            if any(s in k.upper() for s in ("TOKEN", "SECRET", "PASSWORD", "KEY")):
                env[k] = "<redacted>"
        self.write_artifact_json("env.json", env)

    def record_versions(self) -> None:
        info = {
            "ts_utc": utc_ts(),
            "python": {"executable": sys.executable, "version": sys.version, "prefix": sys.prefix},
            "platform": {"system": platform.system(), "release": platform.release(), "version": platform.version(), "machine": platform.machine()},
        }
        self.write_artifact_json("versions.json", info)

    def record_docker(self) -> None:
        diags: Dict[str, Any] = {"ts_utc": utc_ts()}
        for name, cmd in [
            ("docker_version", ["docker", "version"]),
            ("docker_info", ["docker", "info"]),
            ("docker_ps", ["docker", "ps", "-a"]),
            ("docker_images", ["docker", "images", "--digests"]),
        ]:
            diags[name] = run_cmd(cmd, timeout=30)
        self.write_artifact_json("docker_diagnostics.json", diags)

    def record_container(self, container_id: str) -> None:
        data: Dict[str, Any] = {"ts_utc": utc_ts(), "container_id": container_id}
        data["inspect"] = run_cmd(["docker", "inspect", container_id], timeout=30)
        data["logs"] = run_cmd(["docker", "logs", "--timestamps", container_id], timeout=30)
        self.write_artifact_json(f"docker_container_{container_id}.json", data)

    def run_and_capture(self, name: str, cmd: Union[str, Sequence[str]], *, timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        res = run_cmd(cmd, timeout=timeout, env=env)
        self.write_artifact_json(f"cmd_{name}.json", res)
        tail = lambda s: "\n".join(s.splitlines()[-200:])
        self.write_artifact(f"cmd_{name}.stdout.txt", tail(res.get("stdout", "")))
        self.write_artifact(f"cmd_{name}.stderr.txt", tail(res.get("stderr", "")))
        self.log_event("cmd", name=name, returncode=res.get("returncode"), seconds=res.get("seconds"), cmd=res.get("cmd"))
        return res

    def compute_signature(self, *, returncode: Optional[int] = None, exc: Optional[BaseException] = None, stdout: str = "", stderr: str = "", extra: Optional[Dict[str, Any]] = None) -> str:
        payload = {
            "rc": returncode,
            "exc": type(exc).__name__ if exc else None,
            "stdout_tail": "\n".join(stdout.splitlines()[-50:]),
            "stderr_tail": "\n".join(stderr.splitlines()[-50:]),
            "extra": extra or {},
        }
        self.write_artifact_json("signature_payload.json", payload)
        return _sha256_short(json.dumps(payload, sort_keys=True))

    def fail_fast(self, signature: str, *, returncode: Optional[int] = None, note: str = "") -> None:
        self.write_artifact_json("failure.json", {"ts_utc": utc_ts(), "signature": signature, "returncode": returncode, "note": note})
        raise RuntimeError(f"INCIDENT_SIGNATURE={signature} incident_dir={self.dir} returncode={returncode} {note}".strip())
