from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Tuple, List

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: List[str]) -> Tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = (p.stdout or "").strip()
    if out:
        print(out)
    return p.returncode, out


def _read_text(p: Path, limit: int = 200_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def _find_first(candidates: Iterable[Path]) -> Path | None:
    for p in candidates:
        if p.is_file():
            return p
    return None


def _glob_any(base: Path, patterns: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    for pat in patterns:
        out.extend(sorted(base.glob(pat)))
    return out


def _fail(msg: str, failures: List[str]) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


def _warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


def check_tracking_reconciliation(root: Path, failures: List[str]) -> None:
    candidates = [
        root / "TRACKING_RECONCILIATION.md",
        root / "docs" / "TRACKING_RECONCILIATION.md",
        root / "outputs" / "TRACKING_RECONCILIATION.md",
    ]
    p = _find_first(candidates)
    if not p:
        _fail("Missing TRACKING_RECONCILIATION.md (looked in repo root/docs/outputs).", failures)
        return
    txt = _read_text(p)
    if len(txt.strip()) < 200:
        _fail(f"TRACKING_RECONCILIATION.md too small ({len(txt.strip())} chars): {p}", failures)
        return
    must = ["claim", "tracking", "recon"]
    if not any(k in txt.lower() for k in must):
        _fail(f"TRACKING_RECONCILIATION.md lacks expected keywords {must}: {p}", failures)


def check_claim_cards(root: Path, failures: List[str]) -> None:
    dirs = [
        root / "claim_cards",
        root / "Claim Cards",
        root / "claims",
        root / "outputs" / "claim_cards",
        root / "outputs" / "claims",
    ]
    found_files: List[Path] = []
    for d in dirs:
        if d.is_dir():
            found_files.extend([p for p in d.rglob("*.md") if p.is_file()])
    if not found_files:
        # fallback: search for obvious claim-card files anywhere, but bounded
        found_files = [p for p in root.rglob("CLAIM*.md") if p.is_file()]
    if not found_files:
        _fail("Missing Claim Cards (.md) (looked in claim_cards/Claim Cards/claims and outputs/*).", failures)
        return
    good = 0
    for p in found_files[:50]:
        txt = _read_text(p)
        if len(txt.strip()) >= 120 and (re.search(r"\bclaim\b", txt, re.I) or re.search(r"\bevidence\b", txt, re.I)):
            good += 1
    if good == 0:
        _fail(f"Claim Cards present but none appear complete (checked {min(len(found_files),50)} files).", failures)


def check_qa_gate_artifacts(root: Path, failures: List[str]) -> None:
    # Accept common names to be resilient across implementations
    candidates = _glob_any(root, [
        "QA_GATE_REPORT.json",
        "qa_gate_report.json",
        "QA_GATE_REPORT.md",
        "qa_gate_report.md",
        "qa_gate_report.txt",
        "outputs/QA_GATE_REPORT.*",
        "outputs/qa_gate_report.*",
    ])
    p = _find_first(candidates)
    if not p:
        _fail("Missing QA gate report artifact (QA_GATE_REPORT.* or qa_gate_report.* in root/outputs).", failures)
        return
    txt = _read_text(p)
    if len(txt.strip()) < 50:
        _fail(f"QA gate report too small ({len(txt.strip())} chars): {p}", failures)
        return
    # Minimal signal that it contains some structured status
    if p.suffix.lower() == ".json":
        try:
            data = json.loads(txt)
            if not isinstance(data, dict) or not any(k in data for k in ("ok", "status", "failures", "checks")):
                _fail(f"QA gate JSON report missing expected keys: {p}", failures)
        except Exception as e:
            _fail(f"QA gate JSON report not parseable: {p} ({e})", failures)
    else:
        if not re.search(r"\b(pass|fail|status|check)\b", txt, re.I):
            _warn(f"QA gate report lacks obvious status words: {p}")


def main(argv: List[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    failures: List[str] = []

    init_cmd = os.environ.get("INIT_OUTPUTS_CMD")
    validate_cmd = os.environ.get("VALIDATE_OUTPUTS_CMD")

    # Default to running as modules (preferred for deterministic execution).
    init = init_cmd.split() if init_cmd else [sys.executable, "-m", "tools.init_outputs"]
    validate = validate_cmd.split() if validate_cmd else [sys.executable, "-m", "tools.validate_outputs"]

    # Allow passthrough args to validate step, e.g. python -m tools.pipeline -- --strict
    passthrough: List[str] = []
    if "--" in argv:
        i = argv.index("--")
        passthrough = argv[i + 1 :]
        argv = argv[:i]

    rc, _ = _run(init)
    if rc != 0:
        _fail(f"init_outputs failed (rc={rc}).", failures)

    rc2, _ = _run(validate + passthrough)
    if rc2 != 0:
        _fail(f"validate_outputs failed (rc={rc2}).", failures)

    # Required artifact checks (independent of validate step).
    check_tracking_reconciliation(ROOT, failures)
    check_claim_cards(ROOT, failures)
    check_qa_gate_artifacts(ROOT, failures)

    if failures:
        print(f"QA_GATE:FAIL ({len(failures)} issue(s))", file=sys.stderr)
        return 2
    print("QA_GATE:PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
