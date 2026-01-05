#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import shlex
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "runtime" / "_build" / "logs"


def _walk_candidates(name_hints: Iterable[str], max_depth: int = 5) -> List[Path]:
    hints = [h.lower() for h in name_hints]
    out: List[Path] = []
    for p in ROOT.rglob("*.py"):
        try:
            rel = p.relative_to(ROOT)
        except Exception:
            continue
        if len(rel.parts) > max_depth:
            continue
        s = str(rel).lower()
        if any(h in s for h in hints):
            out.append(p)
    out.sort(key=lambda x: (len(x.relative_to(ROOT).parts), len(str(x))))
    return out


def _first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists() and p.is_file():
            return p
    return None


def resolve_command(step: str, env_key: str, hints: Iterable[str], explicit_files: Iterable[str]) -> Tuple[List[str], str]:
    env_val = os.environ.get(env_key, "").strip()
    if env_val:
        return shlex.split(env_val), f"from ${env_key}"

    explicit = [_first_existing([ROOT / f]) for f in explicit_files]
    explicit = [p for p in explicit if p is not None]
    if explicit:
        return [sys.executable, str(explicit[0])], f"script {explicit[0].relative_to(ROOT)}"

    cands = _walk_candidates(hints)
    if cands:
        return [sys.executable, str(cands[0])], f"discovered {cands[0].relative_to(ROOT)}"

    return [], f"missing (set {env_key} to override)"


def run_step(idx: int, name: str, cmd: List[str], origin: str) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{idx:02d}_{name}.log"
    if not cmd:
        msg = f"[{idx}/3] {name}: FAILED - no command ({origin})\n"
        sys.stderr.write(msg)
        log_path.write_text(msg, encoding="utf-8")
        return 2

    header = f"[{idx}/3] {name}: RUN {' '.join(shlex.quote(c) for c in cmd)} ({origin})\n"
    sys.stdout.write(header)
    sys.stdout.flush()

    with log_path.open("w", encoding="utf-8") as lf:
        lf.write(header)
        lf.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
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
        tail = f"[{idx}/3] {name}: {'OK' if rc == 0 else 'FAILED'} (exit={rc})\n"
        sys.stdout.write(tail)
        sys.stdout.flush()
        lf.write(tail)
        lf.flush()
        return rc


def main(argv: List[str]) -> int:
    steps = [
        ("taxonomy_smoke_test", "TAXONOMY_SMOKE_TEST_CMD",
         ["taxonomy", "smoke"], ["taxonomy_smoke_test.py", "taxonomy_smoketest.py", "smoke_test_taxonomy.py"]),
        ("toy_demo_run", "TOY_DEMO_CMD",
         ["toy", "demo"], ["toy_demo.py", "demo_toy.py", "toy_run.py", "run_toy_demo.py"]),
        ("artifact_gate", "ARTIFACT_GATE_CMD",
         ["artifact", "gate"], ["artifact_gate.py", "gate_artifacts.py", "artifact_check.py", "artifact_gating.py"]),
    ]

    for i, (name, env_key, hints, explicit) in enumerate(steps, start=1):
        cmd, origin = resolve_command(name, env_key, hints, explicit)
        rc = run_step(i, name, cmd, origin)
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
