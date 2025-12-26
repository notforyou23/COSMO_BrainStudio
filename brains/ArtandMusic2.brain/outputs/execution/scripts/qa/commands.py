"""QA command construction and environment normalization utilities.

This module defines canonical command specs for containerized and no-container
failsafe execution modes with deterministic defaults across environments.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shlex
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


DEFAULT_OUTPUT_SUBDIR = Path("outputs") / "qa"
DEFAULT_CONTAINER_WORKDIR = Path("/repo")
DEFAULT_CONTAINER_OUTPUT_DIR = Path("/outputs/qa")


@dataclass(frozen=True)
class CommandSpec:
    argv: List[str]
    env: Dict[str, str]
    cwd: Optional[str] = None

    def as_subprocess_kwargs(self) -> Dict[str, object]:
        kw: Dict[str, object] = {"env": self.env}
        if self.cwd:
            kw["cwd"] = self.cwd
        return kw


def _truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def find_repo_root(start: Optional[Path] = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for cur in [p, *p.parents]:
        if (cur / ".git").exists() or (cur / "pyproject.toml").exists() or (cur / "scripts").exists():
            return cur
    return p


def default_outputs_dir(repo_root: Optional[Path] = None) -> Path:
    root = (repo_root or find_repo_root()).resolve()
    return (root / DEFAULT_OUTPUT_SUBDIR).resolve()


def normalize_base_env(
    base: Optional[Mapping[str, str]] = None,
    *,
    outputs_dir: Optional[Path] = None,
    extra: Optional[Mapping[str, str]] = None,
) -> Dict[str, str]:
    env = dict(os.environ if base is None else base)
    env.update(
        {
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": env.get("PYTHONHASHSEED", "0"),
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "FORCE_COLOR": "0",
            "NO_COLOR": env.get("NO_COLOR", "1"),
            "TZ": env.get("TZ", "UTC"),
            "LC_ALL": env.get("LC_ALL", "C.UTF-8"),
            "LANG": env.get("LANG", "C.UTF-8"),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": env.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1"),
        }
    )
    if outputs_dir is not None:
        env["QA_OUTPUT_DIR"] = str(outputs_dir)
        tmp = outputs_dir / "tmp"
        env.setdefault("TMPDIR", str(tmp))
        env.setdefault("TEMP", str(tmp))
        env.setdefault("TMP", str(tmp))
    if extra:
        for k, v in extra.items():
            if v is None:
                env.pop(k, None)
            else:
                env[k] = str(v)
    return env


def shell_join(argv: Sequence[str]) -> str:
    return " ".join(shlex.quote(a) for a in argv)


def canonical_full_qa_argv(python: str = "python") -> List[str]:
    override = os.environ.get("QA_FULL_CMD")
    if override:
        return shlex.split(override)
    return [python, "-m", "pytest", "-q"]


def canonical_failsafe_qa_argv(python: str = "python") -> List[str]:
    override = os.environ.get("QA_FAILSAFE_CMD")
    if override:
        return shlex.split(override)
    return [
        python,
        "-m",
        "pytest",
        "-q",
        "--maxfail=1",
        "--disable-warnings",
        "-k",
        "not slow and not integration and not e2e",
    ]


def canonical_failsafe_timeout_s() -> int:
    v = os.environ.get("QA_FAILSAFE_TIMEOUT_S")
    try:
        return max(10, int(v)) if v else 900
    except Exception:
        return 900


def build_local_command(
    argv: Sequence[str],
    *,
    repo_root: Optional[Path] = None,
    outputs_dir: Optional[Path] = None,
    extra_env: Optional[Mapping[str, str]] = None,
) -> CommandSpec:
    root = (repo_root or find_repo_root()).resolve()
    out = (outputs_dir or default_outputs_dir(root)).resolve()
    env = normalize_base_env(outputs_dir=out, extra=extra_env)
    return CommandSpec(argv=list(argv), env=env, cwd=str(root))


def build_container_command(
    image: str,
    inner_argv: Sequence[str],
    *,
    repo_root: Optional[Path] = None,
    outputs_dir: Optional[Path] = None,
    workdir: Path = DEFAULT_CONTAINER_WORKDIR,
    container_outputs_dir: Path = DEFAULT_CONTAINER_OUTPUT_DIR,
    docker_bin: str = "docker",
    extra_env: Optional[Mapping[str, str]] = None,
) -> CommandSpec:
    root = (repo_root or find_repo_root()).resolve()
    out = (outputs_dir or default_outputs_dir(root)).resolve()

    env = normalize_base_env(outputs_dir=out, extra=extra_env)
    pass_env_keys = [
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "BUILD_NUMBER",
        "RUNNER_OS",
        "QA_OUTPUT_DIR",
        "PYTHONUNBUFFERED",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONHASHSEED",
        "PIP_DISABLE_PIP_VERSION_CHECK",
        "FORCE_COLOR",
        "NO_COLOR",
        "TZ",
        "LC_ALL",
        "LANG",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    ]
    docker_env_args: List[str] = []
    for k in pass_env_keys:
        if k in env:
            docker_env_args += ["-e", f"{k}={env[k]}"]

    argv: List[str] = [
        docker_bin,
        "run",
        "--rm",
        "-t",
        "-v",
        f"{str(root)}:{str(workdir)}",
        "-v",
        f"{str(out)}:{str(container_outputs_dir)}",
        "-w",
        str(workdir),
    ]
    argv += docker_env_args
    argv += [image]
    argv += list(inner_argv)

    # docker itself does not use the normalized env; still return it for logging parity
    return CommandSpec(argv=argv, env=env, cwd=str(root))


def should_force_no_container(env: Optional[Mapping[str, str]] = None) -> bool:
    e = dict(os.environ if env is None else env)
    return _truthy(e.get("QA_NO_CONTAINER")) or _truthy(e.get("NO_CONTAINER")) or _truthy(e.get("QA_FAILSAFE_ONLY"))
