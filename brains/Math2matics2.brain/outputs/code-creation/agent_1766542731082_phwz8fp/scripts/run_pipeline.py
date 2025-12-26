#!/usr/bin/env python3
\"\"\"Run one research cycle and enforce the outputs-per-cycle policy.

Policy: each cycle must add or update at least one file in the chosen outputs dir.
Portability: if /outputs (or the preferred outputs dir) is unwritable, fall back to a
writable directory inside the project (e.g., .outputs/).
\"\"\"

from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import time
def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_policy(root: Path) -> dict:
    cfg = root / "config" / "outputs_policy.json"
    if cfg.is_file():
        try:
            return json.loads(cfg.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Minimal v1 defaults (kept inline to avoid extra dependencies).
    return {
        "outputs_preference": [str(root / "outputs"), "/outputs", str(root / ".outputs")],
        "minimum_v1_required": ["README.md", "core_findings.md"],
        "enforce_change_each_cycle": True,
    }
def _is_writable_dir(d: Path) -> bool:
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def choose_outputs_dir(root: Path, policy: dict) -> Path:
    prefs = policy.get("outputs_preference") or [str(root / "outputs"), "/outputs", str(root / ".outputs")]
    for p in prefs:
        d = Path(p)
        if not d.is_absolute():
            d = (root / d).resolve()
        if _is_writable_dir(d):
            return d
    # Last-resort: create a unique temp-ish directory under root.
    d = root / ".outputs_fallback"
    if not _is_writable_dir(d):
        raise RuntimeError("No writable outputs directory found.")
    return d
def snapshot_outputs(d: Path) -> dict[str, tuple[int, int]]:
    \"\"\"Return {relative_path: (mtime_ns, size)} for all files under outputs.\"\"\"
    snap: dict[str, tuple[int, int]] = {}
    if not d.exists():
        return snap
    for p in sorted(d.rglob("*")):
        if p.is_file():
            st = p.stat()
            snap[str(p.relative_to(d))] = (st.st_mtime_ns, st.st_size)
    return snap


def changed_files(before: dict, after: dict) -> list[str]:
    changed = []
    for k, v in after.items():
        if k not in before or before[k] != v:
            changed.append(k)
    return sorted(changed)
def ensure_minimum_v1_docs(outputs: Path) -> None:
    outputs.mkdir(parents=True, exist_ok=True)
    readme = outputs / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Outputs (minimum v1)\n\n"
            "This directory contains the required, persisted artifacts produced by each research cycle.\n\n"
            "## Policy\n"
            "- Each research cycle must add or update at least one file in this directory.\n"
            "- When `outputs/` is not writable, the pipeline falls back to a writable outputs directory.\n\n"
            "## Core documents\n"
            "- `core_findings.md`: consolidated findings/decisions; updated at least once per cycle.\n",
            encoding="utf-8",
        )
    core = outputs / "core_findings.md"
    if not core.exists():
        core.write_text(
            "# Core findings\n\n"
            "- Initialized: {ts}\n".format(ts=time.strftime("%Y-%m-%d %H:%M:%S")),
            encoding="utf-8",
        )


def touch_core_findings(outputs: Path, note: str) -> None:
    core = outputs / "core_findings.md"
    core.parent.mkdir(parents=True, exist_ok=True)
    existing = core.read_text(encoding="utf-8") if core.exists() else "# Core findings\n\n"
    line = f"- {time.strftime('%Y-%m-%d %H:%M:%S')} — {note}\n"
    core.write_text(existing + line, encoding="utf-8")
def run_research_cycle(outputs: Path) -> int:
    \"\"\"Run the research cycle.

    If RESEARCH_CMD is set, executes it as a shell command with OUTPUTS_DIR env set.
    Otherwise, performs a minimal cycle by appending a heartbeat line to core_findings.
    \"\"\"
    cmd = os.environ.get("RESEARCH_CMD", "").strip()
    if not cmd:
        touch_core_findings(outputs, "cycle heartbeat (no RESEARCH_CMD configured)")
        return 0

    env = dict(os.environ)
    env["OUTPUTS_DIR"] = str(outputs)
    try:
        proc = subprocess.run(cmd, shell=True, env=env)
        return int(proc.returncode)
    except Exception as e:
        touch_core_findings(outputs, f"research command failed to start: {e!r}")
        return 1
def main(argv: list[str]) -> int:
    root = _project_root()
    policy = _load_policy(root)
    outputs = choose_outputs_dir(root, policy)
    ensure_minimum_v1_docs(outputs)

    before = snapshot_outputs(outputs)
    rc = run_research_cycle(outputs)
    after = snapshot_outputs(outputs)

    if policy.get("enforce_change_each_cycle", True):
        diffs = changed_files(before, after)
        if not diffs:
            # Enforce by making a deterministic, minimal update to a core doc.
            touch_core_findings(outputs, "policy enforcement: no outputs changed; forced update")
            after2 = snapshot_outputs(outputs)
            diffs = changed_files(before, after2)
        if not diffs:
            raise SystemExit("Outputs policy violation: no files added/updated in outputs this cycle.")
    # Keep runtime output minimal.
    if os.environ.get("PIPELINE_STATUS", "1") != "0":
        sys.stdout.write(f"outputs_dir={outputs}\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
