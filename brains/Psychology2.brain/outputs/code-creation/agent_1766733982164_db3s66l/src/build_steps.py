from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os, sys, time, json, subprocess
from typing import Optional, Sequence, Dict, Any, List

@dataclass
class StepResult:
    name: str
    ok: bool
    returncode: int
    duration_s: float
    out_dir: str
    cmd: List[str]
    stdout_path: str
    stderr_path: str
    error: Optional[str] = None

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def build_base(root: Optional[Path] = None) -> Path:
    r = root or repo_root()
    p = r / "runtime" / "_build"
    p.mkdir(parents=True, exist_ok=True)
    return p

def step_dir(step: str, root: Optional[Path] = None) -> Path:
    p = build_base(root) / step
    p.mkdir(parents=True, exist_ok=True)
    return p

def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def _discover(root: Path, step: str) -> List[str]:
    py = sys.executable
    if step == "artifact_gate":
        files = ["src/artifact_gate.py", "scripts/artifact_gate.py", "tools/artifact_gate.py"]
        mods = ["artifact_gate", "src.artifact_gate", "tools.artifact_gate"]
    elif step == "taxonomy_validation":
        files = ["src/taxonomy_validation.py", "src/validate_taxonomy.py", "src/taxonomy_validate.py",
                 "scripts/taxonomy_validation.py", "tools/taxonomy_validation.py", "tools/taxonomy_validate.py"]
        mods = ["taxonomy_validation", "validate_taxonomy", "taxonomy_validate",
                "src.taxonomy_validation", "src.validate_taxonomy", "src.taxonomy_validate"]
    elif step == "meta_analysis_demo":
        files = ["src/meta_analysis_demo.py", "src/meta_analysis.py", "scripts/meta_analysis_demo.py", "tools/meta_analysis_demo.py"]
        mods = ["meta_analysis_demo", "src.meta_analysis_demo", "tools.meta_analysis_demo"]
    else:
        raise ValueError(f"Unknown step: {step}")

    for rel in files:
        fp = root / rel
        if fp.is_file():
            return [py, str(fp)]
    for m in mods:
        return [py, "-m", m]
    raise FileNotFoundError(
        f"Could not find an entrypoint for step '{step}'. Looked for files: {files} and modules: {mods}."
    )

def run_subprocess(step: str, cmd: Optional[Sequence[str]] = None, *, root: Optional[Path] = None,
                   extra_env: Optional[Dict[str, str]] = None, timeout_s: Optional[int] = None) -> StepResult:
    r = root or repo_root()
    out = step_dir(step, r)
    stdout_path = out / "stdout.log"
    stderr_path = out / "stderr.log"
    meta_path = out / "result.json"

    real_cmd = list(cmd) if cmd is not None else _discover(r, step)
    env = os.environ.copy()
    env["BUILD_OUTDIR"] = str(out)
    if extra_env:
        env.update({k: str(v) for k, v in extra_env.items()})

    t0 = time.time()
    err = None
    rc = 1
    try:
        with stdout_path.open("w", encoding="utf-8") as so, stderr_path.open("w", encoding="utf-8") as se:
            p = subprocess.run(real_cmd, cwd=str(r), env=env, stdout=so, stderr=se, text=True, timeout=timeout_s)
            rc = int(p.returncode)
    except subprocess.TimeoutExpired as e:
        err = f"Timed out after {timeout_s}s: {e}"
        rc = 124
    except FileNotFoundError as e:
        err = f"Command not found: {e}"
        rc = 127
    except Exception as e:
        err = f"Unexpected error running step '{step}': {type(e).__name__}: {e}"
        rc = 1
    dt = time.time() - t0
    ok = (rc == 0) and (err is None)

    res = StepResult(
        name=step, ok=ok, returncode=rc, duration_s=round(dt, 6), out_dir=str(out),
        cmd=[str(x) for x in real_cmd], stdout_path=str(stdout_path), stderr_path=str(stderr_path), error=err
    )
    _write_json(meta_path, {
        "name": res.name, "ok": res.ok, "returncode": res.returncode, "duration_s": res.duration_s,
        "out_dir": res.out_dir, "cmd": res.cmd, "stdout_path": res.stdout_path, "stderr_path": res.stderr_path,
        "error": res.error,
    })
    if not ok:
        tail = ""
        try:
            s = stderr_path.read_text(encoding="utf-8", errors="replace")
            if s.strip():
                tail = "\n--- stderr (tail) ---\n" + "\n".join(s.splitlines()[-80:])
        except Exception:
            pass
        msg = err or f"Step '{step}' failed with return code {rc}."
        raise RuntimeError(msg + tail)
    return res

def run_artifact_gate(cmd: Optional[Sequence[str]] = None, *, root: Optional[Path] = None, **kw) -> StepResult:
    return run_subprocess("artifact_gate", cmd, root=root, **kw)

def run_taxonomy_validation(cmd: Optional[Sequence[str]] = None, *, root: Optional[Path] = None, **kw) -> StepResult:
    return run_subprocess("taxonomy_validation", cmd, root=root, **kw)

def run_meta_analysis_demo(cmd: Optional[Sequence[str]] = None, *, root: Optional[Path] = None, **kw) -> StepResult:
    return run_subprocess("meta_analysis_demo", cmd, root=root, **kw)
