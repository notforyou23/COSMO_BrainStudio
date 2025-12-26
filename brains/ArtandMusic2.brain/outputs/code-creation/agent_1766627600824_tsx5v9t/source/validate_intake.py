#!/usr/bin/env python3
"""Command-line intake validator for claim cards.

Hard-requires:
(a) verbatim claim text
(b) dataset name + DOI/link (or fallback: research area + >=2 seed papers/authors)
(c) context metadata: who/when/where

Blocks work by exiting non-zero with actionable errors when anchors are missing/invalid.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?$")


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_card(path: Path) -> Dict[str, Any]:
    text = _load_text(path).strip()
    if not text:
        raise ValueError("File is empty.")
    suf = path.suffix.lower()
    if suf in {".json"}:
        return json.loads(text)
    if suf in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:
            raise ValueError(f"YAML support unavailable (install PyYAML). Underlying error: {e}")
        obj = yaml.safe_load(text)
        if obj is None:
            raise ValueError("YAML parsed to null/None.")
        return obj
    # Try JSON, then YAML
    try:
        return json.loads(text)
    except Exception:
        try:
            import yaml  # type: ignore
        except Exception as e:
            raise ValueError(f"Unknown file extension '{suf}' and YAML support unavailable. Underlying error: {e}")
        obj = yaml.safe_load(text)
        if obj is None:
            raise ValueError("Parsed to null/None.")
        return obj


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _get(d: Any, path: str) -> Any:
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _pointer(path: str) -> str:
    return "/" + "/".join(path.split("."))


def validate_card(card: Any) -> List[Tuple[str, str]]:
    errs: List[Tuple[str, str]] = []
    if not isinstance(card, dict):
        return [("/", "Top-level must be an object/dict.")]

    # (a) verbatim claim text
    claim_text = _get(card, "claim.text")
    if claim_text is None:
        claim_text = card.get("claim_text") or card.get("claim") if isinstance(card.get("claim"), str) else None
    if not _is_nonempty_str(claim_text):
        errs.append(("/claim/text", "Missing verbatim claim text. Provide claim.text (non-empty string)."))

    # (c) context metadata who/when/where
    ctx = card.get("context")
    if not isinstance(ctx, dict):
        errs.append(("/context", "Missing context object. Provide context.who, context.when, context.where."))
        ctx = {}
    who = ctx.get("who")
    when = ctx.get("when")
    where = ctx.get("where")

    who_ok = _is_nonempty_str(who) or (isinstance(who, list) and any(_is_nonempty_str(i) for i in who))
    if not who_ok:
        errs.append(("/context/who", "Missing context.who. Provide who created/entered the claim (name/handle or list)."))
    if not _is_nonempty_str(where):
        errs.append(("/context/where", "Missing context.where. Provide where the claim appeared (paper/blog/talk/org/etc.)."))
    if not _is_nonempty_str(when) or not ISO_DATE_RE.match(str(when).strip()):
        errs.append(("/context/when", "Missing/invalid context.when. Provide ISO-like date/time (e.g., 2024-01-31 or 2024-01-31T12:00:00Z)."))

    # (b) dataset name + DOI/link OR fallback: research area + >=2 seed papers/authors
    prov = card.get("provenance")
    if not isinstance(prov, dict):
        prov = {}
    dataset = prov.get("dataset") or card.get("dataset")
    fallback = prov.get("fallback") or card.get("fallback")

    def dataset_ok(ds: Any) -> bool:
        if not isinstance(ds, dict):
            return False
        name = ds.get("name") or ds.get("dataset_name")
        link = ds.get("doi") or ds.get("url") or ds.get("link") or ds.get("doi_or_url")
        return _is_nonempty_str(name) and _is_nonempty_str(link)

    def fallback_ok(fb: Any) -> Tuple[bool, str]:
        if not isinstance(fb, dict):
            return (False, "Provide provenance.fallback object with research_area and seed_papers/authors.")
        ra = fb.get("research_area") or fb.get("area")
        if not _is_nonempty_str(ra):
            return (False, "Fallback requires fallback.research_area (non-empty string).")
        seeds = fb.get("seed_papers") or fb.get("seed_refs") or fb.get("seed_sources") or fb.get("seeds")
        seeds_l = _as_list(seeds)
        if len(seeds_l) < 2:
            return (False, "Fallback requires >=2 seed_papers/authors (at least two anchors).")
        good = 0
        for s in seeds_l:
            if _is_nonempty_str(s):
                good += 1
                continue
            if isinstance(s, dict):
                if _is_nonempty_str(s.get("doi") or s.get("url") or s.get("link") or s.get("citation") or s.get("title")):
                    good += 1
                    continue
                authors = s.get("authors")
                if _is_nonempty_str(authors) or (isinstance(authors, list) and any(_is_nonempty_str(a) for a in authors)):
                    good += 1
                    continue
        if good < 2:
            return (False, "Fallback seed_papers must include >=2 usable anchors (citation/title/doi/url or authors).")
        return (True, "")

    has_dataset = dataset_ok(dataset)
    has_fallback, fb_msg = fallback_ok(fallback) if not has_dataset else (False, "")

    if not has_dataset and not has_fallback:
        errs.append(("/provenance/dataset", "Missing dataset anchor. Provide provenance.dataset.name + provenance.dataset.doi/url (or use fallback)."))
        errs.append(("/provenance/fallback", f"Fallback not satisfied. {fb_msg}"))

    # Additional provenance anchors: prefer explicit sources; warn-as-error if completely absent
    sources = prov.get("sources") or prov.get("citations") or card.get("sources")
    sources_l = _as_list(sources)
    if len(sources_l) == 0 and has_dataset is False and has_fallback is False:
        errs.append(("/provenance/sources", "No provenance sources provided. Add provenance.sources (links/DOIs/citations)."))
    return errs


def format_errors(path: Path, errs: List[Tuple[str, str]]) -> str:
    lines = [f"{path}: VALIDATION_FAILED ({len(errs)} issues)"]
    for ptr, msg in errs:
        lines.append(f"  - {ptr}: {msg}")
    return "\n".join(lines)


def _collect_paths(inputs: List[str]) -> List[Path]:
    out: List[Path] = []
    for s in inputs:
        p = Path(s)
        if any(ch in s for ch in "*?[") and not p.exists():
            out.extend(sorted(Path().glob(s)))
            continue
        if p.is_dir():
            for ext in ("*.json", "*.yml", "*.yaml"):
                out.extend(sorted(p.rglob(ext)))
        else:
            out.append(p)
    # Dedup while preserving order
    seen = set()
    uniq = []
    for p in out:
        rp = str(p.resolve())
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


def pilot_claim() -> Dict[str, Any]:
    return {
        "claim": {"text": "On ImageNet-1K, Model X achieves 85.2% top-1 accuracy under standard single-crop evaluation."},
        "provenance": {
            "dataset": {"name": "ImageNet-1K", "doi": "https://www.image-net.org/"},
            "sources": [{"citation": "Deng et al., 2009 (ImageNet)"}],
        },
        "context": {"who": "intake_operator@example.org", "when": "2025-12-25", "where": "internal intake pilot"},
    }


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Validate claim card intake requirements.")
    ap.add_argument("paths", nargs="*", help="Claim card files/dirs/globs (.json/.yml/.yaml)")
    ap.add_argument("--pilot-test", action="store_true", help="Run a single embedded dataset-verification pilot claim.")
    args = ap.parse_args(argv)

    if args.pilot_test:
        errs = validate_card(pilot_claim())
        if errs:
            print("PILOT_TEST_FAILED")
            print(format_errors(Path("<embedded_pilot_claim>"), errs))
            return 2
        print("PILOT_TEST_PASSED")
        return 0

    if not args.paths:
        ap.print_usage(sys.stderr)
        print("ERROR: Provide at least one path (file/dir/glob) or use --pilot-test.", file=sys.stderr)
        return 2

    paths = _collect_paths(args.paths)
    if not paths:
        print("ERROR: No matching claim card files found.", file=sys.stderr)
        return 2

    any_fail = False
    for p in paths:
        try:
            card = load_card(p)
        except Exception as e:
            any_fail = True
            print(f"{p}: LOAD_FAILED: {e}")
            continue
        errs = validate_card(card)
        if errs:
            any_fail = True
            print(format_errors(p, errs))

    if any_fail:
        return 1
    print(f"OK: validated {len(paths)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
