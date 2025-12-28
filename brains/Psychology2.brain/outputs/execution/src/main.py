import argparse, json, re, random, math
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")

def _tok(s: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(s or "")]

def _sentences(text: str) -> List[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[\.\!\?])\s+|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]

def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa:
        return 0.0
    inter = len(sa & sb)
    return inter / max(1, len(sa | sb))

def _recall(a: List[str], b: List[str]) -> float:
    # how much of a appears in b
    sa, sb = set(a), set(b)
    if not sa:
        return 0.0
    return len(sa & sb) / len(sa)

def _numbers(s: str) -> List[str]:
    return _NUM_RE.findall(s or "")

def _best_quote(claim: str, passage: str) -> Tuple[str, float]:
    ct = _tok(claim)
    best_q, best = "", 0.0
    for sent in _sentences(passage)[:80]:
        st = _tok(sent)
        score = 0.75 * _recall(ct, st) + 0.25 * _jaccard(ct, st)
        if score > best:
            best, best_q = score, sent
    return best_q, float(best)

def _retrieve(claim: str, passages: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    ct = _tok(claim)
    cset = set(ct)
    scored = []
    for p in passages:
        txt = (p or {}).get("text") or ""
        pt = _tok(txt)
        if not pt:
            continue
        pset = set(pt)
        overlap = len(cset & pset)
        score = overlap / math.sqrt(max(1, len(pset)))
        scored.append((float(score), p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:max(1, top_k)]]

@dataclass
class ClaimAudit:
    claim: str
    predicted_supported: bool
    quote_score: float
    threshold: float
    passage_id: Optional[str]
    quote: Optional[str]
    failures: List[str]

def verify_claim(claim: str, passages: List[Dict[str, Any]], top_k: int, quote_threshold: float) -> ClaimAudit:
    failures: List[str] = []
    retrieved = _retrieve(claim, passages, top_k=top_k)
    if not retrieved:
        return ClaimAudit(claim, False, 0.0, quote_threshold, None, None, ["no_retrieved_passages"])
    best = ("", 0.0, None, None)  # quote, score, pid, ptext
    for p in retrieved:
        quote, score = _best_quote(claim, (p or {}).get("text") or "")
        pid = (p or {}).get("id")
        if score > best[1]:
            best = (quote, score, pid, (p or {}).get("text") or "")
    quote, score, pid, _ = best
    if score < quote_threshold:
        failures.append("low_quote_alignment")
    cn = _numbers(claim)
    if cn and not all(n in (quote or "") for n in cn):
        failures.append("number_mismatch")
    supported = (not failures) and bool(quote)
    return ClaimAudit(claim, supported, float(score), float(quote_threshold), pid, quote or None, failures)

def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def _write_jsonl(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def _get_item_passages(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    src = item.get("sources") or item.get("passages") or []
    out = []
    for i, p in enumerate(src):
        if isinstance(p, str):
            out.append({"id": str(i), "text": p})
        else:
            out.append({"id": str(p.get("id", i)), "text": p.get("text") or ""})
    return out

def _get_claims(item: Dict[str, Any]) -> List[str]:
    c = item.get("claims")
    if isinstance(c, list) and c:
        return [str(x) for x in c]
    if "claim" in item:
        return [str(item["claim"])]
    if "question" in item:
        return [str(item["question"])]
    return []

def _get_labels(item: Dict[str, Any], n: int) -> Optional[List[int]]:
    # supports: claim_labels (list), labels (list), label (bool/int)
    for k in ("claim_labels", "labels"):
        v = item.get(k)
        if isinstance(v, list) and len(v) == n:
            return [int(bool(x)) for x in v]
    if "label" in item:
        y = int(bool(item["label"]))
        return [y] * n
    return None

def _f1(y_true: List[int], y_pred: List[int]) -> float:
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    if tp == 0 and (fp > 0 or fn > 0):
        return 0.0
    if tp == 0 and fp == 0 and fn == 0:
        return 0.0
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)

def calibrate_threshold(items: List[Dict[str, Any]], heldout_idx: List[int], top_k: int) -> float:
    ys, scores = [], []
    for idx in heldout_idx:
        it = items[idx]
        passages = _get_item_passages(it)
        claims = _get_claims(it)
        labels = _get_labels(it, len(claims))
        if not claims or labels is None:
            continue
        for c, y in zip(claims, labels):
            # compute best possible quote score from retrieved set without thresholding
            retrieved = _retrieve(c, passages, top_k=top_k)
            best = 0.0
            for p in retrieved:
                _, s = _best_quote(c, (p or {}).get("text") or "")
                best = max(best, s)
            ys.append(int(y))
            scores.append(float(best))
    if not ys:
        return 0.5
    best_thr, best_f1 = 0.5, -1.0
    for i in range(2, 20):  # 0.10 .. 0.95
        thr = i * 0.05
        pred = [1 if s >= thr else 0 for s in scores]
        f1 = _f1(ys, pred)
        if f1 > best_f1 + 1e-12 or (abs(f1 - best_f1) <= 1e-12 and thr > best_thr):
            best_f1, best_thr = f1, thr
    return float(best_thr)

def run(input_path: Path, output_dir: Path, top_k: int, heldout_frac: float, seed: int):
    items = list(_iter_jsonl(input_path))
    n = len(items)
    rng = random.Random(seed)
    idxs = list(range(n))
    rng.shuffle(idxs)
    h = max(1, int(round(n * heldout_frac))) if n else 0
    heldout = idxs[:h]
    thr = calibrate_threshold(items, heldout, top_k=top_k)
    decisions, audits = [], []
    for it in items:
        item_id = str(it.get("id") or it.get("qid") or it.get("uuid") or "")
        passages = _get_item_passages(it)
        claims = _get_claims(it)
        claim_audits = []
        for c in claims:
            ca = verify_claim(c, passages, top_k=top_k, quote_threshold=thr)
            claim_audits.append(ca)
            audits.append({
                "item_id": item_id,
                "claim": ca.claim,
                "predicted_supported": ca.predicted_supported,
                "quote_score": ca.quote_score,
                "threshold": ca.threshold,
                "passage_id": ca.passage_id,
                "quote": ca.quote,
                "failures": ca.failures,
            })
        item_supported = all(ca.predicted_supported for ca in claim_audits) if claim_audits else False
        decisions.append({
            "item_id": item_id,
            "predicted_supported": item_supported,
            "threshold": thr,
            "claims": [asdict(ca) for ca in claim_audits],
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "decisions.jsonl", decisions)
    _write_jsonl(output_dir / "audit.jsonl", audits)
    (output_dir / "calibration.json").write_text(json.dumps({"threshold": thr, "heldout_frac": heldout_frac, "seed": seed, "top_k": top_k}, indent=2), encoding="utf-8")
    print(json.dumps({"status":"ok","n_items":n,"heldout_n":len(heldout),"threshold":thr,"out":str(output_dir)}, ensure_ascii=False))

def main():
    ap = argparse.ArgumentParser(description="Retrieve-then-verify with quote-level alignment, deterministic checks, and calibrated thresholds.")
    ap.add_argument("--input", required=True, help="Path to dataset JSONL.")
    ap.add_argument("--output_dir", required=True, help="Output directory for decisions and audit logs.")
    ap.add_argument("--top_k", type=int, default=5, help="Number of passages to retrieve per claim.")
    ap.add_argument("--heldout_frac", type=float, default=0.2, help="Fraction of items used for threshold calibration.")
    ap.add_argument("--seed", type=int, default=13, help="Random seed for heldout split.")
    args = ap.parse_args()
    run(Path(args.input), Path(args.output_dir), top_k=args.top_k, heldout_frac=args.heldout_frac, seed=args.seed)

if __name__ == "__main__":
    main()
