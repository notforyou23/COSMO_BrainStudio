#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, statistics
from pathlib import Path
from typing import Dict, List, Any, Tuple
def catalog() -> List[Dict[str, Any]]:
    # Priorities: 1=highest; rationale aims at continuum recovery + cross-validation (TN/lattice RG, semiclassical).
    return [
        dict(key="xi_over_a", name="Correlation length / lattice spacing", priority=1, kind="scaling",
             metrics=["nu_eff", "collapse_score"], rationale="Universal indicator of approaching a critical/continuum point; comparable across discretizations."),
        dict(key="susceptibility_like", name="Susceptibility-like integrated 2-pt", priority=1, kind="scaling",
             metrics=["gamma_eff", "hyperscaling"], rationale="Captures long-range correlations; sensitive to criticality and universality class."),
        dict(key="spectral_dimension", name="Spectral dimension d_s(σ)", priority=1, kind="continuum",
             metrics=["curve_L2", "JS_dist"], rationale="Widely used in spin-foam/GFT and CDT; tests emergent geometry and scale-dependence."),
        dict(key="area_law_deficit", name="Entanglement/area-law deficit", priority=2, kind="continuum",
             metrics=["trend", "scheme_consistency"], rationale="Probes geometric entanglement; amenable to TN coarse-graining and semiclassical comparisons."),
        dict(key="curvature_proxy", name="Curvature proxy (Regge/holonomy deficit)", priority=2, kind="semiclassical",
             metrics=["mean_bias", "W1_dist"], rationale="Direct semiclassical check versus effective action / GR expectations."),
        dict(key="two_point_decay", name="2-pt decay exponent η_eff", priority=2, kind="scaling",
             metrics=["eta_eff", "scheme_consistency"], rationale="Universality diagnostic; comparable to lattice/TN critical exponents."),
        dict(key="gauge_violation", name="Gauge/constraint violation norm", priority=3, kind="consistency",
             metrics=["trend", "max_norm"], rationale="Internal consistency of coarse-graining truncations; should decrease or stabilize along RG."),
        dict(key="reflection_positivity", name="Reflection positivity / Osterwalder–Schrader proxy", priority=3, kind="consistency",
             metrics=["pass_rate"], rationale="Continuum QFT consistency check; useful for identifying pathological fixed points."),
    ]
def _log_slope(x: List[float], y: List[float]) -> float | None:
    pts = [(xi, yi) for xi, yi in zip(x, y) if xi > 0 and yi > 0]
    if len(pts) < 3: return None
    lx, ly = zip(*[(math.log(a), math.log(b)) for a, b in pts])
    mx, my = statistics.fmean(lx), statistics.fmean(ly)
    den = sum((u-mx)**2 for u in lx)
    if den == 0: return None
    return sum((u-mx)*(v-my) for u, v in zip(lx, ly)) / den

def _l2_curve(a: List[float], b: List[float]) -> float | None:
    if not a or not b: return None
    n = min(len(a), len(b))
    return math.sqrt(sum((a[i]-b[i])**2 for i in range(n)) / n)

def _js_approx(p: List[float], q: List[float]) -> float | None:
    # crude JS divergence on positive sequences interpreted as histograms
    if not p or not q: return None
    n = min(len(p), len(q))
    pp, qq = [max(0.0, p[i]) for i in range(n)], [max(0.0, q[i]) for i in range(n)]
    sp, sq = sum(pp), sum(qq)
    if sp == 0 or sq == 0: return None
    pp, qq = [u/sp for u in pp], [u/sq for u in qq]
    m = [(pp[i]+qq[i])/2 for i in range(n)]
    def kl(a, b): 
        return sum(0.0 if ai == 0 else ai*math.log(ai/max(bi,1e-15)) for ai, bi in zip(a,b))
    return 0.5*kl(pp,m) + 0.5*kl(qq,m)
def example_rg_data() -> Dict[str, Any]:
    # Minimal synthetic dataset: two RG schemes with shared observables at increasing coarse scale L.
    L = [8, 16, 32, 64]
    def flow(noise: float) -> Dict[str, List[float]]:
        return {
            "xi_over_a": [1.2+0.15*i + noise*(i%2-0.5) for i in range(len(L))],
            "susceptibility_like": [10*(L[i]**0.9)*(1+noise*(0.3-0.1*i)) for i in range(len(L))],
            "spectral_dimension": [2.0, 2.3+0.1*noise, 2.7-0.1*noise, 3.0],
            "curvature_proxy": [0.8, 0.55, 0.35, 0.22+0.05*noise],
            "gauge_violation": [0.35, 0.22, 0.16, 0.13+0.02*noise],
        }
    return {
        "meta": {"note": "synthetic example"},
        "runs": [
            {"scheme": "tensor_network", "L": L, "observables": flow(0.05)},
            {"scheme": "lattice_RG", "L": L, "observables": flow(0.10)},
        ],
        "benchmarks": {
            "semiclassical_targets": {
                "spectral_dimension": [4.0, 4.0, 4.0, 4.0],
                "curvature_proxy": [0.0, 0.0, 0.0, 0.0],
            }
        }
    }

def load_rg_data(path: str | None) -> Dict[str, Any]:
    if not path: return example_rg_data()
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if "runs" not in data: raise ValueError("RG data JSON must contain 'runs'.")
    return data
def compute_diagnostics(data: Dict[str, Any]) -> Dict[str, Any]:
    runs = data.get("runs", [])
    cat = {c["key"]: c for c in catalog()}
    out: Dict[str, Any] = {"observables": {}, "comparisons": {}}

    # Per-run scaling diagnostics
    for r in runs:
        L = r.get("L") or r.get("scales") or []
        obs = (r.get("observables") or {})
        for k, series in obs.items():
            if k not in out["observables"]:
                out["observables"][k] = {"per_run": [], "priority": cat.get(k, {}).get("priority", 99)}
            rec = {"scheme": r.get("scheme", "unknown")}
            if k == "xi_over_a":
                rec["nu_eff"] = _log_slope(L, series)
                rec["trend"] = series[-1] - series[0] if series else None
            elif k == "susceptibility_like":
                rec["gamma_eff"] = _log_slope(L, series)
            elif k == "spectral_dimension":
                rec["curve_L2_to_first"] = _l2_curve(series, obs.get("spectral_dimension", series))
            elif k == "curvature_proxy":
                rec["mean"] = statistics.fmean(series) if series else None
            elif k == "gauge_violation":
                rec["max_norm"] = max(series) if series else None
                rec["trend"] = series[-1] - series[0] if series else None
            out["observables"][k]["per_run"].append(rec)

    # Cross-scheme consistency + benchmark comparisons
    if len(runs) >= 2:
        keys = set().union(*(r.get("observables", {}).keys() for r in runs))
        for k in keys:
            a = runs[0].get("observables", {}).get(k, [])
            b = runs[1].get("observables", {}).get(k, [])
            out["comparisons"].setdefault(k, {})
            out["comparisons"][k]["scheme_curve_L2"] = _l2_curve(a, b)
            out["comparisons"][k]["scheme_JS"] = _js_approx(a, b)

    targets = data.get("benchmarks", {}).get("semiclassical_targets", {})
    for k, tgt in targets.items():
        # compare each run to target curve
        for r in runs:
            series = r.get("observables", {}).get(k, [])
            out["comparisons"].setdefault(k, {})
            out["comparisons"][k][f"{r.get('scheme','run')}_to_target_L2"] = _l2_curve(series, tgt)

    # Produce a simple priority score: priority tier + (smaller distances, larger scaling exponents) heuristics
    scored: List[Tuple[float, str]] = []
    for k, info in out["observables"].items():
        pri = info.get("priority", 99)
        comp = out["comparisons"].get(k, {})
        dist = min([v for v in comp.values() if isinstance(v, (int,float)) and v is not None], default=0.0)
        exps = []
        for pr in info.get("per_run", []):
            for ek in ("nu_eff", "gamma_eff"):
                if isinstance(pr.get(ek), (int,float)) and pr.get(ek) is not None:
                    exps.append(abs(pr[ek]))
        exp_bonus = statistics.fmean(exps) if exps else 0.0
        score = pri*10 + dist - 0.5*exp_bonus
        scored.append((score, k))
        info["score"] = score
        info["catalog"] = {kk: cat.get(k, {}).get(kk) for kk in ("name","kind","metrics","rationale","priority")}
    out["prioritized_keys"] = [k for _, k in sorted(scored)]
    return out
def render_report(diag: Dict[str, Any], as_json: bool) -> str:
    if as_json:
        return json.dumps(diag, indent=2, sort_keys=True)
    lines = []
    lines.append("Continuum-recovery diagnostics (spin-foam/GFT RG):")
    lines.append("Prioritized candidate observables:")
    for i, k in enumerate(diag.get("prioritized_keys", []), 1):
        info = diag["observables"][k]
        c = info.get("catalog", {})
        lines.append(f"  {i}. {k}: {c.get('name','')}  [priority {c.get('priority',99)}, score {info.get('score'):.3g}]")
        if c.get("rationale"): lines.append(f"     - {c['rationale']}")
        comp = diag.get("comparisons", {}).get(k, {})
        if comp:
            best = sorted((v, kk) for kk, v in comp.items() if isinstance(v,(int,float)) and v is not None)[:2]
            if best: lines.append("     - comparisons: " + ", ".join(f"{kk}={v:.3g}" for v, kk in best))
    return "\n".join(lines) + "\n"
def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sf-gft-diagnostics",
        description="Focused conceptual design workflow for continuum-recovery diagnostics and cross-validation tests.")
    ap.add_argument("--rg-data", type=str, default=None, help="Path to RG data JSON (optional; otherwise uses a synthetic example).")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    args = ap.parse_args(argv)

    data = load_rg_data(args.rg_data)
    diag = compute_diagnostics(data)
    print(render_report(diag, as_json=args.json), end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
