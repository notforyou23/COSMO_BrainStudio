from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import os
import shlex
import subprocess
import time
import glob


@dataclass
class RunResult:
    ok: bool
    cmd: List[str]
    cwd: str
    returncode: int
    duration_s: float
    stdout: str
    stderr: str
    error: Optional[str] = None


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: Dict[str, Any]


def find_project_root(start: Path) -> Path:
    start = start.resolve()
    for p in [start] + list(start.parents):
        if (p / "pyproject.toml").is_file() or (p / ".git").exists() or (p / "src").is_dir():
            return p
    return start


def _run(cmd: Sequence[str], cwd: Path, timeout_s: int = 180) -> RunResult:
    t0 = time.time()
    try:
        p = subprocess.run(
            list(cmd),
            cwd=str(cwd),
            env=dict(os.environ),
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        return RunResult(
            ok=(p.returncode == 0),
            cmd=list(cmd),
            cwd=str(cwd),
            returncode=p.returncode,
            duration_s=round(time.time() - t0, 3),
            stdout=p.stdout[-20000:],
            stderr=p.stderr[-20000:],
        )
    except Exception as e:
        return RunResult(
            ok=False,
            cmd=list(cmd),
            cwd=str(cwd),
            returncode=999,
            duration_s=round(time.time() - t0, 3),
            stdout="",
            stderr="",
            error=f"{type(e).__name__}: {e}",
        )


def _discover_generator_cmd(project_root: Path) -> Optional[List[str]]:
    env_cmd = os.environ.get("SCAFFOLD_CMD", "").strip()
    if env_cmd:
        return shlex.split(env_cmd)

    candidates = [
        project_root / "scripts" / "generate_scaffold.py",
        project_root / "scripts" / "scaffold_generator.py",
        project_root / "scripts" / "scaffold.py",
        project_root / "scripts" / "generate.py",
    ]
    for s in candidates:
        if s.is_file():
            return [os.environ.get("PYTHON", "python"), str(s)]
    # As a fallback, try a module invocation if present on path (optional)
    return None


def _expected_artifacts(outputs_dir: Path) -> Dict[str, Path]:
    return {
        "REPORT_OUTLINE.md": outputs_dir / "REPORT_OUTLINE.md",
        "CASE_STUDY_TEMPLATE.md": outputs_dir / "CASE_STUDY_TEMPLATE.md",
        "METADATA_SCHEMA.md": outputs_dir / "METADATA_SCHEMA.md",
        "CASE_STUDIES_INDEX.csv": outputs_dir / "CASE_STUDIES_INDEX.csv",
    }


def _find_rights_artifacts(outputs_dir: Path) -> List[str]:
    patterns = [
        str(outputs_dir / "LICENSE*"),
        str(outputs_dir / "NOTICE*"),
        str(outputs_dir / "RIGHTS*"),
        str(outputs_dir / "COPYRIGHT*"),
        str(outputs_dir / "rights" / "LICENSE*"),
        str(outputs_dir / "rights" / "NOTICE*"),
        str(outputs_dir / "rights" / "RIGHTS*"),
        str(outputs_dir / "rights" / "COPYRIGHT*"),
    ]
    hits: List[str] = []
    for pat in patterns:
        for p in glob.glob(pat):
            pp = Path(p)
            if pp.is_file():
                hits.append(str(pp))
    return sorted(set(hits))


def validate(
    project_root: Optional[Path] = None,
    outputs_dir: Optional[Path] = None,
    run_generator: bool = True,
    timeout_s: int = 180,
) -> Dict[str, Any]:
    root = find_project_root(project_root or Path.cwd())
    out_dir = (outputs_dir or (root / "outputs")).resolve()

    checks: List[CheckResult] = []
    run_result: Optional[RunResult] = None

    if run_generator:
        cmd = _discover_generator_cmd(root)
        if not cmd:
            checks.append(
                CheckResult(
                    name="generator_discovery",
                    ok=False,
                    details={"error": "No scaffold generator entrypoint found. Set SCAFFOLD_CMD or add scripts/generate_scaffold.py."},
                )
            )
        else:
            run_result = _run(cmd, cwd=root, timeout_s=timeout_s)
            checks.append(CheckResult(name="generator_run", ok=run_result.ok, details=asdict(run_result)))

    checks.append(
        CheckResult(
            name="outputs_dir_exists",
            ok=out_dir.exists() and out_dir.is_dir(),
            details={"path": str(out_dir)},
        )
    )

    expected = _expected_artifacts(out_dir)
    missing: Dict[str, str] = {}
    present: Dict[str, Dict[str, Any]] = {}
    for name, p in expected.items():
        if p.is_file():
            try:
                size = p.stat().st_size
            except Exception:
                size = None
            present[name] = {"path": str(p), "size": size}
        else:
            missing[name] = str(p)

    checks.append(
        CheckResult(
            name="required_files_present",
            ok=(len(missing) == 0),
            details={"present": present, "missing": missing},
        )
    )

    rights_hits = _find_rights_artifacts(out_dir)
    checks.append(
        CheckResult(
            name="rights_artifacts_present",
            ok=(len(rights_hits) > 0),
            details={"matches": rights_hits},
        )
    )

    ok = all(c.ok for c in checks)
    return {
        "ok": ok,
        "project_root": str(root),
        "outputs_dir": str(out_dir),
        "run_generator": run_generator,
        "checks": [asdict(c) for c in checks],
        "generator": (asdict(run_result) if run_result else None),
    }
