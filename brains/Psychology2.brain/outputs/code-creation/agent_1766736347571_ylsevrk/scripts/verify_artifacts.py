from __future__ import annotations
from pathlib import Path
import json
import sys
from datetime import datetime, timezone

REQUIRED_ARTIFACTS = [
    "runtime/_build/logs/run.log",
    "runtime/_build/manifest.json",
    "runtime/_build/validation/taxonomy_report.json",
    "runtime/_build/meta_analysis/summary_table.csv",
    "runtime/_build/meta_analysis/forest_plot.png",
]

def _artifact_status(root: Path, rel_path: str) -> dict:
    p = root / rel_path
    exists = p.exists() and p.is_file()
    size = p.stat().st_size if exists else 0
    non_empty = bool(exists and size > 0)
    return {
        "path": rel_path,
        "absolute_path": str(p),
        "exists": exists,
        "size_bytes": int(size),
        "non_empty": non_empty,
        "status": "pass" if non_empty else "fail",
    }

def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    details = [_artifact_status(root, rp) for rp in REQUIRED_ARTIFACTS]
    overall_pass = all(d["status"] == "pass" for d in details)

    report = {
        "tool": "verify_artifacts.py",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "overall_status": "pass" if overall_pass else "fail",
        "artifacts": details,
    }

    out_path = root / "runtime/_build/verification_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Minimal console output
    if not overall_pass:
        failing = [d["path"] for d in details if d["status"] != "pass"]
        print("VERIFICATION_FAIL:" + ",".join(failing))
        return 1
    print("VERIFICATION_PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
