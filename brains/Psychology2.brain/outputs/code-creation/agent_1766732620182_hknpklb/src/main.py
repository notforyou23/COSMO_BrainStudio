from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path
from typing import Dict, Any, List, Tuple

def _read_jsonl(p: Path) -> List[Dict[str, Any]]:
    out = []
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out

def _read_json(p: Path) -> List[Dict[str, Any]]:
    obj = json.loads(p.read_text(encoding='utf-8'))
    if isinstance(obj, list): return obj
    if isinstance(obj, dict) and 'data' in obj and isinstance(obj['data'], list): return obj['data']
    raise ValueError('JSON must be a list[record] or {"data":[...]}')

def _read_csv(p: Path) -> List[Dict[str, Any]]:
    with p.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]

def load_dataset(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    suf = p.suffix.lower()
    if suf == '.jsonl': return _read_jsonl(p)
    if suf == '.json': return _read_json(p)
    if suf == '.csv': return _read_csv(p)
    raise ValueError(f'Unsupported dataset extension: {suf}')

def to_float01(x: Any, default: float = 0.0) -> float:
    if x is None: return default
    if isinstance(x, bool): return 1.0 if x else 0.0
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip().lower()
    if s in ('1','true','t','yes','y','correct','pos','positive'): return 1.0
    if s in ('0','false','f','no','n','incorrect','neg','negative'): return 0.0
    try: return float(s)
    except Exception: return default

def compute_uncertainty_signals(claim: str) -> Dict[str, float]:
    c = claim or ''
    toks = [t for t in c.replace('\n',' ').split(' ') if t]
    n = max(1, len(toks))
    hedges = ('maybe','possibly','might','could','allegedly','reportedly','unclear','unknown','likely','seems','approx','approximately')
    has_hedge = 1.0 if any(h in c.lower() for h in hedges) else 0.0
    has_q = 1.0 if '?' in c else 0.0
    has_num = 1.0 if any(ch.isdigit() for ch in c) else 0.0
    caps_ratio = (sum(1 for ch in c if ch.isupper()) / max(1, sum(1 for ch in c if ch.isalpha())))
    longness = min(1.0, math.log(n + 1, 50))
    noisiness = min(1.0, 0.6*has_hedge + 0.25*has_q + 0.15*has_num)
    style = min(1.0, 0.7*caps_ratio + 0.3*(1.0 - min(1.0, len(c)/280.0)))
    return {'longness': longness, 'noisiness': noisiness, 'style': style}

def aggregate_uncertainty(sig: Dict[str, float]) -> float:
    return float(min(1.0, max(0.0, 0.45*sig.get('noisiness',0.0) + 0.35*sig.get('style',0.0) + 0.20*sig.get('longness',0.0))))

def route(unc: float, auto_th: float, abstain_th: float) -> str:
    if unc < auto_th: return 'auto'
    if unc < abstain_th: return 'escalate'
    return 'abstain'

def eval_metrics(rows: List[Dict[str, Any]], policy: Dict[str, float], costs: Dict[str, float]) -> Dict[str, float]:
    n = len(rows)
    if n == 0:
        return {'n':0,'auto_rate':0.0,'escalate_rate':0.0,'abstain_rate':0.0,'error_rate':0.0,'expected_cost':0.0}
    auto = esc = absn = err = 0
    total_cost = 0.0
    for r in rows:
        u = float(r['uncertainty'])
        dec = route(u, policy['auto_th'], policy['abstain_th'])
        y = to_float01(r.get('label', r.get('correct', r.get('y', 1))), default=1.0)
        if dec == 'auto':
            auto += 1
            if y < 0.5:
                err += 1
                total_cost += costs['error_cost']
        elif dec == 'escalate':
            esc += 1
            total_cost += costs['human_review_cost']
        else:
            absn += 1
            total_cost += costs['abstain_cost']
    return {
        'n': n,
        'auto_rate': auto/n,
        'escalate_rate': esc/n,
        'abstain_rate': absn/n,
        'error_rate': err/n,
        'expected_cost': total_cost/n
    }

def sweep(rows: List[Dict[str, Any]], tiers: List[str], grid_auto: List[float], grid_abstain: List[float], costs: Dict[str, float], tier_overrides: Dict[str, Dict[str, float]] | None = None) -> List[Dict[str, Any]]:
    tier_overrides = tier_overrides or {}
    by_tier: Dict[str, List[Dict[str, Any]]] = {t: [] for t in tiers}
    for r in rows:
        t = str(r.get('risk_tier', r.get('tier', 'default')))
        if t not in by_tier:
            by_tier[t] = []
            tiers.append(t)
        by_tier[t].append(r)
    out = []
    for t in tiers:
        base = {'auto_th': 0.25, 'abstain_th': 0.75}
        base.update(tier_overrides.get(t, {}))
        for a in grid_auto:
            for b in grid_abstain:
                if b <= a: 
                    continue
                pol = {'auto_th': float(a), 'abstain_th': float(b)}
                m = eval_metrics(by_tier.get(t, []), pol, costs)
                out.append({'risk_tier': t, 'auto_th': a, 'abstain_th': b, **m})
    return out

def write_csv(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    cols = list(rows[0].keys())
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in cols})

def main():
    ap = argparse.ArgumentParser(description='Per-claim uncertainty + routing + threshold sweep.')
    ap.add_argument('--dataset', required=True, help='Path to labeled claims dataset (.jsonl/.json/.csv).')
    ap.add_argument('--outdir', default=str(Path.cwd()/'outputs'), help='Output directory.')
    ap.add_argument('--label-field', default='', help='Optional label field name (default: label/correct/y).')
    ap.add_argument('--tier-field', default='', help='Optional tier field name (default: risk_tier/tier).')
    ap.add_argument('--config', default='', help='Optional JSON config with tier_overrides and costs.')
    ap.add_argument('--grid-auto', default='0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50', help='Comma-separated auto thresholds.')
    ap.add_argument('--grid-abstain', default='0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90,0.95', help='Comma-separated abstain thresholds.')
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = {}
    if args.config:
        cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    costs = {'human_review_cost': 1.0, 'abstain_cost': 0.3, 'error_cost': 5.0}
    costs.update(cfg.get('costs', {}))
    tier_overrides = cfg.get('tier_overrides', {})

    data = load_dataset(args.dataset)
    rows = []
    for rec in data:
        claim = rec.get('claim', rec.get('text', rec.get('prompt', '')))
        if claim is None: claim = ''
        sig = compute_uncertainty_signals(str(claim))
        unc = aggregate_uncertainty(sig)
        r = dict(rec)
        if args.label_field and args.label_field in r:
            r['label'] = r[args.label_field]
        if args.tier_field and args.tier_field in r:
            r['risk_tier'] = r[args.tier_field]
        r.setdefault('risk_tier', r.get('tier', 'default'))
        r['uncertainty'] = float(unc)
        for k,v in sig.items():
            r[f'u_{k}'] = float(v)
        rows.append(r)

    tiers = sorted({str(r.get('risk_tier','default')) for r in rows})
    grid_auto = [float(x) for x in args.grid_auto.split(',') if x.strip()]
    grid_abs = [float(x) for x in args.grid_abstain.split(',') if x.strip()]

    sweep_rows = sweep(rows, tiers, grid_auto, grid_abs, costs, tier_overrides=tier_overrides)

    # Pick a simple "best" per tier: minimize expected_cost, tie-break by lower error_rate then higher auto_rate
    best = {}
    for t in tiers:
        cand = [r for r in sweep_rows if r['risk_tier']==t]
        if not cand: 
            continue
        cand.sort(key=lambda r: (r['expected_cost'], r['error_rate'], -r['auto_rate']))
        best[t] = cand[0]

    (outdir/'claims_scored.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + ('\n' if rows else ''), encoding='utf-8')
    write_csv(outdir/'threshold_sweep.csv', sweep_rows)
    (outdir/'best_by_tier.json').write_text(json.dumps(best, indent=2, ensure_ascii=False), encoding='utf-8')
    summary = {
        'n': len(rows),
        'tiers': tiers,
        'costs': costs,
        'best_by_tier': best,
        'dataset': str(Path(args.dataset).resolve())
    }
    (outdir/'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

if __name__ == '__main__':
    main()
