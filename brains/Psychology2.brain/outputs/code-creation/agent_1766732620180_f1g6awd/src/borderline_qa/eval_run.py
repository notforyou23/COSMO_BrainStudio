from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _to_id_map(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        i = r.get("id") or r.get("qid") or r.get("example_id")
        if i is None:
            continue
        out[str(i)] = r
    return out


def _normalize_url_or_doi(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if s.lower().startswith("doi:"):
        return "doi:" + s[4:].strip()
    return s


def _validate_citations(answer: str, citations: Any) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    if citations is None:
        return False, ["citations_missing"]
    if not isinstance(citations, list) or not citations:
        return False, ["citations_empty_or_not_list"]
    if not isinstance(answer, str):
        return False, ["answer_not_str"]
    n = len(answer)
    for idx, c in enumerate(citations):
        if not isinstance(c, dict):
            errs.append(f"c[{idx}]_not_object")
            continue
        quote = c.get("quote")
        span = c.get("span")
        u = _normalize_url_or_doi(c.get("url") or c.get("URL") or c.get("doi") or c.get("DOI") or c.get("source"))
        if not quote or not isinstance(quote, str):
            errs.append(f"c[{idx}]_quote_missing")
        if not u:
            errs.append(f"c[{idx}]_url_or_doi_missing")
        if not (isinstance(span, (list, tuple)) and len(span) == 2 and all(isinstance(x, int) for x in span)):
            errs.append(f"c[{idx}]_span_invalid")
            continue
        a, b = int(span[0]), int(span[1])
        if not (0 <= a <= b <= n):
            errs.append(f"c[{idx}]_span_oob")
            continue
        if quote and isinstance(quote, str):
            if answer[a:b] != quote:
                errs.append(f"c[{idx}]_span_quote_mismatch")
            if quote not in answer:
                errs.append(f"c[{idx}]_quote_not_in_answer")
    return (len(errs) == 0), errs


def _is_correct(ex: Dict[str, Any], pred: Dict[str, Any]) -> bool:
    if "is_correct" in pred:
        return bool(pred["is_correct"])
    gold = ex.get("gold") or ex.get("gold_answer") or ex.get("answer")
    pa = pred.get("answer") or pred.get("prediction") or pred.get("output")
    if isinstance(gold, str) and isinstance(pa, str):
        return gold.strip().lower() == pa.strip().lower()
    if isinstance(gold, list) and isinstance(pa, str):
        p = pa.strip().lower()
        return any(isinstance(g, str) and g.strip().lower() == p for g in gold)
    return False


def _confidence(pred: Dict[str, Any]) -> float:
    c = pred.get("confidence")
    if isinstance(c, (int, float)):
        return float(c)
    c = pred.get("score")
    if isinstance(c, (int, float)):
        return float(c)
    return 0.0


@dataclass
class SelectiveMetrics:
    threshold: float
    coverage: float
    accuracy_on_accepted: float
    false_accept_rate: float
    false_accept_overall: float
    accepted: int
    total: int


def _selective_metrics(rows: List[Tuple[bool, float, bool]]) -> List[SelectiveMetrics]:
    # rows: (correct, confidence, cite_ok)
    thresholds = [i / 20 for i in range(0, 21)]
    out: List[SelectiveMetrics] = []
    total = len(rows)
    for t in thresholds:
        accepted_mask = [(c, conf, cite_ok) for (c, conf, cite_ok) in rows if conf >= t and cite_ok]
        acc_n = sum(1 for (c, _, __) in accepted_mask if c)
        rej_n = total - len(accepted_mask)
        acc_d = max(1, len(accepted_mask))
        false_acc_n = sum(1 for (c, _, __) in accepted_mask if not c)
        out.append(SelectiveMetrics(
            threshold=t,
            coverage=(len(accepted_mask) / total) if total else 0.0,
            accuracy_on_accepted=(acc_n / acc_d),
            false_accept_rate=(false_acc_n / acc_d),
            false_accept_overall=(false_acc_n / total) if total else 0.0,
            accepted=len(accepted_mask),
            total=total,
        ))
    return out


def _run(dataset_path: Path, self_pred_path: Path, rtv_pred_path: Path, out_path: Optional[Path]) -> Dict[str, Any]:
    ds = _read_jsonl(dataset_path)
    ds_map = _to_id_map(ds)
    self_map = _to_id_map(_read_jsonl(self_pred_path))
    rtv_map = _to_id_map(_read_jsonl(rtv_pred_path))

    def build_rows(pred_map: Dict[str, Dict[str, Any]], enforce_cite: bool) -> Tuple[List[Tuple[bool, float, bool]], Dict[str, Any]]:
        rows: List[Tuple[bool, float, bool]] = []
        cite_fail = 0
        missing = 0
        for i, ex in ds_map.items():
            pred = pred_map.get(i)
            if not pred:
                missing += 1
                continue
            correct = _is_correct(ex, pred)
            conf = _confidence(pred)
            cite_ok = True
            if enforce_cite:
                ans = pred.get("answer") or pred.get("prediction") or pred.get("output") or ""
                cite_ok, _errs = _validate_citations(str(ans), pred.get("citations"))
                if not cite_ok:
                    cite_fail += 1
            rows.append((correct, conf, cite_ok))
        meta = {"n_dataset": len(ds_map), "n_scored": len(rows), "n_missing_pred": missing, "n_citation_fail": cite_fail}
        return rows, meta

    self_rows, self_meta = build_rows(self_map, enforce_cite=False)
    rtv_rows, rtv_meta = build_rows(rtv_map, enforce_cite=True)

    self_sel = _selective_metrics(self_rows)
    rtv_sel = _selective_metrics(rtv_rows)

    # main comparison at tau=0.5
    def pick(sel: List[SelectiveMetrics], tau: float = 0.5) -> Dict[str, Any]:
        m = min(sel, key=lambda x: abs(x.threshold - tau)) if sel else None
        return {} if m is None else {
            "threshold": m.threshold, "coverage": m.coverage, "accuracy_on_accepted": m.accuracy_on_accepted,
            "false_accept_rate": m.false_accept_rate, "false_accept_overall": m.false_accept_overall,
            "accepted": m.accepted, "total": m.total
        }

    report: Dict[str, Any] = {
        "dataset": str(dataset_path),
        "self_conf_prompting": {"meta": self_meta, "at_0_5": pick(self_sel, 0.5), "selective_curve": [m.__dict__ for m in self_sel]},
        "retrieve_then_verify_must_cite": {"meta": rtv_meta, "at_0_5": pick(rtv_sel, 0.5), "selective_curve": [m.__dict__ for m in rtv_sel]},
    }

    # delta false-accept at 0.5 (lower is better)
    s = report["self_conf_prompting"]["at_0_5"]
    r = report["retrieve_then_verify_must_cite"]["at_0_5"]
    if s and r:
        report["comparison_at_0_5"] = {
            "delta_false_accept_rate": r["false_accept_rate"] - s["false_accept_rate"],
            "delta_coverage": r["coverage"] - s["coverage"],
            "delta_accuracy_on_accepted": r["accuracy_on_accepted"] - s["accuracy_on_accepted"],
        }

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(prog="borderline-qa-eval", description="Run borderline QA harness with self-confidence vs retrieve-then-verify must-cite.")
    ap.add_argument("--dataset", type=Path, required=True, help="JSONL dataset with id and gold/gold_answer/answer fields.")
    ap.add_argument("--self", dest="self_pred", type=Path, required=True, help="JSONL predictions (id, answer/prediction, confidence).")
    ap.add_argument("--rtv", dest="rtv_pred", type=Path, required=True, help="JSONL predictions (id, answer/prediction, confidence, citations).")
    ap.add_argument("--out", type=Path, default=None, help="Write JSON report to this path.")
    args = ap.parse_args(argv)
    rep = _run(args.dataset, args.self_pred, args.rtv_pred, args.out)
    # brief stdout summary for CLI use
    def brief(name: str, block: Dict[str, Any]) -> str:
        at = block.get("at_0_5") or {}
        return f"{name}: cov={at.get('coverage', 0):.3f} acc={at.get('accuracy_on_accepted', 0):.3f} far={at.get('false_accept_rate', 0):.3f}"
    print(brief("self", rep["self_conf_prompting"]))
    print(brief("rtv", rep["retrieve_then_verify_must_cite"]))
    if "comparison_at_0_5" in rep:
        c = rep["comparison_at_0_5"]
        print(f"delta_far={c['delta_false_accept_rate']:.3f} delta_cov={c['delta_coverage']:.3f} delta_acc={c['delta_accuracy_on_accepted']:.3f}")


if __name__ == "__main__":
    main()
