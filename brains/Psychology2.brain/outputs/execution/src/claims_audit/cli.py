"""claims_audit.cli

Small CLI to:
- validate inputs,
- build/load a TF-IDF retrieval index over a curated reference corpus,
- run claim-level audits (supported/unsupported/insufficient),
- compute tiered false-accept/abstain metrics.

File formats (JSONL):
- corpus.jsonl: {id, text, label?} where label in {supported, unsupported}; omit/other -> insufficient
- claims.jsonl: {id, text, predicted_label?} where predicted_label in {supported, unsupported, insufficient}
"""

from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception as e:  # pragma: no cover
    TfidfVectorizer = None


LABELS = ("supported", "unsupported", "insufficient")


def _norm_label(x: Any) -> str:
    s = (str(x).strip().lower() if x is not None else "")
    if s in ("support", "supported", "true", "yes"):
        return "supported"
    if s in ("refute", "refuted", "unsupported", "false", "no", "contradicted", "contradiction"):
        return "unsupported"
    if s in ("insufficient", "unknown", "unclear", "abstain", "n/a", "na", ""):
        return "insufficient"
    raise ValueError(f"Invalid label: {x!r}; expected one of {LABELS}")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                raise ValueError(f"{path}:{i} invalid JSON: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{i} expected JSON object per line")
            rows.append(obj)
    return rows


def _require_fields(rows: List[Dict[str, Any]], path: Path, fields: Iterable[str]) -> None:
    for i, r in enumerate(rows, 1):
        for k in fields:
            if k not in r:
                raise ValueError(f"{path}:{i} missing required field {k!r}")


@dataclass
class Index:
    vectorizer: Any
    matrix: Any
    corpus: List[Dict[str, Any]]


def build_index(corpus_path: Path) -> Index:
    if TfidfVectorizer is None:
        raise RuntimeError("scikit-learn not available; cannot build TF-IDF index")
    corpus = _read_jsonl(corpus_path)
    _require_fields(corpus, corpus_path, ("id", "text"))
    texts = [str(r.get("text", "")) for r in corpus]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    X = vec.fit_transform(texts)
    return Index(vectorizer=vec, matrix=X, corpus=corpus)


def save_index(index: Index, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        pickle.dump(index, f)


def load_index(path: Path) -> Index:
    with path.open("rb") as f:
        obj = pickle.load(f)
    if not isinstance(obj, Index):
        # backward-compatible: stored as dict
        if isinstance(obj, dict) and {"vectorizer", "matrix", "corpus"} <= set(obj.keys()):
            return Index(vectorizer=obj["vectorizer"], matrix=obj["matrix"], corpus=obj["corpus"])
        raise ValueError(f"Invalid index file: {path}")
    return obj


def retrieve(index: Index, query_text: str, top_k: int = 5) -> List[Tuple[float, Dict[str, Any]]]:
    q = index.vectorizer.transform([query_text])
    scores = (index.matrix @ q.T).toarray().ravel()
    if scores.size == 0:
        return []
    k = int(min(max(top_k, 1), scores.size))
    idx = np.argpartition(-scores, k - 1)[:k]
    idx = idx[np.argsort(-scores[idx])]
    return [(float(scores[i]), index.corpus[int(i)]) for i in idx]


def audit_claim(claim_text: str, hits: List[Tuple[float, Dict[str, Any]]], sim_threshold: float) -> Tuple[str, float, Optional[str]]:
    if not hits:
        return "insufficient", 0.0, None
    top_sim, top_doc = hits[0]
    if top_sim < sim_threshold:
        return "insufficient", float(top_sim), str(top_doc.get("id"))
    doc_label = _norm_label(top_doc.get("label", "insufficient"))
    # Only allow supported/unsupported to be asserted from corpus; otherwise abstain.
    if doc_label not in ("supported", "unsupported"):
        doc_label = "insufficient"
    return doc_label, float(top_sim), str(top_doc.get("id"))


def tier_for_sim(sim: float) -> str:
    if sim >= 0.55:
        return "high"
    if sim >= 0.35:
        return "mid"
    return "low"


def compute_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    # rows: {tier, predicted_label, audited_label}
    def agg(sub: List[Dict[str, Any]]) -> Dict[str, float]:
        n = len(sub)
        if n == 0:
            return {"n": 0}
        pred_sup = sum(r["predicted_label"] == "supported" for r in sub)
        pred_uns = sum(r["predicted_label"] == "unsupported" for r in sub)
        pred_ins = sum(r["predicted_label"] == "insufficient" for r in sub)
        false_accept = sum(
            (r["predicted_label"] in ("supported", "unsupported")) and (r["predicted_label"] != r["audited_label"])
            for r in sub
        )
        correct = sum(r["predicted_label"] == r["audited_label"] for r in sub)
        # "abstain" when prediction is insufficient (regardless of audited)
        abstain = pred_ins
        # "strict accuracy": insufficient counts as a normal class
        strict_acc = correct / n
        # "selective accuracy": among non-abstains only; NaN if none
        denom = n - abstain
        sel_acc = (sum(
            (r["predicted_label"] in ("supported", "unsupported")) and (r["predicted_label"] == r["audited_label"])
            for r in sub
        ) / denom) if denom > 0 else float("nan")
        return {
            "n": n,
            "pred_supported": pred_sup,
            "pred_unsupported": pred_uns,
            "pred_insufficient": pred_ins,
            "false_accept_rate": false_accept / n,
            "abstain_rate": abstain / n,
            "strict_accuracy": strict_acc,
            "selective_accuracy": sel_acc,
        }

    tiers = sorted(set(r["tier"] for r in rows))
    out: Dict[str, Any] = {"overall": agg(rows), "by_tier": {}}
    for t in tiers:
        out["by_tier"][t] = agg([r for r in rows if r["tier"] == t])
    return out


def cmd_build(args: argparse.Namespace) -> int:
    corpus_path = Path(args.corpus)
    index_path = Path(args.index)
    if not corpus_path.is_file():
        raise SystemExit(f"Corpus not found: {corpus_path}")
    idx = build_index(corpus_path)
    save_index(idx, index_path)
    print(json.dumps({"status": "ok", "action": "build", "corpus": str(corpus_path), "index": str(index_path), "n": len(idx.corpus)}))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    claims_path = Path(args.claims)
    index_path = Path(args.index)
    out_path = Path(args.out) if args.out else None
    if not claims_path.is_file():
        raise SystemExit(f"Claims not found: {claims_path}")
    if not index_path.is_file():
        raise SystemExit(f"Index not found: {index_path}")
    idx = load_index(index_path)

    claims = _read_jsonl(claims_path)
    _require_fields(claims, claims_path, ("id", "text"))

    audit_rows: List[Dict[str, Any]] = []
    for c in claims:
        cid = str(c.get("id"))
        text = str(c.get("text", ""))
        pred = _norm_label(c.get("predicted_label", "insufficient"))
        hits = retrieve(idx, text, top_k=int(args.top_k))
        audited, sim, evidence_id = audit_claim(text, hits, sim_threshold=float(args.sim_threshold))
        tier = tier_for_sim(sim)
        audit_rows.append({
            "id": cid,
            "text": text,
            "predicted_label": pred,
            "audited_label": audited,
            "top_similarity": sim,
            "tier": tier,
            "evidence_id": evidence_id,
        })

    metrics = compute_metrics(audit_rows)
    payload = {"metrics": metrics, "audits": audit_rows if args.save_audits else None}

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({"status": "ok", "action": "audit", "claims": str(claims_path), "index": str(index_path), "n": len(audit_rows)}))
    print(json.dumps({"metrics": metrics}, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="claims-audit", description="Claim-level audit CLI (build index, run audits, compute metrics).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("build", help="Build a TF-IDF retrieval index from a reference corpus JSONL.")
    pb.add_argument("--corpus", required=True, help="Path to corpus JSONL.")
    pb.add_argument("--index", required=True, help="Path to write index pickle.")
    pb.set_defaults(func=cmd_build)

    pa = sub.add_parser("audit", help="Audit claims JSONL against an existing index.")
    pa.add_argument("--claims", required=True, help="Path to claims JSONL.")
    pa.add_argument("--index", required=True, help="Path to index pickle.")
    pa.add_argument("--out", default=None, help="Optional path to write JSON report.")
    pa.add_argument("--top-k", default=5, type=int, help="Top K retrieval hits to consider.")
    pa.add_argument("--sim-threshold", default=0.35, type=float, help="Minimum cosine similarity to assert support/refute; else insufficient.")
    pa.add_argument("--save-audits", action="store_true", help="Include per-claim audit rows in the saved report.")
    pa.set_defaults(func=cmd_audit)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
