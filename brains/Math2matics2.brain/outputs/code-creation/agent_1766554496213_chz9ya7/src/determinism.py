from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import shutil
from typing import Callable, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = 1


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(root: Path, *, include_globs: Optional[Iterable[str]] = None) -> str:
    if not root.exists():
        return _sha256_bytes(b"")
    files: List[Path] = []
    if root.is_file():
        files = [root]
    else:
        if include_globs:
            for pat in include_globs:
                files.extend([p for p in root.rglob(pat) if p.is_file()])
        else:
            files = [p for p in root.rglob("*") if p.is_file()]
    files = sorted(set(files), key=lambda p: p.as_posix())
    h = hashlib.sha256()
    for p in files:
        rel = p.relative_to(root) if root.is_dir() else Path(p.name)
        h.update(rel.as_posix().encode("utf-8") + b"\n")
        h.update(sha256_file(p).encode("utf-8") + b"\n")
    return h.hexdigest()


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    kind: str  # "file" | "tree"
    relpath: str
    include_globs: Optional[Tuple[str, ...]] = None


DEFAULT_ARTIFACTS: Tuple[ArtifactSpec, ...] = (
    ArtifactSpec(name="results.json", kind="file", relpath="results.json"),
    ArtifactSpec(name="run_stamp.json", kind="file", relpath="run_stamp.json"),
    ArtifactSpec(name="logs", kind="tree", relpath="logs"),
)


def _ensure_empty_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _artifact_checksum(run_outputs_dir: Path, spec: ArtifactSpec) -> Dict[str, Optional[str]]:
    p = run_outputs_dir / spec.relpath
    if spec.kind == "file":
        if not p.exists() or not p.is_file():
            return {"path": spec.relpath, "sha256": None}
        return {"path": spec.relpath, "sha256": sha256_file(p)}
    if spec.kind == "tree":
        if not p.exists():
            return {"path": spec.relpath, "sha256": _sha256_bytes(b"")}
        globs = list(spec.include_globs) if spec.include_globs else None
        return {"path": spec.relpath, "sha256": sha256_tree(p, include_globs=globs)}
    raise ValueError(f"Unknown artifact kind: {spec.kind}")


def build_determinism_report(
    run1_outputs_dir: Path,
    run2_outputs_dir: Path,
    *,
    seed: int,
    artifacts: Iterable[ArtifactSpec] = DEFAULT_ARTIFACTS,
) -> Dict:
    artifacts = list(artifacts)
    report: Dict = {
        "schema_version": SCHEMA_VERSION,
        "seed": int(seed),
        "runs": {
            "run1": {"outputs_dir": run1_outputs_dir.as_posix()},
            "run2": {"outputs_dir": run2_outputs_dir.as_posix()},
        },
        "artifacts": {},
        "all_match": True,
    }
    for spec in artifacts:
        a1 = _artifact_checksum(run1_outputs_dir, spec)
        a2 = _artifact_checksum(run2_outputs_dir, spec)
        match = (a1.get("sha256") == a2.get("sha256")) and (a1.get("sha256") is not None)
        report["artifacts"][spec.name] = {
            "run1": a1,
            "run2": a2,
            "match": bool(match),
        }
        report["all_match"] = bool(report["all_match"] and match)
    return report


def write_determinism_report(report: Dict, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


Runner = Callable[[int, Path], None]


def run_pipeline_twice_and_report(
    runner: Runner,
    *,
    seed: int = 12345,
    outputs_dir: Optional[Path] = None,
    report_path: Optional[Path] = None,
    artifacts: Iterable[ArtifactSpec] = DEFAULT_ARTIFACTS,
    clean_between_runs: bool = True,
) -> Dict:
    root = Path.cwd()
    outputs_dir = outputs_dir or (root / "outputs")
    report_path = report_path or (outputs_dir / "determinism_report.json")

    run1_dir = outputs_dir / "_determinism_run1"
    run2_dir = outputs_dir / "_determinism_run2"
    if clean_between_runs:
        _ensure_empty_dir(run1_dir)
        _ensure_empty_dir(run2_dir)
    else:
        run1_dir.mkdir(parents=True, exist_ok=True)
        run2_dir.mkdir(parents=True, exist_ok=True)

    # Encourage deterministic behavior across common libs; runner may additionally seed inside.
    os.environ["PYTHONHASHSEED"] = str(int(seed))
    os.environ["PIPELINE_SEED"] = str(int(seed))

    runner(int(seed), run1_dir)
    runner(int(seed), run2_dir)

    report = build_determinism_report(run1_dir, run2_dir, seed=int(seed), artifacts=artifacts)
    write_determinism_report(report, report_path)
    return report
