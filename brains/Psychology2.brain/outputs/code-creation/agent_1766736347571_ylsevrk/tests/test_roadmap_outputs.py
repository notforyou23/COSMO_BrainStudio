import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

import pytest


def _norm(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _run_cli(args: List[str]) -> str:
    env = dict(os.environ)
    env.setdefault("PYTHONHASHSEED", "0")
    env.setdefault("LC_ALL", "C")
    env.setdefault("LANG", "C")
    p = subprocess.run(
        [sys.executable, "-m", "psyprim.cli", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    return p.stdout.strip()


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(text)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _api_output(kind: str) -> Optional[Dict[str, Any]]:
    try:
        import psyprim  # type: ignore
    except Exception:
        return None

    candidates = {
        "roadmap": ["generate_roadmap", "build_roadmap", "roadmap"],
        "checklist": ["generate_checklist", "build_checklist", "checklist"],
        "instruments": ["generate_instruments", "build_instruments", "instruments"],
    }[kind]

    for name in candidates:
        fn = getattr(psyprim, name, None)
        if not callable(fn):
            continue
        for kwargs in ({}, {"format": "json"}, {"output_format": "json"}):
            try:
                out = fn(**kwargs)
            except TypeError:
                continue
            if isinstance(out, dict):
                return out
            if isinstance(out, str):
                obj = _try_parse_json(out)
                if obj:
                    return obj
    return None


def _cli_output(kind: str) -> Dict[str, Any]:
    cmd_sets = {
        "roadmap": [
            ["roadmap", "--format", "json"],
            ["generate", "roadmap", "--format", "json"],
            ["generate-roadmap", "--format", "json"],
            ["roadmap", "--json"],
        ],
        "checklist": [
            ["checklist", "--format", "json"],
            ["generate", "checklist", "--format", "json"],
            ["generate-checklist", "--format", "json"],
            ["checklist", "--json"],
        ],
        "instruments": [
            ["instruments", "--format", "json"],
            ["generate", "instruments", "--format", "json"],
            ["generate-instruments", "--format", "json"],
            ["instruments", "--json"],
        ],
    }[kind]

    last_err = None
    for args in cmd_sets:
        try:
            out = _run_cli(args)
            obj = _try_parse_json(out)
            if obj:
                return obj
        except Exception as e:
            last_err = e
            continue
    raise AssertionError(f"Could not produce JSON for {kind} via CLI. Last error: {last_err!r}")


def get_output(kind: str) -> Dict[str, Any]:
    obj = _api_output(kind)
    if obj:
        return obj
    return _cli_output(kind)


def _lower_str_blob(obj: Any) -> str:
    try:
        return _norm(obj).lower()
    except Exception:
        return str(obj).lower()


def _assert_contains_any(hay: str, needles: List[str]) -> None:
    for n in needles:
        if n in hay:
            return
    raise AssertionError(f"Missing all of: {needles}")


def _assert_keypath(d: Dict[str, Any], keys: List[str]) -> Any:
    cur: Any = d
    for k in keys:
        assert isinstance(cur, dict), f"Expected dict at {k} in path {keys}, got {type(cur)}"
        assert k in cur, f"Missing key {k} in path {keys}"
        cur = cur[k]
    return cur


def test_outputs_are_deterministic_and_valid_json() -> None:
    for kind in ("roadmap", "checklist", "instruments"):
        a = get_output(kind)
        b = get_output(kind)
        assert isinstance(a, dict) and isinstance(b, dict)
        assert _norm(a) == _norm(b), f"{kind} output must be deterministic"


def test_roadmap_contains_required_mission_elements() -> None:
    rm = get_output("roadmap")
    blob = _lower_str_blob(rm)

    _assert_contains_any(blob, ["survey", "questionnaire"])
    _assert_contains_any(blob, ["audit study", "audit", "field audit"])
    _assert_contains_any(blob, ["repository", "repositories", "archive", "archives"])
    _assert_contains_any(blob, ["metadata", "checklist"])
    _assert_contains_any(blob, ["workflow", "workflows"])

    # Key technical detection features
    _assert_contains_any(blob, ["edition", "edition provenance"])
    _assert_contains_any(blob, ["translation", "translator"])
    _assert_contains_any(blob, ["variant pagination", "pagination variants", "page variant", "page mapping"])
    _assert_contains_any(blob, ["repository citation", "repository citations", "catalog", "call number", "shelfmark"])

    # Specialist-agent task assignment signals
    _assert_contains_any(blob, ["agent", "specialist", "librarian", "archivist"])
    _assert_contains_any(blob, ["nlp", "engineer", "developer", "data", "qa", "evaluation"])


def test_checklist_has_core_primary_source_metadata_fields() -> None:
    ck = get_output("checklist")
    blob = _lower_str_blob(ck)
    _assert_contains_any(blob, ["edition"])
    _assert_contains_any(blob, ["translation", "translator"])
    _assert_contains_any(blob, ["publisher", "imprint"])
    _assert_contains_any(blob, ["year", "date of publication", "publication date"])
    _assert_contains_any(blob, ["page", "pagination"])
    _assert_contains_any(blob, ["repository", "archive", "library", "collection"])
    _assert_contains_any(blob, ["identifier", "doi", "isbn", "oclc", "url"])


def test_instruments_include_survey_and_audit_measures() -> None:
    ins = get_output("instruments")
    blob = _lower_str_blob(ins)

    _assert_contains_any(blob, ["survey"])
    _assert_contains_any(blob, ["audit"])
    _assert_contains_any(blob, ["likert", "scale", "multiple choice", "open-ended", "open ended"])
    _assert_contains_any(blob, ["primary source", "original", "facsimile"])

    # Prefer explicit sections when present
    for key in ("survey", "audit"):
        if isinstance(ins.get(key, None), dict):
            sec = ins[key]
            assert isinstance(sec, dict)
            # At least one plausible question container key
            qkeys = {"questions", "items", "prompts", "measures"}
            assert any(k in sec for k in qkeys), f"Expected {key} section to include one of {sorted(qkeys)}"
