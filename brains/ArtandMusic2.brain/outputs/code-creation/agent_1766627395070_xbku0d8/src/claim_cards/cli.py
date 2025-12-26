"""Claim card workflow CLI.

Validates claim cards and (optionally) a pilot case study for required workflow checks.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


RE_CC_ID = re.compile(r"\bCC[-_][A-Za-z0-9][A-Za-z0-9._-]*\b")
RE_URL = re.compile(r"https?://\S+", re.IGNORECASE)
RE_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)


REQUIRED_FIELDS = [
    "claim text",
    "scope",
    "evidence type",
    "citations",
    "verification status",
    "abstention triggers",
]


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    candidates = {"pyproject.toml", "setup.cfg", ".git"}
    for p in [cur, *cur.parents]:
        for name in candidates:
            if (p / name).exists():
                return p
    return cur


def _discover_claim_card_dirs(root: Path) -> List[Path]:
    dirs = []
    for name in ("claim_cards", "claims", "claim-cards", "claimcards"):
        d = root / name
        if d.is_dir():
            dirs.append(d)
    docs = root / "docs"
    if docs.is_dir():
        for name in ("claim_cards", "claims", "claim-cards", "claimcards"):
            d = docs / name
            if d.is_dir():
                dirs.append(d)
    # Avoid including source package directory.
    dirs = [d for d in dirs if "src" not in d.parts or d.name not in ("claim_cards",)]
    # De-dup
    seen = set()
    out = []
    for d in dirs:
        r = d.resolve()
        if r not in seen:
            seen.add(r)
            out.append(d)
    return out


def _iter_md_files(paths: Sequence[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if p.is_file() and p.suffix.lower() in (".md", ".markdown"):
            files.append(p)
        elif p.is_dir():
            files.extend(sorted([x for x in p.rglob("*.md") if x.is_file()]))
            files.extend(sorted([x for x in p.rglob("*.markdown") if x.is_file()]))
    # De-dup stable
    seen = set()
    out = []
    for f in files:
        r = f.resolve()
        if r not in seen:
            seen.add(r)
            out.append(f)
    return out


def _extract_card_ids(file_path: Path, text: str) -> Set[str]:
    ids = set(RE_CC_ID.findall(text))
    stem = file_path.stem
    if stem.upper().startswith("CC-") or stem.upper().startswith("CC_"):
        ids.add(stem)
    return ids


def _has_field(text: str, field: str) -> bool:
    n = _norm(field)
    # Accept headings, bold labels, or simple label lines.
    patterns = [
        rf"^\s*#+\s*{re.escape(n)}\b",
        rf"\*\*\s*{re.escape(n)}\s*\*\*\s*:",
        rf"^\s*{re.escape(n)}\s*:",
    ]
    low = text.lower()
    for pat in patterns:
        if re.search(pat, low, flags=re.IGNORECASE | re.MULTILINE):
            return True
    # For citations, allow DOI/URL presence
    if n == "citations":
        if RE_URL.search(text) or RE_DOI.search(text):
            return True
    return False


def validate_claim_card(path: Path, text: str) -> Tuple[List[str], List[str], Set[str]]:
    errs: List[str] = []
    warns: List[str] = []
    ids = _extract_card_ids(path, text)

    for f in REQUIRED_FIELDS:
        if not _has_field(text, f):
            errs.append(f"{path}: missing required field section/label '{f}'")

    # Verification status value
    m = re.search(r"verification status\s*:\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        val = _norm(m.group(1))
        if not any(x in val for x in ("unverified", "partially", "verified")):
            errs.append(f"{path}: verification status must include one of: unverified, partially, verified")
    else:
        # If provided as heading, try to locate value nearby
        if re.search(r"^\s*#+\s*verification status\b", text, flags=re.IGNORECASE | re.MULTILINE):
            block = re.split(r"^\s*#+\s*verification status\b", text, flags=re.IGNORECASE | re.MULTILINE)
            if len(block) > 1:
                after = block[1][:400].lower()
                if not any(x in after for x in ("unverified", "partially", "verified")):
                    warns.append(f"{path}: could not confirm verification status value (expected unverified/partially/verified)")
        else:
            # field missing already reported; no extra
            pass

    if not ids:
        warns.append(f"{path}: no claim card ID found (expected e.g. CC-001)")

    # Citations should contain something like URL/DOI or non-empty list
    if _has_field(text, "citations") and not (RE_URL.search(text) or RE_DOI.search(text)):
        # might be manual citations without urls; warn lightly
        warns.append(f"{path}: citations section present but no URL/DOI detected")

    return errs, warns, ids


def validate_claim_cards(card_paths: Sequence[Path]) -> Tuple[ValidationResult, Set[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    all_ids: Set[str] = set()

    files = _iter_md_files(card_paths)
    if not files:
        return ValidationResult(False, ["No claim card markdown files found."], []), set()

    for f in files:
        txt = _read_text(f)
        e, w, ids = validate_claim_card(f, txt)
        errors.extend(e)
        warnings.extend(w)
        all_ids |= ids

    # Duplicate IDs
    id_to_files: Dict[str, List[Path]] = {}
    for f in files:
        ids = _extract_card_ids(f, _read_text(f))
        for i in ids:
            id_to_files.setdefault(i, []).append(f)
    for i, fs in id_to_files.items():
        if len(fs) > 1:
            errors.append(f"Duplicate claim card ID '{i}' found in: {', '.join(str(x) for x in fs)}")

    return ValidationResult(not errors, errors, warnings), all_ids


def _discover_case_study_files(root: Path, user: Optional[str]) -> List[Path]:
    if user:
        p = (root / user) if not Path(user).is_absolute() else Path(user)
        if p.is_file():
            return [p]
        if p.is_dir():
            return _iter_md_files([p])
        # Glob relative to root
        matches = sorted(root.glob(user))
        if matches:
            return _iter_md_files(matches)
        return []
    # Heuristics for pilot
    heur = []
    for base in (root / "case_studies", root / "case-studies", root / "docs" / "case_studies", root / "docs" / "case-studies"):
        if base.is_dir():
            heur.extend(sorted(base.glob("*pilot*.md")))
            heur.extend(sorted(base.glob("pilot*.md")))
    # De-dup
    seen = set()
    out = []
    for f in heur:
        r = f.resolve()
        if r not in seen:
            seen.add(r)
            out.append(f)
    return out


def validate_case_study(path: Path, text: str, known_ids: Set[str]) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    # Identify "empirical claim" lines heuristically and require CC id.
    empirical_lines: List[Tuple[int, str]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        l = line.strip()
        if not l:
            continue
        if re.search(r"\bempirical\b", l, flags=re.IGNORECASE) and (l.startswith("-") or l.startswith("*") or l.lower().startswith("claim")):
            empirical_lines.append((idx, l))
        elif "[empirical]" in l.lower() or "(empirical)" in l.lower():
            empirical_lines.append((idx, l))

    if not empirical_lines:
        warnings.append(f"{path}: no empirical-claim markers found; skipping claim-to-card linkage check")
        return ValidationResult(True, errors, warnings)

    for ln, l in empirical_lines:
        ids = set(RE_CC_ID.findall(l))
        if not ids:
            errors.append(f"{path}:{ln}: empirical claim missing claim card ID (expected CC-...): {l}")
            continue
        unknown = sorted([i for i in ids if known_ids and i not in known_ids])
        if unknown:
            errors.append(f"{path}:{ln}: references unknown claim card ID(s): {', '.join(unknown)}")

    return ValidationResult(not errors, errors, warnings)


def _print_report(title: str, res: ValidationResult) -> None:
    if res.errors:
        print(f"{title}: FAIL")
        for e in res.errors:
            print(f"ERROR: {e}")
    else:
        print(f"{title}: OK")
    for w in res.warnings:
        print(f"WARN: {w}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="claim-cards", description="Validate claim cards and case study linkage.")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="Run required validation checks.")
    v.add_argument("--root", default=".", help="Project root (default: current directory)")
    v.add_argument("--claim-cards", nargs="*", default=None, help="Paths to claim card files/dirs (default: auto-discover)")
    v.add_argument("--case-study", default=None, help="Case study file/dir/glob to validate (default: discover pilot)")
    v.add_argument("--no-case-study", action="store_true", help="Skip case study validation")
    v.add_argument("--quiet", action="store_true", help="Suppress OK lines (still prints errors)")
    return p


def cmd_validate(args: argparse.Namespace) -> int:
    root = _find_repo_root(Path(args.root))

    if args.claim_cards:
        card_paths = [(root / p) if not Path(p).is_absolute() else Path(p) for p in args.claim_cards]
    else:
        dirs = _discover_claim_card_dirs(root)
        card_paths = dirs if dirs else []

    cc_res, known_ids = validate_claim_cards(card_paths)
    if not args.quiet or cc_res.errors:
        _print_report("CLAIM_CARDS", cc_res)

    exit_code = 0 if cc_res.ok else 2

    if not args.no_case_study:
        cs_files = _discover_case_study_files(root, args.case_study)
        if not cs_files:
            # Case study validation is required in the workflow; fail unless explicitly skipped.
            print("CASE_STUDY: FAIL")
            print("ERROR: No case study files found (provide --case-study or use --no-case-study to skip).")

            return max(exit_code, 3)

        cs_errors: List[str] = []
        cs_warnings: List[str] = []
        ok = True
        for f in cs_files:
            res = validate_case_study(f, _read_text(f), known_ids)
            ok = ok and res.ok
            cs_errors.extend(res.errors)
            cs_warnings.extend(res.warnings)

        cs_res = ValidationResult(ok, cs_errors, cs_warnings)
        if not args.quiet or cs_res.errors:
            _print_report("CASE_STUDY", cs_res)
        exit_code = max(exit_code, 0 if cs_res.ok else 4)

    return exit_code


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "validate":
        return cmd_validate(args)
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
