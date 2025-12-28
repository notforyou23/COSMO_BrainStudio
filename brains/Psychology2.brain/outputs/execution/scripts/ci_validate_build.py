"""ci_validate_build.py

Standalone CI validator for runtime/_build outputs.

Checks:
- runtime/_build/{reports,tables,figures,logs} exist and are non-empty (recursively).
- tables: CSV/TSV have parseable headers; JSON is loadable; parquet presence is allowed.
- logs: UTF-8 decodable.
- figures: valid PNG/JPG/GIF/BMP/TIFF via PIL if available; SVG parseable XML.
- reports: non-empty; HTML/MD decodable; PDF has signature.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

REQUIRED_SUBDIRS = ("reports", "tables", "figures", "logs")


def _iter_files(p: Path):
    for f in p.rglob("*"):
        if f.is_file() and not any(part.startswith(".") for part in f.parts):
            yield f


def _nonempty_dir(p: Path) -> bool:
    return any(True for _ in _iter_files(p))


def _read_bytes(p: Path, limit: int | None = None) -> bytes:
    b = p.read_bytes()
    return b if limit is None else b[:limit]


def _is_utf8_decodable(p: Path) -> bool:
    try:
        p.read_text(encoding="utf-8")
        return True
    except Exception:
        return False


def _validate_csv_tsv(p: Path, delimiter: str) -> None:
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = next(reader, None)
    if not header or not any(str(h).strip() for h in header):
        raise ValueError(f"missing/blank header: {p}")


def _validate_json(p: Path) -> None:
    with p.open("r", encoding="utf-8") as f:
        json.load(f)


def _validate_svg(p: Path) -> None:
    data = p.read_text(encoding="utf-8")
    if "<svg" not in data.lower():
        raise ValueError(f"not an svg: {p}")
    ET.fromstring(data)


def _validate_image(p: Path) -> None:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        b = _read_bytes(p, 16)
        if p.suffix.lower() == ".png" and not b.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"invalid png signature: {p}")
        if p.suffix.lower() in (".jpg", ".jpeg") and not (b.startswith(b"\xff\xd8") and b.endswith(b"\xff\xd9")):
            # allow truncated read; only check SOI
            if not b.startswith(b"\xff\xd8"):
                raise ValueError(f"invalid jpeg signature: {p}")
        return
    with Image.open(p) as im:
        im.verify()


def validate_build(build_dir: Path) -> None:
    if not build_dir.exists():
        raise FileNotFoundError(f"build dir not found: {build_dir}")

    missing = [d for d in REQUIRED_SUBDIRS if not (build_dir / d).is_dir()]
    if missing:
        raise FileNotFoundError(f"missing required subdirs: {missing}")

    for d in REQUIRED_SUBDIRS:
        sub = build_dir / d
        if not _nonempty_dir(sub):
            raise FileNotFoundError(f"required subdir empty: {sub}")

    # Validate tables
    table_files = list(_iter_files(build_dir / "tables"))
    if not table_files:
        raise FileNotFoundError("no table files found")
    for p in table_files:
        suf = p.suffix.lower()
        if suf == ".csv":
            _validate_csv_tsv(p, ",")
        elif suf == ".tsv":
            _validate_csv_tsv(p, "\t")
        elif suf == ".json":
            _validate_json(p)
        elif suf in (".parquet", ".pq"):
            if p.stat().st_size == 0:
                raise ValueError(f"empty parquet: {p}")
        else:
            if p.stat().st_size == 0:
                raise ValueError(f"empty table artifact: {p}")

    # Validate logs
    log_files = list(_iter_files(build_dir / "logs"))
    if not log_files:
        raise FileNotFoundError("no log files found")
    for p in log_files:
        if p.stat().st_size == 0:
            raise ValueError(f"empty log: {p}")
        if p.suffix.lower() in (".log", ".txt", ".out", ".err", ".md", ".json", ".yaml", ".yml", ".csv", ".tsv"):
            if not _is_utf8_decodable(p):
                raise ValueError(f"log not utf-8 decodable: {p}")

    # Validate figures
    fig_files = list(_iter_files(build_dir / "figures"))
    if not fig_files:
        raise FileNotFoundError("no figure files found")
    for p in fig_files:
        if p.stat().st_size == 0:
            raise ValueError(f"empty figure: {p}")
        suf = p.suffix.lower()
        if suf in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"):
            _validate_image(p)
        elif suf == ".svg":
            _validate_svg(p)

    # Validate reports
    rep_files = list(_iter_files(build_dir / "reports"))
    if not rep_files:
        raise FileNotFoundError("no report files found")
    for p in rep_files:
        if p.stat().st_size == 0:
            raise ValueError(f"empty report: {p}")
        suf = p.suffix.lower()
        if suf in (".html", ".htm", ".md", ".txt"):
            if not _is_utf8_decodable(p):
                raise ValueError(f"report not utf-8 decodable: {p}")
        elif suf == ".pdf":
            if not _read_bytes(p, 5).startswith(b"%PDF-"):
                raise ValueError(f"invalid pdf signature: {p}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate runtime/_build outputs for CI.")
    ap.add_argument("--build-dir", default="runtime/_build", help="Path to build directory (default: runtime/_build).")
    args = ap.parse_args(argv)

    build_dir = Path(args.build_dir)
    try:
        validate_build(build_dir)
    except Exception as e:
        print(f"CI_VALIDATE_BUILD:FAIL:{e}", file=sys.stderr)
        return 1

    print(f"CI_VALIDATE_BUILD:OK:{build_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
