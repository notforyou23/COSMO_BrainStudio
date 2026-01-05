from __future__ import annotations
import json
from dataclasses import is_dataclass, asdict
from typing import Any, Dict, List, Optional

def _to_dict(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_dict(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        return _to_dict(obj.model_dump())
    if is_dataclass(obj):
        return _to_dict(asdict(obj))
    if hasattr(obj, "__dict__"):
        return _to_dict({k: v for k, v in vars(obj).items() if not k.startswith("_")})
    return str(obj)

def render_plan_json(plan: Any, *, indent: int = 2) -> str:
    return json.dumps(_to_dict(plan), ensure_ascii=False, indent=indent, sort_keys=False) + "\n"

def _get(d: Any, key: str, default: Any = None) -> Any:
    if d is None:
        return default
    if isinstance(d, dict):
        return d.get(key, default)
    return getattr(d, key, default)

def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

def _md_kv(title: str, value: Any) -> str:
    if value is None or value == "" or value == [] or value == {}:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return f"- **{title}**: {value}\n"
    if isinstance(value, dict):
        lines = [f"- **{title}**:"]
        for k, v in value.items():
            if v is None or v == "" or v == [] or v == {}:
                continue
            lines.append(f"  - {k}: {_to_dict(v)}")
        return "\n".join(lines) + "\n"
    if isinstance(value, list):
        lines = [f"- **{title}**:"]
        for it in value:
            lines.append(f"  - {_to_dict(it)}")
        return "\n".join(lines) + "\n"
    return f"- **{title}**: {_to_dict(value)}\n"

def _render_arms_md(plan_d: Dict[str, Any]) -> str:
    arms = _as_list(plan_d.get("arms") or plan_d.get("experimental_arms"))
    if not arms:
        return ""
    out = ["## Experimental arms\n"]
    for i, arm in enumerate(arms, 1):
        ad = _to_dict(arm)
        name = ad.get("name") or ad.get("label") or f"Arm {i}"
        out.append(f"### {i}. {name}\n")
        desc = ad.get("description") or ad.get("rationale")
        if desc:
            out.append(f"{desc}\n")
        comps = ad.get("components") or ad.get("intervention_components") or []
        if comps:
            out.append("**Intervention components**\n")
            for c in comps:
                cd = _to_dict(c)
                if isinstance(cd, dict):
                    cn = cd.get("name") or cd.get("type") or "component"
                    out.append(f"- {cn}")
                    det = cd.get("details") or cd.get("description")
                    if det:
                        out.append(f"  - details: {det}")
                    dosage = cd.get("dose") or cd.get("dosage") or cd.get("frequency")
                    if dosage:
                        out.append(f"  - dose: {dosage}")
                else:
                    out.append(f"- {cd}")
            out.append("")
        zpd = ad.get("zpd") or ad.get("zpd_support") or ad.get("social_support") or {}
        if zpd:
            out.append("**ZPD operationalization (type / timing / fading)**\n")
            for key in ("type", "timing", "fading", "contingency", "agent", "delivery_channel", "dose", "monitoring"):
                v = zpd.get(key) if isinstance(zpd, dict) else _get(zpd, key)
                if v not in (None, "", [], {}):
                    out.append(_md_kv(key.replace("_", " ").title(), v).rstrip("\n"))
            out.append("")
        outcomes = ad.get("proximal_mediators") or ad.get("mediators")
        if outcomes:
            out.append("**Targeted proximal mediators**\n")
            for m in _as_list(outcomes):
                md = _to_dict(m)
                if isinstance(md, dict):
                    out.append(f"- {md.get('name') or md.get('construct') or md}")
                    if md.get("measure"):
                        out.append(f"  - measure: {md['measure']}")
                    if md.get("expected_direction"):
                        out.append(f"  - expected_direction: {md['expected_direction']}")
                else:
                    out.append(f"- {md}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"

def _render_timeline_md(plan_d: Dict[str, Any]) -> str:
    waves = _as_list(plan_d.get("waves") or plan_d.get("timeline") or plan_d.get("measurement_waves"))
    if not waves:
        return ""
    out = ["## Multi-wave timeline & measurement schedule\n"]
    for w in waves:
        wd = _to_dict(w)
        label = wd.get("label") or wd.get("name") or wd.get("wave") or "Wave"
        when = wd.get("when") or wd.get("timepoint") or wd.get("week")
        out.append(f"### {label}" + (f" ({when})" if when not in (None, "") else "") + "\n")
        out.append((wd.get("purpose") or wd.get("notes") or "").rstrip())
        measures = _as_list(wd.get("measures") or wd.get("assessments"))
        if measures:
            out.append("\n**Measures**")
            for m in measures:
                md = _to_dict(m)
                if isinstance(md, dict):
                    nm = md.get("name") or md.get("construct") or "measure"
                    out.append(f"- {nm}")
                    for k in ("instrument", "task", "modality", "window", "reporter", "duration_min", "quality_checks"):
                        if md.get(k) not in (None, "", [], {}):
                            out.append(f"  - {k}: {md.get(k)}")
                else:
                    out.append(f"- {md}")
        out.append("")
    return "\n".join([x for x in out if x is not None]).rstrip() + "\n"

def _render_causal_tests_md(plan_d: Dict[str, Any]) -> str:
    tests = _as_list(plan_d.get("causal_tests") or plan_d.get("analyses") or plan_d.get("hypothesis_tests"))
    if not tests:
        return ""
    out = ["## Causal-chain tests (mediation, moderation, transfer, durability)\n"]
    for i, t in enumerate(tests, 1):
        td = _to_dict(t)
        name = td.get("name") or td.get("type") or f"Test {i}"
        out.append(f"### {i}. {name}\n")
        out.append(_md_kv("Purpose", td.get("purpose") or td.get("question")).rstrip("\n"))
        for k in ("estimand", "model", "identification", "assumptions", "covariates", "missing_data", "multiple_testing", "robustness"):
            out.append(_md_kv(k.replace("_", " ").title(), td.get(k)).rstrip("\n"))
        chain = td.get("causal_chain") or td.get("path") or {}
        if chain:
            out.append("**Causal chain**")
            cd = chain if isinstance(chain, dict) else _to_dict(chain)
            if isinstance(cd, dict):
                out.append(_md_kv("Treatment", cd.get("treatment") or cd.get("X")).rstrip("\n"))
                out.append(_md_kv("Mediator(s)", cd.get("mediators") or cd.get("M")).rstrip("\n"))
                out.append(_md_kv("Outcome(s)", cd.get("outcomes") or cd.get("Y")).rstrip("\n"))
                out.append(_md_kv("Moderators", cd.get("moderators") or cd.get("W")).rstrip("\n"))
                out.append(_md_kv("Time ordering", cd.get("time_ordering") or cd.get("temporal_order")).rstrip("\n"))
            else:
                out.append(f"- {cd}")
        out.append("")
    return "\n".join([ln for ln in out if ln is not None and ln != ""]).rstrip() + "\n"

def _render_logistics_md(plan_d: Dict[str, Any]) -> str:
    logi = plan_d.get("logistics") or plan_d.get("operations") or plan_d.get("checklists")
    if not logi:
        return ""
    ld = _to_dict(logi)
    out = ["## Logistics to compare transfer & durability within cohorts\n"]
    if isinstance(ld, dict):
        for section in ("randomization", "implementation", "fidelity", "blinding", "data_collection", "retention", "ethics", "power", "sites", "staffing", "materials", "platforms", "adverse_events"):
            v = ld.get(section)
            if v in (None, "", [], {}):
                continue
            out.append(f"### {section.replace('_',' ').title()}\n")
            if isinstance(v, list):
                for item in v:
                    out.append(f"- {_to_dict(item)}")
            elif isinstance(v, dict):
                for k, item in v.items():
                    out.append(f"- {k}: {_to_dict(item)}")
            else:
                out.append(str(v))
            out.append("")
    else:
        out.append(str(ld) + "\n")
    return "\n".join(out).rstrip() + "\n"

def render_plan_markdown(plan: Any) -> str:
    d = _to_dict(plan) if not isinstance(plan, dict) else plan
    title = d.get("title") or d.get("name") or "Multi-wave randomized intervention trial plan"
    summary = d.get("summary") or d.get("mission_summary") or d.get("overview")
    out = [f"# {title}\n"]
    if summary:
        out.append(str(summary).rstrip() + "\n")
    out.append("## Core construct linkage (mechanism)\n")
    mech = d.get("mechanism") or d.get("theory_of_change") or {}
    if mech:
        out.append(_md_kv("Within-child cognitive growth", _get(mech, "cognitive_growth") or _get(mech, "within_child_growth")).rstrip("\n"))
        out.append(_md_kv("Mediators (EF / processing speed)", _get(mech, "mediators") or _get(mech, "proximal_mediators")).rstrip("\n"))
        out.append(_md_kv("Reasoning", _get(mech, "reasoning")).rstrip("\n"))
        out.append(_md_kv("Real-world decisions", _get(mech, "decisions") or _get(mech, "decision_outcomes")).rstrip("\n"))
        out.append(_md_kv("Social support (ZPD)", _get(mech, "zpd") or _get(mech, "social_support")).rstrip("\n"))
        out.append("")
    else:
        out.append("- **Within-child cognitive growth** (executive function + processing speed) → **reasoning** → **real-world decisions**.\n- **ZPD social support** is operationalized by **type**, **timing**, and **fading**; tested as mediator and moderator.\n")
    arms_md = _render_arms_md(d)
    if arms_md:
        out.append(arms_md)
    timeline_md = _render_timeline_md(d)
    if timeline_md:
        out.append(timeline_md)
    measures = d.get("measures") or {}
    if measures:
        out.append("## Measures catalog\n")
        md = _to_dict(measures)
        if isinstance(md, dict):
            for k, v in md.items():
                out.append(f"### {k.replace('_',' ').title()}\n")
                if isinstance(v, list):
                    for it in v:
                        out.append(f"- {_to_dict(it)}")
                else:
                    out.append(str(_to_dict(v)))
                out.append("")
        else:
            out.append(str(md) + "\n")
    tests_md = _render_causal_tests_md(d)
    if tests_md:
        out.append(tests_md)
    logi_md = _render_logistics_md(d)
    if logi_md:
        out.append(logi_md)
    return "\n".join([s for s in out if s is not None]).rstrip() + "\n"
