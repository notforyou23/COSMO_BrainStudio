from pathlib import Path
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def runtime_qa_dir(root: Optional[Path] = None) -> Path:
    r = root or project_root()
    return r / "runtime" / "outputs" / "qa"


def report_path(root: Optional[Path] = None) -> Path:
    return runtime_qa_dir(root) / "linkcheck_report.json"


def summary_path(root: Optional[Path] = None) -> Path:
    return runtime_qa_dir(root) / "LINKCHECK_SUMMARY.md"


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def discover_case_study_json_files(root: Optional[Path] = None) -> List[Path]:
    r = (root or project_root()).resolve()
    candidate_dirs = [
        r / "case_studies",
        r / "case-studies",
        r / "case_study",
        r / "runtime" / "inputs",
        r / "data",
        r / "src" / "case_studies",
    ]
    found: List[Path] = []
    for d in candidate_dirs:
        if d.exists() and d.is_dir():
            found.extend(sorted(p for p in d.rglob("*.json") if p.is_file()))
    if found:
        return _filter_case_study_like(found)
    patterns = ["*.case_study.json", "*case*study*.json", "*case-study*.json"]
    for pat in patterns:
        found.extend(sorted(p for p in r.rglob(pat) if p.is_file()))
    return _filter_case_study_like(sorted(set(found)))


def _filter_case_study_like(paths: Iterable[Path]) -> List[Path]:
    out: List[Path] = []
    for p in paths:
        name = p.name.lower()
        if "case" in name and ("study" in name or "studies" in name):
            out.append(p)
    return out


def read_linkcheck_report(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or report_path()
    if not p.exists():
        return {"generated_at": None, "results": {}, "meta": {"schema": "linkcheck_report_v1"}}
    data = read_json(p)
    if not isinstance(data, dict):
        return {"generated_at": None, "results": {}, "meta": {"schema": "linkcheck_report_v1"}}
    data.setdefault("results", {})
    data.setdefault("meta", {}).setdefault("schema", "linkcheck_report_v1")
    return data


def write_linkcheck_report(report: Dict[str, Any], path: Optional[Path] = None) -> Path:
    p = path or report_path()
    report = dict(report or {})
    report.setdefault("meta", {}).setdefault("schema", "linkcheck_report_v1")
    report["generated_at"] = report.get("generated_at") or _iso_now()
    report.setdefault("results", {})
    write_json(p, report)
    return p


def render_markdown_summary(report: Dict[str, Any]) -> str:
    results = (report or {}).get("results") or {}
    rows = []
    ok = redirects = failed = 0
    for url in sorted(results.keys()):
        r = results.get(url) or {}
        status = r.get("status")
        final_url = r.get("final_url") or r.get("url") or url
        chain = r.get("redirect_chain") or []
        checked_at = r.get("checked_at") or r.get("last_checked") or ""
        err = r.get("error") or ""
        if isinstance(chain, list) and len(chain) > 0 and final_url != url:
            redirects += 1
        if isinstance(status, int) and 200 <= status < 400:
            ok += 1
        else:
            failed += 1
        rows.append((url, status, final_url, len(chain) if isinstance(chain, list) else 0, checked_at, err))
    gen = (report or {}).get("generated_at") or ""
    total = len(rows)
    lines = [
        "# Linkcheck Summary",
        "",
        f"- Generated at (UTC): `{gen}`",
        f"- Total URLs: `{total}`",
        f"- OK (2xx/3xx): `{ok}`",
        f"- Redirected: `{redirects}`",
        f"- Failed/Other: `{failed}`",
        "",
        "## Results",
        "",
        "| URL | Status | Final URL | Redirects | Last Checked | Error |",
        "|---|---:|---|---:|---|---|",
    ]
    for url, status, final_url, nredir, checked_at, err in rows:
        s = "" if status is None else str(status)
        lines.append(f"| {url} | {s} | {final_url} | {nredir} | {checked_at} | {err} |")
    lines.append("")
    return "\n".join(lines)


def write_markdown_summary(report: Dict[str, Any], path: Optional[Path] = None) -> Path:
    p = path or summary_path()
    ensure_parent(p)
    p.write_text(render_markdown_summary(report), encoding="utf-8")
    return p
