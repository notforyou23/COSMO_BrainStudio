#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_QA = {"unreviewed","in_progress","pass","fail","blocked"}

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def paths():
    base = repo_root()
    return base / "outputs" / "PROJECT_TRACKER.json", base / "TRACKING_RECONCILIATION.md"

def load_tracker(p: Path) -> list[dict]:
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8") or "[]")
    if isinstance(data, dict) and "goals" in data:
        data = data["goals"]
    if not isinstance(data, list):
        raise SystemExit("Tracker JSON must be a list (or {'goals':[...]}).")
    return data

def save_tracker(p: Path, goals: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(goals, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def normalize_goal(g: dict) -> dict:
    out = {
        "goal_id": str(g.get("goal_id","")).strip(),
        "description": str(g.get("description","")).strip(),
        "priority": str(g.get("priority","")).strip(),
        "progress_pct": int(g.get("progress_pct", 0) if g.get("progress_pct", 0) != "" else 0),
        "qa_status": str(g.get("qa_status","unreviewed")).strip() or "unreviewed",
        "last_updated": str(g.get("last_updated","")).strip() or now_iso(),
    }
    return out

def validate(goals: list[dict]) -> list[str]:
    errs = []
    seen = set()
    for i, g0 in enumerate(goals):
        g = normalize_goal(g0)
        goals[i] = g
        gid = g["goal_id"]
        if not gid:
            errs.append(f"missing goal_id at index {i}")
        elif gid in seen:
            errs.append(f"duplicate goal_id: {gid}")
        seen.add(gid)
        if not g["description"]:
            errs.append(f"{gid or f'index {i}'}: missing description")
        try:
            p = int(g["progress_pct"])
        except Exception:
            errs.append(f"{gid}: progress_pct not int")
            p = 0
        if p < 0 or p > 100:
            errs.append(f"{gid}: progress_pct out of range 0-100")
        if g["qa_status"] not in ALLOWED_QA:
            errs.append(f"{gid}: qa_status must be one of {sorted(ALLOWED_QA)}")
        try:
            datetime.fromisoformat(g["last_updated"].replace("Z","+00:00"))
        except Exception:
            errs.append(f"{gid}: last_updated must be ISO-8601")
    return errs

def find_goal(goals: list[dict], goal_id: str) -> dict | None:
    for g in goals:
        if str(g.get("goal_id","")) == goal_id:
            return g
    return None

def upsert(goals: list[dict], goal_id: str, description: str | None, priority: str | None) -> dict:
    g = find_goal(goals, goal_id)
    if g is None:
        g = {"goal_id": goal_id, "description": description or "", "priority": priority or "", "progress_pct": 0, "qa_status": "unreviewed", "last_updated": now_iso()}
        goals.append(g)
    if description is not None:
        g["description"] = description
    if priority is not None:
        g["priority"] = priority
    g["last_updated"] = now_iso()
    return g

def coerce_int(x: str) -> int:
    try:
        return int(float(x))
    except Exception:
        raise SystemExit(f"Invalid integer: {x}")

def render_md(goals: list[dict], errors: list[str], tracker_path: Path) -> str:
    goals_sorted = sorted(goals, key=lambda g: (str(g.get("priority","")), str(g.get("goal_id",""))))
    lines = []
    lines.append("# TRACKING_RECONCILIATION")
    lines.append("")
    lines.append(f"- Generated: {now_iso()}")
    lines.append(f"- Tracker: {tracker_path.as_posix()}")
    lines.append(f"- Goals: {len(goals_sorted)}")
    lines.append("")
    lines.append("## Validation")
    if errors:
        lines.append("")
        for e in errors:
            lines.append(f"- [!] {e}")
    else:
        lines.append("")
        lines.append("- OK: no validation errors")
    lines.append("")
    lines.append("## Goals")
    lines.append("")
    lines.append("| goal_id | priority | progress_pct | qa_status | last_updated | description |")
    lines.append("|---|---:|---:|---|---|---|")
    for g in goals_sorted:
        desc = (g.get("description","") or "").replace("\n"," ").strip()
        if len(desc) > 120:
            desc = desc[:117] + "..."
        lines.append(f"| {g.get('goal_id','')} | {g.get('priority','')} | {g.get('progress_pct',0)} | {g.get('qa_status','')} | {g.get('last_updated','')} | {desc} |")
    lines.append("")
    prog = [int(g.get("progress_pct",0) or 0) for g in goals_sorted] or [0]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Avg progress: {sum(prog)/len(prog):.1f}%")
    qa_counts = {}
    for g in goals_sorted:
        qa = g.get("qa_status","unreviewed")
        qa_counts[qa] = qa_counts.get(qa, 0) + 1
    lines.append("- QA counts: " + ", ".join(f"{k}={qa_counts[k]}" for k in sorted(qa_counts)))
    lines.append("")
    return "\n".join(lines) + "\n"

def main(argv=None) -> int:
    tracker_path, md_path = paths()
    ap = argparse.ArgumentParser(description="Update outputs/PROJECT_TRACKER.json and generate TRACKING_RECONCILIATION.md")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create tracker if missing (no changes if exists)")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing tracker with empty list")

    p_up = sub.add_parser("upsert", help="Create/update a goal (description/priority)")
    p_up.add_argument("goal_id")
    p_up.add_argument("--description")
    p_up.add_argument("--priority")

    p_set = sub.add_parser("set", help="Set fields on a goal")
    p_set.add_argument("goal_id")
    p_set.add_argument("--progress", type=str)
    p_set.add_argument("--qa", type=str)
    p_set.add_argument("--description")
    p_set.add_argument("--priority")

    sub.add_parser("report", help="Generate reconciliation markdown from current tracker")

    args = ap.parse_args(argv)
    goals = [] if (args.cmd == "init" and args.force) else load_tracker(tracker_path)

    if args.cmd == "init":
        if tracker_path.exists() and not args.force:
            pass
        else:
            goals = []
            save_tracker(tracker_path, goals)

    elif args.cmd == "upsert":
        upsert(goals, args.goal_id, args.description, args.priority)
        errs = validate(goals)
        save_tracker(tracker_path, goals)
        md_path.write_text(render_md(goals, errs, tracker_path), encoding="utf-8")
        return 1 if errs else 0

    elif args.cmd == "set":
        g = upsert(goals, args.goal_id, args.description, args.priority)
        if args.progress is not None:
            g["progress_pct"] = coerce_int(args.progress)
        if args.qa is not None:
            g["qa_status"] = args.qa.strip()
        g["last_updated"] = now_iso()
        errs = validate(goals)
        save_tracker(tracker_path, goals)
        md_path.write_text(render_md(goals, errs, tracker_path), encoding="utf-8")
        return 1 if errs else 0

    elif args.cmd == "report":
        errs = validate(goals)
        if not tracker_path.exists():
            save_tracker(tracker_path, goals)
        md_path.write_text(render_md(goals, errs, tracker_path), encoding="utf-8")
        return 1 if errs else 0

    errs = validate(goals)
    save_tracker(tracker_path, goals)
    md_path.write_text(render_md(goals, errs, tracker_path), encoding="utf-8")
    return 1 if errs else 0

if __name__ == "__main__":
    raise SystemExit(main())
