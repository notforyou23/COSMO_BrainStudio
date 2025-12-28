#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Iterable, Optional

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".tif", ".tiff", ".bmp"}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    # Typical layout: <root>/src/verify_build_artifacts.py
    if here.parent.name == "src":
        return here.parent.parent
    return Path.cwd().resolve()


def _iter_files(dir_path: Path, exts: Iterable[str]) -> Iterable[Path]:
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    exts_l = {e.lower() for e in exts}
    return (p for p in dir_path.rglob("*") if p.is_file() and p.suffix.lower() in exts_l)


def _file_nonempty(p: Path) -> bool:
    try:
        return p.stat().st_size > 0
    except OSError:
        return False


def _json_nonempty(p: Path) -> bool:
    if not _file_nonempty(p):
        return False
    try:
        txt = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            txt = p.read_text(encoding="utf-8-sig")
        except Exception:
            return False
    except Exception:
        return False
    if not txt.strip():
        return False
    try:
        data = json.loads(txt)
    except Exception:
        return False
    if data is None or data == "" or data == [] or data == {}:
        return False
    return True


def _csv_nonempty(p: Path) -> bool:
    if not _file_nonempty(p):
        return False
    try:
        with p.open("r", encoding="utf-8", newline="") as f:
            r = csv.reader(f)
            for row in r:
                if any((c or "").strip() for c in row):
                    return True
    except UnicodeDecodeError:
        try:
            with p.open("r", encoding="utf-8-sig", newline="") as f:
                r = csv.reader(f)
                for row in r:
                    if any((c or "").strip() for c in row):
                        return True
        except Exception:
            return False
    except Exception:
        return False
    return False


def _find_first_valid(paths: Iterable[Path], predicate) -> Optional[Path]:
    for p in paths:
        if predicate(p):
            return p
    return None


def main(argv: list[str]) -> int:
    root = _repo_root()
    reports_dir = root / "runtime" / "_build" / "reports"
    tables_dir = root / "runtime" / "_build" / "tables"
    figures_dir = root / "runtime" / "_build" / "figures"

    json_files = list(_iter_files(reports_dir, [".json"]))
    csv_files = list(_iter_files(tables_dir, [".csv"]))
    img_files = list(_iter_files(figures_dir, IMAGE_EXTS))

    good_json = _find_first_valid(json_files, _json_nonempty)
    good_csv = _find_first_valid(csv_files, _csv_nonempty)
    good_img = _find_first_valid(img_files, _file_nonempty)

    missing = []
    if good_json is None:
        missing.append(f"non-empty JSON in {reports_dir.as_posix()}")
    if good_csv is None:
        missing.append(f"non-empty CSV in {tables_dir.as_posix()}")
    if good_img is None:
        missing.append(f"image file in {figures_dir.as_posix()}")

    if missing:
        sys.stderr.write("BUILD ARTIFACT VERIFICATION FAILED: missing " + ", ".join(missing) + "\n")
        sys.stderr.write(f"Found JSON: {len(json_files)}, CSV: {len(csv_files)}, Images: {len(img_files)}\n")
        return 1

    sys.stdout.write("BUILD ARTIFACT VERIFICATION PASSED\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
