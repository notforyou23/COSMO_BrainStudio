from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple
import os
import re


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    errors: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()


def canonicalize_path(path: os.PathLike | str, *, base: Optional[os.PathLike | str] = None) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (Path(base) if base else Path.cwd()) / p
    try:
        return p.resolve()
    except Exception:
        return p.absolute()


def _read_text(p: Path, max_bytes: int = 256_000) -> str:
    try:
        b = p.read_bytes()
    except Exception:
        return ""
    if len(b) > max_bytes:
        b = b[:max_bytes]
    try:
        return b.decode("utf-8")
    except Exception:
        try:
            return b.decode("utf-8", errors="replace")
        except Exception:
            return ""


def _nonempty_lines(s: str) -> List[str]:
    return [ln.strip() for ln in s.splitlines() if ln.strip()]


def _has_markdown_link(s: str) -> bool:
    return bool(re.search(r"\[[^\]]+\]\([^\)]+\)", s))


def _find_first_existing(root: Path, rels: Sequence[str]) -> Optional[Path]:
    for r in rels:
        p = root / r
        if p.is_file():
            return p
    return None


def _glob_first(root: Path, patterns: Sequence[str]) -> Optional[Path]:
    for pat in patterns:
        for p in root.glob(pat):
            if p.is_file():
                return p
    return None


def _collect_claim_card_files(root: Path) -> List[Path]:
    candidates: List[Path] = []
    for drel in ("claim_cards", "claims", "artifacts/claim_cards", "outputs/claim_cards", "qa/claim_cards"):
        d = root / drel
        if d.is_dir():
            candidates.extend([p for p in d.rglob("*.md") if p.is_file()])
    candidates.extend([p for p in root.glob("**/CLAIM_CARDS.md") if p.is_file()])
    candidates.extend([p for p in root.glob("**/claim_cards*.md") if p.is_file()])
    candidates.extend([p for p in root.glob("**/*claim*card*.md") if p.is_file()])
    seen = set()
    out = []
    for p in candidates:
        cp = canonicalize_path(p)
        if cp not in seen:
            seen.add(cp)
            out.append(cp)
    return out
def check_tracking_reconciliation(root: os.PathLike | str) -> CheckResult:
    rootp = canonicalize_path(root)
    p = _find_first_existing(rootp, ["TRACKING_RECONCILIATION.md", "docs/TRACKING_RECONCILIATION.md", "artifacts/TRACKING_RECONCILIATION.md"])
    if not p:
        return CheckResult(False, errors=("Missing required TRACKING_RECONCILIATION.md",))
    txt = _read_text(p)
    lines = _nonempty_lines(txt)
    errors: List[str] = []
    warnings: List[str] = []

    if len(lines) < 8:
        errors.append(f"{p.name} appears incomplete (expected >= 8 non-empty lines, found {len(lines)})")

    joined = "\n".join(lines).lower()
    must_tokens = ["reconcil", "track"]
    if not all(tok in joined for tok in must_tokens):
        warnings.append(f"{p.name} missing expected keywords (tracking/reconciliation)")

    if not (_has_markdown_link(txt) or "http" in joined):
        warnings.append(f"{p.name} has no obvious links to supporting artifacts")

    if not any("claim" in ln.lower() for ln in lines):
        warnings.append(f"{p.name} does not mention claims; expected mapping to Claim Cards")

    return CheckResult(len(errors) == 0, errors=tuple(errors), warnings=tuple(warnings))


def _claim_card_quality(p: Path) -> Tuple[bool, List[str]]:
    txt = _read_text(p)
    lines = _nonempty_lines(txt)
    errs: List[str] = []
    if len(lines) < 6:
        errs.append(f"{p}: too short (expected >= 6 non-empty lines)")
        return False, errs
    joined = "\n".join(lines).lower()
    has_heading = any(ln.startswith("#") for ln in lines)
    if not has_heading:
        errs.append(f"{p}: missing markdown heading(s)")
    key_terms = ["claim", "evidence", "status"]
    if sum(1 for t in key_terms if t in joined) < 2:
        errs.append(f"{p}: missing expected fields (need at least two of: Claim/Evidence/Status)")
    return len(errs) == 0, errs


def check_claim_cards(root: os.PathLike | str) -> CheckResult:
    rootp = canonicalize_path(root)
    files = _collect_claim_card_files(rootp)
    if not files:
        return CheckResult(False, errors=("Missing Claim Cards (no matching .md files found)",))
    ok_any = False
    errors: List[str] = []
    warnings: List[str] = []
    for p in sorted(files)[:20]:
        ok, errs = _claim_card_quality(p)
        if ok:
            ok_any = True
        else:
            errors.extend(errs)
    if not ok_any:
        errors.insert(0, "Found Claim Card files, but none meet minimal completeness heuristics")
    if len(files) > 20:
        warnings.append(f"Detected {len(files)} claim-card-like files; only first 20 were inspected for completeness")
    return CheckResult(len(errors) == 0, errors=tuple(errors), warnings=tuple(warnings))
def check_qa_gate_artifacts(root: os.PathLike | str) -> CheckResult:
    rootp = canonicalize_path(root)
    errors: List[str] = []
    warnings: List[str] = []

    report = _glob_first(
        rootp,
        [
            "**/qa_gate_report.json",
            "**/QA_GATE_REPORT.json",
            "**/qa_gate_report.md",
            "**/QA_GATE_REPORT.md",
            "**/qa_gate.md",
            "**/QA_GATE.md",
        ],
    )
    if not report:
        errors.append("Missing QA gate report artifact (expected qa_gate_report.{json,md} or QA_GATE_REPORT.{json,md})")
        return CheckResult(False, errors=tuple(errors))

    txt = _read_text(report)
    if report.suffix.lower() == ".json":
        try:
            import json as _json  # local import to keep module light

            data = _json.loads(txt or "{}")
            if not isinstance(data, dict):
                errors.append(f"{report}: JSON report is not an object")
            else:
                if not any(k in data for k in ("ok", "status", "passed", "failures", "errors", "stages")):
                    warnings.append(f"{report}: JSON lacks common QA gate keys (ok/status/passed/errors/stages)")
        except Exception as e:
            errors.append(f"{report}: invalid JSON ({e})")
    else:
        lines = _nonempty_lines(txt)
        if len(lines) < 5:
            errors.append(f"{report}: appears incomplete (expected >= 5 non-empty lines, found {len(lines)})")
        if not (any("pass" in ln.lower() for ln in lines) or any("fail" in ln.lower() for ln in lines)):
            warnings.append(f"{report}: does not contain obvious PASS/FAIL wording")

    gate_dir = _glob_first(rootp, ["**/.qa_gate/index.json", "**/.qa_gate/manifest.json", "**/.qa_gate/report.json"])
    if not gate_dir:
        warnings.append("No .qa_gate index/manifest found; report exists but structured gate dir artifacts are missing")

    return CheckResult(len(errors) == 0, errors=tuple(errors), warnings=tuple(warnings))


def run_all_required_checks(project_root: os.PathLike | str) -> CheckResult:
    rootp = canonicalize_path(project_root)
    results = [
        ("TRACKING_RECONCILIATION", check_tracking_reconciliation(rootp)),
        ("CLAIM_CARDS", check_claim_cards(rootp)),
        ("QA_GATE_ARTIFACTS", check_qa_gate_artifacts(rootp)),
    ]
    errors: List[str] = []
    warnings: List[str] = []
    for name, r in results:
        errors.extend([f"[{name}] {e}" for e in r.errors])
        warnings.extend([f"[{name}] {w}" for w in r.warnings])
    return CheckResult(len(errors) == 0, errors=tuple(errors), warnings=tuple(warnings))
