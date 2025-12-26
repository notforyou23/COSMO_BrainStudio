#!/usr/bin/env python3
from __future__ import annotations
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA_DIR = ROOT / "outputs" / "qa"
LOGS_DIR = QA_DIR / "logs"

def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _run_and_tee(cmd: list[str], log_fp) -> tuple[int, str]:
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    out_parts: list[str] = []
    assert p.stdout is not None
    for line in p.stdout:
        out_parts.append(line)
        try:
            sys.stdout.write(line)
            sys.stdout.flush()
        except Exception:
            pass
        log_fp.write(line)
        log_fp.flush()
    rc = p.wait()
    return rc, "".join(out_parts)

def _parse_items(text: str) -> dict[str, list[str]]:
    missing, failed = [], []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(missing|failed)\b\s*[:\-]?(.*)$", line, flags=re.I)
        if m:
            current = m.group(1).lower()
            rest = m.group(2).strip(" :\t-")
            if rest:
                (missing if current == "missing" else failed).append(rest)
            continue
        m2 = re.match(r"^(?:\*\s*|\-\s*|\d+\.\s+)(.+)$", line)
        if current in ("missing", "failed") and m2:
            item = m2.group(1).strip()
            if item:
                (missing if current == "missing" else failed).append(item)
            continue
        m3 = re.match(r"^(MISSING|FAILED)\s*[:\-]\s*(.+)$", line)
        if m3:
            kind = m3.group(1).lower()
            item = m3.group(2).strip()
            if kind == "missing":
                missing.append(item)
            else:
                failed.append(item)
    def _dedupe(xs: list[str]) -> list[str]:
        seen, out = set(), []
        for x in xs:
            x2 = re.sub(r"\s+", " ", x).strip()
            if x2 and x2 not in seen:
                seen.add(x2); out.append(x2)
        return out
    return {"missing": _dedupe(missing), "failed": _dedupe(failed)}

def _write_summary(path: Path, status: str, rc_init: int, rc_val: int, items: dict[str, list[str]], ts: str) -> None:
    lines = [
        "# Outputs QA Summary",
        "",
        f"- Timestamp: `{ts}`",
        f"- Status: **{status}**",
        f"- init_outputs return code: `{rc_init}`",
        f"- validate_outputs return code: `{rc_val}`",
        "",
    ]
    if status != "PASS":
        if items.get("missing"):
            lines += ["## Missing items", ""] + [f"- {x}" for x in items["missing"]] + [""]
        if items.get("failed"):
            lines += ["## Failed items", ""] + [f"- {x}" for x in items["failed"]] + [""]
        if not items.get("missing") and not items.get("failed"):
            lines += ["## Notes", "", "- One or more QA steps returned non-zero but no missing/failed items were parsed from output.", ""]
    else:
        lines += ["## Notes", "", "- All checks passed.", ""]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

def main() -> int:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = _timestamp()
    log_path = LOGS_DIR / f"{ts}_run.log"

    scripts_dir = ROOT / "scripts"
    init_script = scripts_dir / "init_outputs.py"
    val_script = scripts_dir / "validate_outputs.py"
    if not init_script.exists() or not val_script.exists():
        missing = []
        if not init_script.exists(): missing.append(str(init_script))
        if not val_script.exists(): missing.append(str(val_script))
        QA_DIR.mkdir(parents=True, exist_ok=True)
        _write_summary(QA_DIR / "SUMMARY.md", "FAIL", 127, 127, {"missing": missing, "failed": ["Required script(s) not found."]}, ts)
        sys.stderr.write("ERROR: Required script(s) not found. See SUMMARY.md.\n")
        return 127

    with log_path.open("w", encoding="utf-8") as log_fp:
        log_fp.write(f"Outputs QA run @ {ts}\n")
        log_fp.write(f"Root: {ROOT}\n\n")

        rc_init, out_init = _run_and_tee([sys.executable, str(init_script)], log_fp)
        log_fp.write(f"\n[init_outputs exit code: {rc_init}]\n\n")
        rc_val, out_val = _run_and_tee([sys.executable, str(val_script)], log_fp)
        log_fp.write(f"\n[validate_outputs exit code: {rc_val}]\n")

    items = _parse_items(out_init + "\n" + out_val)
    status = "PASS" if (rc_init == 0 and rc_val == 0 and not items["missing"] and not items["failed"]) else "FAIL"
    QA_DIR.mkdir(parents=True, exist_ok=True)
    _write_summary(QA_DIR / "SUMMARY.md", status, rc_init, rc_val, items, ts)
    return 0 if status == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
