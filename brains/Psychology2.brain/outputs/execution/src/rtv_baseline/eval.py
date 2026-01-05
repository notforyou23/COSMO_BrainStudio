from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


LABELS = ("SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                out.append(json.loads(s))
    return out


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


@dataclass
class EvalRow:
    rid: str
    gold: str
    pred: str
    abstain: bool
    conf: float
    correct: Optional[bool]
    quote_ok: Optional[bool]


def _merge_preds(data: List[Dict[str, Any]], preds: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if preds is None:
        return data
    pmap: Dict[str, Dict[str, Any]] = {}
    for r in preds:
        rid = str(r.get("id", r.get("rid", "")))
        if rid:
            pmap[rid] = r
    merged: List[Dict[str, Any]] = []
    for r in data:
        rid = str(r.get("id", r.get("rid", "")))
        pr = pmap.get(rid, {})
        rr = dict(r)
        for k in ("pred_label", "prediction", "pred", "label_pred", "confidence", "conf", "abstain", "abstained", "quote_ok"):
            if k in pr and k not in rr:
                rr[k] = pr[k]
        merged.append(rr)
    return merged


def _normalize_label(x: Any) -> str:
    s = str(x or "").strip().upper()
    aliases = {"SUPPORTED": "SUPPORTS", "SUPPORT": "SUPPORTS", "REFUTE": "REFUTES", "NEI": "NOT_ENOUGH_INFO", "UNKNOWN": "NOT_ENOUGH_INFO"}
    s = aliases.get(s, s)
    return s if s in LABELS else s


def _rows(records: List[Dict[str, Any]]) -> List[EvalRow]:
    out: List[EvalRow] = []
    for r in records:
        rid = str(r.get("id", r.get("rid", "")))
        gold = _normalize_label(r.get("gold_label", r.get("label", r.get("gold", ""))))
        pred = _normalize_label(r.get("pred_label", r.get("prediction", r.get("pred", r.get("label_pred", "")))))
        abst = bool(r.get("abstain", r.get("abstained", False)))
        conf = _clamp01(_safe_float(r.get("confidence", r.get("conf", 0.0)), 0.0))
        if abst:
            correct = None
        else:
            correct = (pred == gold) if (pred and gold) else None
        qok = r.get("quote_ok", r.get("quote_attribution_ok", None))
        quote_ok = None if qok is None else bool(qok)
        out.append(EvalRow(rid=rid, gold=gold, pred=pred, abstain=abst, conf=conf, correct=correct, quote_ok=quote_ok))
    return out


def _calibration(rows: List[EvalRow], bins: int = 10) -> Dict[str, Any]:
    rs = [r for r in rows if (r.correct is not None)]
    n = len(rs)
    if n == 0:
        return {"n": 0, "ece": None, "brier": None, "nll": None, "bins": []}
    ece = 0.0
    brier = 0.0
    nll = 0.0
    bin_counts = [0] * bins
    bin_conf = [0.0] * bins
    bin_acc = [0.0] * bins
    for r in rs:
        c = _clamp01(r.conf)
        y = 1.0 if r.correct else 0.0
        brier += (c - y) ** 2
        eps = 1e-12
        nll += -(y * math.log(max(c, eps)) + (1 - y) * math.log(max(1 - c, eps)))
        i = min(bins - 1, int(c * bins))
        bin_counts[i] += 1
        bin_conf[i] += c
        bin_acc[i] += y
    bins_out = []
    for i in range(bins):
        cnt = bin_counts[i]
        if cnt:
            avg_c = bin_conf[i] / cnt
            avg_a = bin_acc[i] / cnt
            ece += abs(avg_a - avg_c) * (cnt / n)
        else:
            avg_c = None
            avg_a = None
        lo = i / bins
        hi = (i + 1) / bins
        bins_out.append({"bin": i, "lo": lo, "hi": hi, "n": cnt, "avg_conf": avg_c, "avg_acc": avg_a})
    return {"n": n, "ece": ece, "brier": brier / n, "nll": nll / n, "bins": bins_out}


def _false_accept_at_risk(rows: List[EvalRow], risk_tiers: Iterable[float]) -> List[Dict[str, Any]]:
    rs = [r for r in rows if (r.correct is not None)]
    out: List[Dict[str, Any]] = []
    n = len(rs)
    for risk in risk_tiers:
        thr = 1.0 - float(risk)
        accepted = [r for r in rs if r.conf >= thr]
        a = len(accepted)
        fa = sum(1 for r in accepted if not r.correct)
        out.append({
            "risk": float(risk),
            "threshold": thr,
            "n_total_answered": n,
            "n_accepted": a,
            "coverage_over_answered": (a / n) if n else None,
            "false_accepts": fa,
            "false_accept_rate_over_accepted": (fa / a) if a else None,
            "false_accept_rate_over_answered": (fa / n) if n else None,
        })
    return out


def evaluate(data_path: Path, preds_path: Optional[Path], out_dir: Path) -> Dict[str, Any]:
    data = _read_jsonl(data_path)
    preds = _read_jsonl(preds_path) if preds_path else None
    merged = _merge_preds(data, preds)
    rows = _rows(merged)
    total = len(rows)
    answered = [r for r in rows if r.correct is not None]
    abstained = [r for r in rows if r.correct is None]
    n_ans = len(answered)
    n_abs = len(abstained)
    n_correct = sum(1 for r in answered if r.correct)
    n_incorrect = n_ans - n_correct

    quote_known = [r for r in answered if r.quote_ok is not None]
    quote_pass = sum(1 for r in quote_known if r.quote_ok)
    quote_rate = (quote_pass / len(quote_known)) if quote_known else None

    report: Dict[str, Any] = {
        "data_path": str(data_path),
        "preds_path": str(preds_path) if preds_path else None,
        "n_total": total,
        "n_answered": n_ans,
        "n_abstained": n_abs,
        "coverage": (n_ans / total) if total else None,
        "selective_accuracy": (n_correct / n_ans) if n_ans else None,
        "answered_correct": n_correct,
        "answered_incorrect": n_incorrect,
        "quote_attribution_pass_rate": quote_rate,
        "calibration": _calibration(rows, bins=10),
        "false_accept_at_risk_tiers": _false_accept_at_risk(rows, risk_tiers=(0.05, 0.1, 0.2, 0.3, 0.4)),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "report.json", report)

    with (out_dir / "per_record.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "gold", "pred", "abstain", "confidence", "correct", "quote_ok"])
        for r in rows:
            w.writerow([r.rid, r.gold, r.pred, int(r.abstain), f"{r.conf:.6f}", "" if r.correct is None else int(bool(r.correct)),
                        "" if r.quote_ok is None else int(bool(r.quote_ok))])
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="rtv-eval", description="Evaluate retrieve-then-verify outputs on a curated dataset.")
    ap.add_argument("--data", required=True, type=Path, help="JSONL dataset with gold labels; may include predictions.")
    ap.add_argument("--preds", default=None, type=Path, help="Optional JSONL predictions file keyed by id.")
    ap.add_argument("--out", required=True, type=Path, help="Output directory for report.json and per_record.csv")
    args = ap.parse_args(argv)
    evaluate(args.data, args.preds, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
