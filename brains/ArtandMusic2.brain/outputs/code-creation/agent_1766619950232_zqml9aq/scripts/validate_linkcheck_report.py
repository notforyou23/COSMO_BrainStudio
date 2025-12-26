from __future__ import annotations

from pathlib import Path
import json
import re
import sys
from datetime import datetime, timezone


def _die(msg: str, code: int = 2) -> None:
    print(f"VALIDATION_ERROR: {msg}")
    raise SystemExit(code)


def _read_json(path: Path):
    if not path.exists():
        _die(f"Missing required file: {path.as_posix()}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _die(f"Invalid JSON in {path.as_posix()}: {e}")


def _parse_iso8601(ts: str) -> None:
    if not isinstance(ts, str) or not ts.strip():
        _die("last_checked must be a non-empty string")
    t = ts.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(t)
    except Exception:
        _die(f"last_checked is not ISO-8601: {ts!r}")


def _compute_totals(items: list[dict]) -> dict:
    total = len(items)
    ok = 0
    redirected = 0
    broken = 0
    errors = 0
    for it in items:
        sc = it.get("status_code", None)
        err = it.get("error", None)
        chain = it.get("redirect_chain", [])
        if err:
            errors += 1
        if isinstance(chain, list) and len(chain) > 0:
            redirected += 1
        if isinstance(sc, int):
            if 200 <= sc < 400:
                ok += 1
            elif sc >= 400:
                broken += 1
        else:
            if err:
                broken += 1
    return {"total": total, "ok": ok, "redirected": redirected, "broken": broken, "errors": errors}


def _extract_summary_totals(md_text: str) -> dict:
    # Accept a variety of headings; require at least Total, OK, Broken.
    patterns = {
        "total": r"(?im)^\s*(?:Total|Links\s+checked)\s*:\s*(\d+)\s*$",
        "ok": r"(?im)^\s*(?:OK|Success(?:ful)?)\s*:\s*(\d+)\s*$",
        "redirected": r"(?im)^\s*(?:Redirected|Redirects)\s*:\s*(\d+)\s*$",
        "broken": r"(?im)^\s*(?:Broken|Failures?|Non-?OK)\s*:\s*(\d+)\s*$",
        "errors": r"(?im)^\s*(?:Errors?)\s*:\s*(\d+)\s*$",
    }
    out = {}
    for k, pat in patterns.items():
        m = re.search(pat, md_text)
        if m:
            out[k] = int(m.group(1))
    missing = [k for k in ("total", "ok", "broken") if k not in out]
    if missing:
        _die(f"LINKCHECK_SUMMARY.md missing totals fields: {', '.join(missing)}")
    return out


def validate(report_path: Path, summary_path: Path) -> None:
    report = _read_json(report_path)

    if not isinstance(report, dict):
        _die("linkcheck_report.json must be a JSON object at top-level")

    # Accept either 'results' or 'links'
    items = report.get("results", None)
    if items is None:
        items = report.get("links", None)
    if items is None:
        _die("linkcheck_report.json must contain 'results' or 'links' list")

    if not isinstance(items, list):
        _die("'results'/'links' must be a list")

    seen = set()
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            _die(f"Item {i} must be an object")
        url = it.get("url")
        if not isinstance(url, str) or not url.strip():
            _die(f"Item {i} missing non-empty string 'url'")
        if url in seen:
            _die(f"Duplicate url in report: {url}")
        seen.add(url)

        sc = it.get("status_code", None)
        if sc is not None and not isinstance(sc, int):
            _die(f"Item {i} status_code must be int or null")
        if isinstance(sc, int) and (sc < 100 or sc > 599):
            _die(f"Item {i} status_code out of range: {sc}")

        final_url = it.get("final_url", None)
        if final_url is not None and not isinstance(final_url, str):
            _die(f"Item {i} final_url must be string or null")

        chain = it.get("redirect_chain", [])
        if chain is None:
            chain = []
        if not isinstance(chain, list) or not all(isinstance(x, str) for x in chain):
            _die(f"Item {i} redirect_chain must be a list of strings")

        lc = it.get("last_checked", None)
        if lc is None:
            _die(f"Item {i} missing 'last_checked'")
        _parse_iso8601(lc)

        err = it.get("error", None)
        if err is not None and not isinstance(err, str):
            _die(f"Item {i} error must be string or null")

    computed = _compute_totals(items)

    # Validate report-provided totals if present
    rep_totals = report.get("totals", None)
    if rep_totals is not None:
        if not isinstance(rep_totals, dict):
            _die("report.totals must be an object")
        for k in ("total", "ok", "redirected", "broken", "errors"):
            if k in rep_totals:
                v = rep_totals[k]
                if not isinstance(v, int) or v < 0:
                    _die(f"report.totals.{k} must be a non-negative int")
                if v != computed[k]:
                    _die(f"report.totals.{k} mismatch: expected {computed[k]}, got {v}")

    if not summary_path.exists():
        _die(f"Missing required file: {summary_path.as_posix()}")
    md = summary_path.read_text(encoding="utf-8", errors="replace")
    summ = _extract_summary_totals(md)
    for k in ("total", "ok", "broken"):
        if summ[k] != computed[k]:
            _die(f"Summary {k} mismatch: expected {computed[k]}, got {summ[k]}")
    for k in ("redirected", "errors"):
        if k in summ and summ[k] != computed[k]:
            _die(f"Summary {k} mismatch: expected {computed[k]}, got {summ[k]}")

    # Basic recency sanity check: last_checked values should not be in the future by > 5 minutes
    now = datetime.now(timezone.utc)
    for it in items:
        t = it["last_checked"].strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if (dt - now).total_seconds() > 300:
            _die(f"last_checked appears to be in the future for url={it['url']}: {it['last_checked']}")

    print(f"VALIDATION_OK: totals={computed}")


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    report_path = root / "runtime" / "outputs" / "qa" / "linkcheck_report.json"
    summary_path = root / "runtime" / "outputs" / "qa" / "LINKCHECK_SUMMARY.md"
    if len(argv) >= 2:
        report_path = Path(argv[1]).expanduser().resolve()
    if len(argv) >= 3:
        summary_path = Path(argv[2]).expanduser().resolve()
    validate(report_path, summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
