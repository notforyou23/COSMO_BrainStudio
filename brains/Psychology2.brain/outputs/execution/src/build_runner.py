from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import sys
from typing import Iterable, Optional, Sequence


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _is_nonempty_file(p: Path) -> bool:
    try:
        return p.is_file() and p.stat().st_size > 0
    except FileNotFoundError:
        return False


def _validate_artifacts(paths: Iterable[Path], *, label: str) -> None:
    missing = [str(p) for p in paths if not _is_nonempty_file(p)]
    if missing:
        raise FileNotFoundError(f"{label}: missing/empty required artifact(s): {', '.join(missing)}")


def _run_step(
    name: str,
    cmd: Sequence[str],
    *,
    build_dir: Path,
    cwd: Path,
    env: Optional[dict] = None,
) -> None:
    _ensure_dir(build_dir)
    log_path = build_dir / f"{name}.log"
    step_env = dict(os.environ)
    if env:
        step_env.update(env)
    step_env.setdefault("BUILD_DIR", str(build_dir))
    step_env.setdefault("COSMO_BUILD_DIR", str(build_dir))
    step_env.setdefault("_BUILD_DIR", str(build_dir))

    with log_path.open("w", encoding="utf-8") as lf:
        lf.write(f"[build_runner] step={name}\n[build_runner] cmd={' '.join(cmd)}\n[build_runner] cwd={cwd}\n")
        lf.flush()
        proc = subprocess.Popen(
            list(cmd),
            cwd=str(cwd),
            env=step_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            lf.write(line)
        rc = proc.wait()
        lf.write(f"\n[build_runner] step={name} rc={rc}\n")
        lf.flush()
    if rc != 0:
        raise subprocess.CalledProcessError(rc, list(cmd))



@dataclass(frozen=True)
class BuildConfig:
    repo_root: Path
    build_dir: Path
    artifact_gate_cmd: Sequence[str]
    taxonomy_validate_cmd: Sequence[str]
    toy_meta_analysis_cmd: Sequence[str]
    required_artifacts: Sequence[Path]


def run_build(config: BuildConfig) -> None:
    repo_root = config.repo_root.resolve()
    build_dir = config.build_dir.resolve()
    _ensure_dir(build_dir)

    # Force tools that respect common env/args to write into _build/
    env = {"BUILD_DIR": str(build_dir), "COSMO_BUILD_DIR": str(build_dir), "_BUILD_DIR": str(build_dir)}

    _run_step("01_artifact_gate", config.artifact_gate_cmd, build_dir=build_dir, cwd=repo_root, env=env)
    _validate_artifacts(config.required_artifacts, label="after artifact gate")

    _run_step("02_taxonomy_validation", config.taxonomy_validate_cmd, build_dir=build_dir, cwd=repo_root, env=env)
    _validate_artifacts(config.required_artifacts, label="after taxonomy validation")

    _run_step("03_toy_meta_analysis_demo", config.toy_meta_analysis_cmd, build_dir=build_dir, cwd=repo_root, env=env)
    _validate_artifacts(config.required_artifacts, label="after toy meta-analysis demo")



def _default_cmd(py: str, rel: str, build_dir: Path) -> Sequence[str]:
    # Many scripts accept --out/--output/--build-dir; we pass a conservative flag plus env.
    # If the script ignores it, logs still land in _build/ via this runner.
    return [py, rel, "--build-dir", str(build_dir)]


def default_config(
    *,
    repo_root: Path,
    build_dir: Optional[Path] = None,
    python_exe: Optional[str] = None,
    required_artifacts: Optional[Sequence[Path]] = None,
    artifact_gate_cmd: Optional[Sequence[str]] = None,
    taxonomy_validate_cmd: Optional[Sequence[str]] = None,
    toy_meta_analysis_cmd: Optional[Sequence[str]] = None,
) -> BuildConfig:
    repo_root = repo_root.resolve()
    build_dir = (build_dir or (repo_root / "_build")).resolve()
    py = python_exe or sys.executable

    req = list(required_artifacts or [])
    if not req:
        # Conservative defaults: caller/CI should override for strictness.
        req = [repo_root / "_build" / "build_manifest.json"]

    return BuildConfig(
        repo_root=repo_root,
        build_dir=build_dir,
        artifact_gate_cmd=artifact_gate_cmd or _default_cmd(py, "scripts/artifact_gate.py", build_dir),
        taxonomy_validate_cmd=taxonomy_validate_cmd or _default_cmd(py, "scripts/validate_taxonomy.py", build_dir),
        toy_meta_analysis_cmd=toy_meta_analysis_cmd or _default_cmd(py, "scripts/toy_meta_analysis_demo.py", build_dir),
        required_artifacts=tuple(Path(p) for p in req),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv or sys.argv[1:])
    repo_root = Path.cwd()
    build_dir = repo_root / "_build"
    cfg = default_config(repo_root=repo_root, build_dir=build_dir)
    try:
        run_build(cfg)
    except FileNotFoundError as e:
        sys.stderr.write(f"[build_runner] ERROR: {e}\n")
        return 2
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"[build_runner] ERROR: step failed rc={e.returncode}: {' '.join(map(str, e.cmd))}\n")
        return int(e.returncode) if e.returncode else 1
    except Exception as e:
        sys.stderr.write(f"[build_runner] ERROR: unexpected: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
