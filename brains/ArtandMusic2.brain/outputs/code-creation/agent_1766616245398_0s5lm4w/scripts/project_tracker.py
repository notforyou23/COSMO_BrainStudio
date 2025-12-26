#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, csv
from pathlib import Path
from datetime import datetime, timezone

def _root_dir() -> Path:
    return Path(__file__).resolve().parents[1]

def _paths():
    root = _root_dir()
    out = root / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out / "PROJECT_TRACKER.json", out / "PROJECT_TRACKER.csv"

def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _default_ledger():
    return {"version": 1, "created_at": _now(), "goals": {}, "cycles": [], "aggregates": {"by_goal": {}, "totals": {"pursued": 0, "completed": 0}}}

def load_ledger(path: Path):
    if not path.exists():
        return _default_ledger()
    return json.loads(path.read_text(encoding="utf-8"))

def recompute(ledger: dict) -> dict:
    by_goal = {gid: {"pursued": 0, "completed": 0} for gid in ledger.get("goals", {})}
    totals = {"pursued": 0, "completed": 0}
    for cyc in ledger.get("cycles", []):
        updates = (cyc.get("updates") or {})
        for gid, u in updates.items():
            by_goal.setdefault(gid, {"pursued": 0, "completed": 0})
            by_goal[gid]["pursued"] += int(u.get("pursued", 0))
            by_goal[gid]["completed"] += int(u.get("completed", 0))
            totals["pursued"] += int(u.get("pursued", 0))
            totals["completed"] += int(u.get("completed", 0))
    ledger["aggregates"] = {"by_goal": by_goal, "totals": totals}
    return ledger

def save_ledger(path: Path, ledger: dict):
    ledger = recompute(ledger)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def _get_cycle(ledger: dict, cycle_id: str | None):
    cycles = ledger.get("cycles", [])
    if not cycles:
        return None
    if cycle_id is None:
        return cycles[-1]
    for c in cycles:
        if c.get("id") == cycle_id:
            return c
    return None

def _active_goals(ledger: dict):
    out = []
    for gid, g in (ledger.get("goals") or {}).items():
        if bool(g.get("active", True)):
            out.append(gid)
    return sorted(out)

def cmd_init(args):
    jpath, _ = _paths()
    ledger = _default_ledger()
    save_ledger(jpath, ledger)
    print(f"OK init: {jpath}")

def cmd_goal_add(args):
    jpath, _ = _paths()
    ledger = load_ledger(jpath)
    gid = args.id
    goals = ledger.setdefault("goals", {})
    if gid in goals and not args.force:
        raise SystemExit(f"Goal already exists: {gid} (use --force to overwrite)")
    goals[gid] = {"title": args.title, "active": (not args.inactive), "created_at": _now(), "notes": args.notes or ""}
    save_ledger(jpath, ledger)
    print(f"OK goal add: {gid}")

def cmd_goal_set_active(args):
    jpath, _ = _paths()
    ledger = load_ledger(jpath)
    g = (ledger.get("goals") or {}).get(args.id)
    if not g:
        raise SystemExit(f"Unknown goal id: {args.id}")
    g["active"] = (args.active == "true")
    g["updated_at"] = _now()
    save_ledger(jpath, ledger)
    print(f"OK goal active={g['active']}: {args.id}")

def cmd_cycle_start(args):
    jpath, _ = _paths()
    ledger = load_ledger(jpath)
    cid = args.id or f"cycle-{len(ledger.get('cycles', []))+1:04d}"
    if _get_cycle(ledger, cid) is not None:
        raise SystemExit(f"Cycle already exists: {cid}")
    cyc = {"id": cid, "ts": _now(), "active_goals": _active_goals(ledger), "updates": {}}
    ledger.setdefault("cycles", []).append(cyc)
    save_ledger(jpath, ledger)
    print(f"OK cycle start: {cid}")
    if cyc["active_goals"]:
        print("ACTIVE_GOALS: " + ", ".join(cyc["active_goals"]))
    else:
        print("ACTIVE_GOALS: (none)")

def cmd_update(args):
    jpath, _ = _paths()
    ledger = load_ledger(jpath)
    cyc = _get_cycle(ledger, args.cycle)
    if cyc is None:
        raise SystemExit("No cycle found. Run: project_tracker.py cycle start")
    gid = args.goal
    if gid not in (ledger.get("goals") or {}):
        raise SystemExit(f"Unknown goal id: {gid} (add it first)")
    upd = (cyc.setdefault("updates", {}).setdefault(gid, {"pursued": 0, "completed": 0}))
    upd["pursued"] = int(upd.get("pursued", 0)) + int(args.pursued)
    upd["completed"] = int(upd.get("completed", 0)) + int(args.completed)
    cyc["updated_at"] = _now()
    save_ledger(jpath, ledger)
    print(f"OK update: cycle={cyc['id']} goal={gid} pursued+={args.pursued} completed+={args.completed}")

def cmd_status(args):
    jpath, _ = _paths()
    ledger = recompute(load_ledger(jpath))
    cyc = _get_cycle(ledger, args.cycle)
    if cyc is None:
        print("NO_CYCLE")
        return
    goals = ledger.get("goals") or {}
    print(f"CYCLE: {cyc.get('id')} @ {cyc.get('ts')}")
    ag = cyc.get("active_goals") or []
    if ag:
        for gid in ag:
            title = (goals.get(gid) or {}).get("title", "")
            u = (cyc.get("updates") or {}).get(gid, {})
            print(f"- {gid}: {title} | pursued={int(u.get('pursued',0))} completed={int(u.get('completed',0))}")
    else:
        print("ACTIVE_GOALS: (none)")
    totals = (ledger.get("aggregates") or {}).get("totals") or {}
    print(f"TOTALS: pursued={int(totals.get('pursued',0))} completed={int(totals.get('completed',0))}")

def cmd_export(args):
    jpath, cpath = _paths()
    ledger = recompute(load_ledger(jpath))
    goals = ledger.get("goals") or {}
    rows = []
    for cyc in ledger.get("cycles", []):
        cid, ts = cyc.get("id"), cyc.get("ts")
        updates = cyc.get("updates") or {}
        active = set(cyc.get("active_goals") or [])
        for gid in sorted(set(list(active) + list(updates.keys()))):
            u = updates.get(gid, {})
            rows.append({
                "cycle_id": cid, "cycle_ts": ts, "goal_id": gid,
                "goal_title": (goals.get(gid) or {}).get("title",""),
                "goal_active": bool((goals.get(gid) or {}).get("active", True)),
                "in_active_list": gid in active,
                "pursued": int(u.get("pursued", 0)), "completed": int(u.get("completed", 0)),
            })
    with cpath.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cycle_id","cycle_ts","goal_id","goal_title","goal_active","in_active_list","pursued","completed"])
        w.writeheader()
        w.writerows(rows)
    print(f"OK export: {cpath}")

def main(argv=None):
    p = argparse.ArgumentParser(prog="project_tracker.py", description="Single source-of-truth goal progress ledger.")
    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("init").set_defaults(fn=cmd_init)

    pg = sp.add_parser("goal")
    sg = pg.add_subparsers(dest="sub", required=True)
    a = sg.add_parser("add")
    a.add_argument("--id", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--notes", default="")
    a.add_argument("--inactive", action="store_true")
    a.add_argument("--force", action="store_true")
    a.set_defaults(fn=cmd_goal_add)
    s = sg.add_parser("set-active")
    s.add_argument("--id", required=True)
    s.add_argument("--active", choices=["true","false"], required=True)
    s.set_defaults(fn=cmd_goal_set_active)

    pc = sp.add_parser("cycle")
    sc = pc.add_subparsers(dest="sub", required=True)
    st = sc.add_parser("start")
    st.add_argument("--id", default=None)
    st.set_defaults(fn=cmd_cycle_start)

    u = sp.add_parser("update")
    u.add_argument("--goal", required=True)
    u.add_argument("--cycle", default=None)
    u.add_argument("--pursued", type=int, default=1)
    u.add_argument("--completed", type=int, default=0)
    u.set_defaults(fn=cmd_update)

    stt = sp.add_parser("status")
    stt.add_argument("--cycle", default=None)
    stt.set_defaults(fn=cmd_status)

    ex = sp.add_parser("export")
    ex.set_defaults(fn=cmd_export)

    args = p.parse_args(argv)
    return args.fn(args)

if __name__ == "__main__":
    raise SystemExit(main())
