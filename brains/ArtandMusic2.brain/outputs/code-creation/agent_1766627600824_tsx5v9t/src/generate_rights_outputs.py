#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

CSV_COLUMNS = [
    "exemplar_id",
    "title",
    "creator",
    "source_url",
    "license_type",
    "proof_url/screenshot_ref",
    "usage_decision",
    "notes",
    "date_checked",
]

CHECKLIST_MD = """# Rights & Licensing Checklist

Use this checklist to verify rights clearance for each exemplar (image, document, audio, video, dataset, code, or other media) before publishing, distributing, or incorporating into derivative works.

## 1) Identify the exemplar
- [ ] Exemplar ID assigned (unique)
- [ ] Title/description recorded
- [ ] Creator/author/rights-holder recorded (if known)
- [ ] Source URL or repository location recorded
- [ ] Date accessed recorded

## 2) Determine rights status
- [ ] Is the work in the public domain? If yes, record basis (jurisdiction, date, source evidence)
- [ ] Is there a license? Record exact license name/version and link
- [ ] If no clear license: treat as "All rights reserved" until permission is obtained
- [ ] Check for embedded/third-party materials within the exemplar

## 3) Validate license terms (if licensed)
- [ ] License allows intended use (commercial/noncommercial, internal/external, distribution, modification)
- [ ] Attribution requirements understood and recorded
- [ ] Share-alike / copyleft obligations understood (if applicable)
- [ ] No additional restrictions (e.g., platform-specific terms) conflict with intended use
- [ ] For Creative Commons: verify deed + legal code match and note version (e.g., CC BY 4.0)

## 4) Obtain and store proof
- [ ] Save proof of license/permission (URL, screenshot, email, letter, invoice, or release form)
- [ ] Store proof reference (link/path) in the RIGHTS_LOG.csv
- [ ] Note any special conditions or expiration dates

## 5) Make a usage decision
- [ ] APPROVED: Use as-is under documented terms
- [ ] APPROVED WITH CONDITIONS: Use only with listed constraints (attribution text, scope limits, etc.)
- [ ] NEEDS REVIEW: Unclear license/terms; escalate for legal/rights review
- [ ] REJECTED: Do not use; document rationale

## 6) Recordkeeping
- [ ] Log entry created/updated in RIGHTS_LOG.csv
- [ ] Date checked recorded
- [ ] Re-check scheduled if source/license can change (e.g., web content)

---

## Suggested attribution format
"Title" by Creator, Source (URL), licensed under License (link). Changes: describe edits (if any).

## Notes
This checklist is a process aid and not legal advice. When in doubt, consult qualified counsel.
"""

def _resolve_out_dir(out_dir: str | None) -> Path:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    if out_dir:
        p = Path(out_dir)
        return (p if p.is_absolute() else (project_root / p)).resolve()
    return (project_root / "outputs" / "rights").resolve()

def _write_md(path: Path, overwrite: bool, append: bool) -> str:
    if path.exists() and not overwrite and not append:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite or not path.exists() else "a"
    with path.open(mode, encoding="utf-8", newline="") as f:
        if mode == "a":
            f.write("\n\n---\n\n")
        f.write(CHECKLIST_MD.strip() + "\n")
    return "written"

def _csv_has_header(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            first = next(reader, None)
        return first == CSV_COLUMNS
    except FileNotFoundError:
        return False

def _write_csv(path: Path, overwrite: bool, append: bool) -> str:
    if path.exists() and not overwrite and not append:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)

    if overwrite or not path.exists():
        with path.open("w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(CSV_COLUMNS)
        return "written"

    if append:
        if not _csv_has_header(path):
            raise SystemExit(f"Existing CSV header mismatch or missing: {path}")
        with path.open("a", encoding="utf-8", newline="") as f:
            row = {k: "" for k in CSV_COLUMNS}
            row["date_checked"] = date.today().isoformat()
            csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerow(row)
        return "appended"

    return "skipped"

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate rights checklist and rights log under outputs/rights.")
    ap.add_argument("--out-dir", default=None, help="Output directory (default: <project_root>/outputs/rights)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs (both MD and CSV).")
    ap.add_argument("--append", action="store_true", help="Append to existing outputs (MD appends checklist; CSV appends a blank row).")
    args = ap.parse_args(argv)

    if args.overwrite and args.append:
        raise SystemExit("Choose only one: --overwrite or --append")

    out_dir = _resolve_out_dir(args.out_dir)
    md_path = out_dir / "RIGHTS_AND_LICENSING_CHECKLIST.md"
    csv_path = out_dir / "RIGHTS_LOG.csv"

    md_status = _write_md(md_path, overwrite=args.overwrite, append=args.append)
    csv_status = _write_csv(csv_path, overwrite=args.overwrite, append=args.append)

    print(f"MD:{md_status}:{md_path}")
    print(f"CSV:{csv_status}:{csv_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
