from __future__ import annotations
from pathlib import Path
import csv, json, math, traceback
from datetime import datetime

BASE = Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution")
KIT_DIR = BASE / "outputs" / "meta_analysis_starter_kit"
OUT_DIR = KIT_DIR / "outputs"
ASSET_DIR = KIT_DIR / "assets"
TEMPLATE_PATH = ASSET_DIR / "extraction_template.csv"
SCREEN_LOG_PATH = ASSET_DIR / "screening_log.csv"
SKELETON_PY = KIT_DIR / "analysis_skeleton.py"
SKELETON_IPYNB = KIT_DIR / "analysis_skeleton.ipynb"
RUN_LOG = OUT_DIR / "run_log.txt"

def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def load_extraction(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = []
        for row in r:
            try:
                eff = float(row["effect"])
                se = float(row["se"])
            except Exception:
                continue
            if not (math.isfinite(eff) and math.isfinite(se) and se > 0):
                continue
            row["_effect"] = eff
            row["_se"] = se
            rows.append(row)
        return rows

def fixed_effect_meta(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("No usable rows found in extraction template.")
    ws, wes = 0.0, 0.0
    for r in rows:
        w = 1.0 / (r["_se"] ** 2)
        ws += w
        wes += w * r["_effect"]
        r["_w"] = w
    pooled = wes / ws
    se_pooled = math.sqrt(1.0 / ws)
    ci = (pooled - 1.96 * se_pooled, pooled + 1.96 * se_pooled)
    return {"k": len(rows), "pooled": pooled, "se": se_pooled, "ci_low": ci[0], "ci_high": ci[1]}
def make_forest_plot(rows: list[dict], summ: dict, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [(r.get("author_year") or r.get("study_id") or "").strip() for r in rows]
    effs = [r["_effect"] for r in rows]
    ses = [r["_se"] for r in rows]
    lo = [e - 1.96 * s for e, s in zip(effs, ses)]
    hi = [e + 1.96 * s for e, s in zip(effs, ses)]
    y = list(range(len(rows), 0, -1))

    fig_h = max(3.0, 0.35 * len(rows) + 2.0)
    fig, ax = plt.subplots(figsize=(7.5, fig_h))
    for yi, e, l, h in zip(y, effs, lo, hi):
        ax.plot([l, h], [yi, yi], color="black", lw=1)
        ax.plot([e], [yi], marker="s", color="black", ms=5)

    y_p = 0
    p, pl, ph = summ["pooled"], summ["ci_low"], summ["ci_high"]
    ax.plot([pl, ph], [y_p, y_p], color="black", lw=2)
    ax.plot([p], [y_p], marker="D", color="black", ms=7)

    ax.axvline(0.0, color="gray", lw=1, ls="--")
    ax.set_yticks(y + [y_p])
    ax.set_yticklabels(labels + ["Pooled (fixed)"])
    ax.set_xlabel("Effect (placeholder scale)")
    ax.set_title("Forest plot (placeholder fixed-effect meta-analysis)")
    xs = lo + [pl, 0.0] + hi + [ph]
    xpad = (max(xs) - min(xs)) * 0.1 if max(xs) > min(xs) else 1.0
    ax.set_xlim(min(xs) - xpad, max(xs) + xpad)
    ax.set_ylim(-1, len(rows) + 1)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)

def write_summary(rows: list[dict], summ: dict, out_path: Path) -> None:
    header = ["study_id","author_year","effect","se","ci_low","ci_high","weight"]
    out_rows = []
    for r in rows:
        e, s = r["_effect"], r["_se"]
        out_rows.append([
            r.get("study_id",""), r.get("author_year",""),
            f"{e:.6g}", f"{s:.6g}", f"{(e-1.96*s):.6g}", f"{(e+1.96*s):.6g}", f"{r.get('_w',float('nan')):.6g}"
        ])
    out_rows.append(["POOLED_FIXED","",f"{summ['pooled']:.6g}",f"{summ['se']:.6g}",f"{summ['ci_low']:.6g}",f"{summ['ci_high']:.6g}",""])
    write_csv(out_path, header, out_rows)

def write_skeletons() -> None:
    py = f'''from pathlib import Path
import csv, math
from datetime import datetime

BASE = Path(r"{BASE}")
KIT_DIR = BASE / "outputs" / "meta_analysis_starter_kit"
ASSET_DIR = KIT_DIR / "assets"
OUT_DIR = KIT_DIR / "outputs"

def load_rows(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows=[]
        for row in r:
            try:
                e=float(row["effect"]); se=float(row["se"])
            except Exception:
                continue
            if se>0 and math.isfinite(e) and math.isfinite(se):
                rows.append((row.get("author_year") or row.get("study_id") or "", e, se))
        return rows

rows=load_rows(ASSET_DIR/"extraction_template.csv")
ws=sum(1/(se**2) for _,_,se in rows)
pooled=sum((1/(se**2))*e for _,e,se in rows)/ws
se_pooled=math.sqrt(1/ws)
print("k=",len(rows),"pooled=",pooled,"se=",se_pooled,"timestamp=",datetime.now().isoformat(timespec="seconds"))
'''
    SKELETON_PY.write_text(py, encoding="utf-8")
    ip = {
        "cells": [
            {"cell_type":"markdown","metadata":{},"source":["# Meta-analysis starter kit (placeholder)\n","This notebook loads the extraction template and computes a placeholder fixed-effect pooled estimate.\n"]},
            {"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],
             "source":[
                 "from pathlib import Path\n","import csv, math\n","from datetime import datetime\n",
                 f"BASE = Path(r"{BASE}")\n","KIT_DIR = BASE / 'outputs' / 'meta_analysis_starter_kit'\n",
                 "ASSET_DIR = KIT_DIR / 'assets'\n","OUT_DIR = KIT_DIR / 'outputs'\n",
                 "path = ASSET_DIR / 'extraction_template.csv'\n",
                 "rows=[]\n",
                 "with path.open('r', newline='', encoding='utf-8') as f:\n",
                 "    r=csv.DictReader(f)\n",
                 "    for row in r:\n",
                 "        try:\n",
                 "            e=float(row['effect']); se=float(row['se'])\n",
                 "        except Exception:\n",
                 "            continue\n",
                 "        if se>0 and math.isfinite(e) and math.isfinite(se):\n",
                 "            rows.append((row.get('author_year') or row.get('study_id') or '', e, se))\n",
                 "ws=sum(1/(se**2) for _,_,se in rows)\n",
                 "pooled=sum((1/(se**2))*e for _,e,se in rows)/ws\n",
                 "se_pooled=math.sqrt(1/ws)\n",
                 "print({'k':len(rows),'pooled':pooled,'se':se_pooled,'timestamp':datetime.now().isoformat(timespec='seconds')})\n"
             ]}
        ],
        "metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python","version":"3.x"}},
        "nbformat":4,"nbformat_minor":5
    }
    SKELETON_IPYNB.write_text(json.dumps(ip, indent=2), encoding="utf-8")
def main() -> int:
    KIT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    extract_cols = ["study_id","author_year","effect_type","effect","se","n_treat","n_control","notes"]
    extract_rows = [
        ["S1","Smith 2020","SMD",0.20,0.10,50,50,"Example row; replace with your extracted data."],
        ["S2","Garcia 2021","SMD",-0.05,0.12,40,42,"Example row; replace with your extracted data."],
        ["S3","Lee 2022","SMD",0.15,0.08,60,58,"Example row; replace with your extracted data."]
    ]
    write_csv(TEMPLATE_PATH, extract_cols, extract_rows)

    screen_cols = ["record_id","title","abstract_decision","fulltext_decision","reason","reviewer","date"]
    screen_rows = [["R1","Example title","include","","","reviewer1",datetime.now().date().isoformat()]]
    write_csv(SCREEN_LOG_PATH, screen_cols, screen_rows)

    write_skeletons()

    summary_csv = OUT_DIR / "summary_table.csv"
    forest_png = OUT_DIR / "forest_plot.png"

    t0 = datetime.now()
    log_lines = [f"meta_analysis_starter_kit run @ {t0.isoformat(timespec='seconds')}"]
    try:
        rows = load_extraction(TEMPLATE_PATH)
        summ = fixed_effect_meta(rows)
        write_summary(rows, summ, summary_csv)
        make_forest_plot(rows, summ, forest_png)
        log_lines += [
            f"k={summ['k']}",
            f"pooled_fixed={summ['pooled']:.6g}",
            f"se={summ['se']:.6g}",
            f"ci95=[{summ['ci_low']:.6g},{summ['ci_high']:.6g}]",
            f"wrote={summary_csv}",
            f"wrote={forest_png}",
            "status=OK"
        ]
        code = 0
    except Exception as e:
        log_lines += ["status=ERROR", f"error={type(e).__name__}: {e}", traceback.format_exc()]
        code = 1
    RUN_LOG.write_text("\n".join(log_lines).rstrip() + "\n", encoding="utf-8")
    print("KIT_CREATED:" + str(KIT_DIR))
    print("KIT_OUTPUTS:" + json.dumps(sorted([p.name for p in OUT_DIR.glob('*') if p.is_file()])))
    return code

if __name__ == "__main__":
    raise SystemExit(main())
