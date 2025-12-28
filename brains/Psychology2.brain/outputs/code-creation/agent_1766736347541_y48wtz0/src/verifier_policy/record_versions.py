from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

try:
    import importlib.metadata as importlib_metadata  # py3.8+
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore


_JSON_KW = {"ensure_ascii": False, "indent": 2, "sort_keys": True}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_cmd(cmd: List[str], cwd: Optional[Path] = None, timeout_s: float = 2.0) -> Optional[str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        out = (p.stdout or "").strip()
        return out or None
    except Exception:
        return None


def _normalize_dist_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", (name or "").strip()).lower()


def get_git_info(cwd: Optional[Path] = None) -> Dict[str, Any]:
    cwd = Path(cwd) if cwd else None
    head = _safe_cmd(["git", "rev-parse", "HEAD"], cwd=cwd)
    branch = _safe_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    dirty = _safe_cmd(["git", "status", "--porcelain"], cwd=cwd)
    info: Dict[str, Any] = {"head": head, "branch": branch}
    info["is_dirty"] = bool(dirty) if dirty is not None else None
    return info


def get_platform_info() -> Dict[str, Any]:
    return {
        "python": {
            "version": sys.version.replace("\n", " "),
            "version_info": list(sys.version_info),
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
        },
        "os": {
            "platform": sys.platform,
            "name": os.name,
            "machine": platform.machine(),
            "processor": platform.processor(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        },
    }


def get_installed_distributions() -> Dict[str, str]:
    d: Dict[str, str] = {}
    try:
        for dist in importlib_metadata.distributions():
            name = _normalize_dist_name(getattr(dist, "metadata", {}).get("Name", "") if getattr(dist, "metadata", None) else "")
            if not name:
                name = _normalize_dist_name(getattr(dist, "name", "") or "")
            version = getattr(dist, "version", None)
            if name and version:
                d[name] = str(version)
    except Exception:
        pass
    return dict(sorted(d.items(), key=lambda kv: kv[0]))


def get_selected_package_versions(packages: Iterable[str]) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {}
    for p in packages:
        key = _normalize_dist_name(p)
        try:
            out[key] = importlib_metadata.version(p)
        except Exception:
            out[key] = None
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def compute_fingerprint(payload: Mapping[str, Any]) -> str:
    s = json.dumps(payload, **_JSON_KW)
    return sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VersionRecord:
    created_at_utc: str
    platform: Dict[str, Any]
    git: Dict[str, Any]
    env: Dict[str, Any]
    selected_packages: Dict[str, Optional[str]]
    installed_distributions: Dict[str, str]
    fingerprint_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at_utc": self.created_at_utc,
            "platform": self.platform,
            "git": self.git,
            "env": self.env,
            "selected_packages": self.selected_packages,
            "installed_distributions": self.installed_distributions,
            "fingerprint_sha256": self.fingerprint_sha256,
        }


def collect_version_record(
    *,
    project_root: Optional[Path] = None,
    selected_packages: Optional[Iterable[str]] = None,
    include_installed_distributions: bool = True,
    env_keys: Optional[Iterable[str]] = None,
) -> VersionRecord:
    project_root = Path(project_root) if project_root else None
    selected_packages = list(selected_packages) if selected_packages else []
    env_keys = list(env_keys) if env_keys else ["PYTHONHASHSEED", "CUDA_VISIBLE_DEVICES", "TOKENIZERS_PARALLELISM", "OMP_NUM_THREADS"]

    platform_info = get_platform_info()
    git_info = get_git_info(cwd=project_root)
    env_info = {k: os.environ.get(k) for k in env_keys}

    selected = get_selected_package_versions(selected_packages)
    installed = get_installed_distributions() if include_installed_distributions else {}

    payload = {
        "created_at_utc": _utc_now_iso(),
        "platform": platform_info,
        "git": git_info,
        "env": env_info,
        "selected_packages": selected,
        "installed_distributions": installed,
    }
    fp = compute_fingerprint(payload)
    return VersionRecord(
        created_at_utc=payload["created_at_utc"],
        platform=platform_info,
        git=git_info,
        env=env_info,
        selected_packages=selected,
        installed_distributions=installed,
        fingerprint_sha256=fp,
    )


def write_version_record_json(
    output_path: Path,
    *,
    project_root: Optional[Path] = None,
    selected_packages: Optional[Iterable[str]] = None,
    include_installed_distributions: bool = True,
    env_keys: Optional[Iterable[str]] = None,
) -> VersionRecord:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rec = collect_version_record(
        project_root=project_root,
        selected_packages=selected_packages,
        include_installed_distributions=include_installed_distributions,
        env_keys=env_keys,
    )
    output_path.write_text(json.dumps(rec.to_dict(), **_JSON_KW) + "\n", encoding="utf-8")
    return rec
