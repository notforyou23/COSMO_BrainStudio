from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
import csv
import json
from datetime import datetime, timezone

EXPORT_SCHEMA_VERSION = "1.0.0"
RESULTS_CSV_VERSION = "1.0.0"
RUN_REPORT_VERSION = "1.0.0"

DEFAULT_BUILD_ROOT = Path("runtime/_build")
DEFAULT_TABLES_DIR = DEFAULT_BUILD_ROOT / "tables"
DEFAULT_REPORTS_DIR = DEFAULT_BUILD_ROOT / "reports"

CSV_COLUMNS: Tuple[str, ...] = (
    "doi_input",
    "doi_normalized",
    "ok",
    "failure_category",
    "failure_reason",
    "provider",
    "provider_status",
    "resolved_url",
    "title",
    "publisher",
    "year",
    "authors",
    "metadata_json",
)

FAILURE_CATEGORY_FALLBACK = "unknown_error"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "ok", "success")
    return False


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _j(v: Any) -> str:
    try:
        return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return json.dumps({"unserializable": _safe_str(v)}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _pick(d: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _extract_metadata_fields(meta: Any) -> Dict[str, str]:
    if not isinstance(meta, Mapping):
        return {"title": "", "publisher": "", "year": "", "authors": ""}
    title = _pick(meta, "title", "container_title", "name", default="")
    if isinstance(title, list):
        title = title[0] if title else ""
    publisher = _pick(meta, "publisher", "publisher_name", default="")
    year = _pick(meta, "year", "published_year", "issued_year", "publication_year", default="")
    authors = _pick(meta, "authors", "author", default="")
    if isinstance(authors, list):
        parts = []
        for a in authors:
            if isinstance(a, Mapping):
                fam = _pick(a, "family", "last", "lastname", default="")
                giv = _pick(a, "given", "first", "firstname", default="")
                nm = (f"{giv} {fam}").strip() if (giv or fam) else _pick(a, "name", default="")
                if nm:
                    parts.append(nm)
            else:
                s = _safe_str(a).strip()
                if s:
                    parts.append(s)
        authors = "; ".join(parts)
    return {
        "title": _safe_str(title).strip(),
        "publisher": _safe_str(publisher).strip(),
        "year": _safe_str(year).strip(),
        "authors": _safe_str(authors).strip(),
    }


def _normalize_result(r: Mapping[str, Any]) -> Dict[str, Any]:
    doi_input = _pick(r, "doi_input", "doi", "input_doi", default="")
    doi_norm = _pick(r, "doi_normalized", "normalized_doi", "doi_norm", default="")
    ok = _as_bool(_pick(r, "ok", "success", "resolved", default=False))
    provider = _pick(r, "provider", "source", "resolver", default="")
    provider_status = _pick(r, "provider_status", "status_code", "http_status", default="")
    resolved_url = _pick(r, "resolved_url", "url", "landing_page", default="")
    failure_category = _pick(r, "failure_category", "error_category", "category", default="")
    failure_reason = _pick(r, "failure_reason", "error_reason", "reason", "message", default="")
    meta = _pick(r, "metadata", "meta", "record", default=None)

    if ok:
        failure_category = ""
        failure_reason = ""
    else:
        failure_category = _safe_str(failure_category).strip() or FAILURE_CATEGORY_FALLBACK
        failure_reason = _safe_str(failure_reason).strip() or "unspecified failure"

    fields = _extract_metadata_fields(meta)
    return {
        "doi_input": _safe_str(doi_input).strip(),
        "doi_normalized": _safe_str(doi_norm).strip(),
        "ok": ok,
        "failure_category": failure_category,
        "failure_reason": failure_reason,
        "provider": _safe_str(provider).strip(),
        "provider_status": _safe_str(provider_status).strip(),
        "resolved_url": _safe_str(resolved_url).strip(),
        "title": fields["title"],
        "publisher": fields["publisher"],
        "year": fields["year"],
        "authors": fields["authors"],
        "metadata_json": _j(meta) if meta is not None else "",
    }


def export_doi_results_csv(results: Iterable[Mapping[str, Any]], out_csv_path: Path) -> Dict[str, Any]:
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = [_normalize_result(r) for r in results]
    with out_csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(CSV_COLUMNS), extrasaction="ignore")
        w.writeheader()
        for row in rows:
            row = dict(row)
            row["ok"] = "1" if row.get("ok") else "0"
            w.writerow(row)
    return {"rows_written": len(rows), "path": str(out_csv_path)}


def export_doi_run_report_json(
    results: Iterable[Mapping[str, Any]],
    out_report_path: Path,
    run_meta: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    out_report_path.parent.mkdir(parents=True, exist_ok=True)
    norm = [_normalize_result(r) for r in results]
    total = len(norm)
    ok_n = sum(1 for r in norm if r["ok"])
    fail_n = total - ok_n
    by_category: Dict[str, int] = {}
    failures: List[Dict[str, str]] = []
    for r in norm:
        if r["ok"]:
            continue
        cat = r["failure_category"] or FAILURE_CATEGORY_FALLBACK
        by_category[cat] = by_category.get(cat, 0) + 1
        failures.append(
            {
                "doi_input": r["doi_input"],
                "doi_normalized": r["doi_normalized"],
                "failure_category": r["failure_category"],
                "failure_reason": r["failure_reason"],
                "provider": r["provider"],
                "provider_status": r["provider_status"],
            }
        )
    report = {
        "schema": {"name": "doi_run_report", "schema_version": EXPORT_SCHEMA_VERSION, "version": RUN_REPORT_VERSION},
        "generated_at_utc": _now_iso(),
        "run_meta": dict(run_meta or {}),
        "summary": {
            "total": total,
            "ok": ok_n,
            "failed": fail_n,
            "success_rate": (ok_n / total) if total else 0.0,
            "failures_by_category": dict(sorted(by_category.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
        "failures": failures,
    }
    out_report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"path": str(out_report_path), "total": total, "ok": ok_n, "failed": fail_n}


def export_doi_run_artifacts(
    results: Iterable[Mapping[str, Any]],
    build_root: Path = DEFAULT_BUILD_ROOT,
    run_meta: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    tables_dir = build_root / "tables"
    reports_dir = build_root / "reports"
    csv_path = tables_dir / "doi_results.csv"
    report_path = reports_dir / "doi_run_report.json"
    csv_info = export_doi_results_csv(results, csv_path)
    rpt_info = export_doi_run_report_json(results, report_path, run_meta=run_meta)
    return {"csv": csv_info, "report": rpt_info, "build_root": str(build_root)}
