from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


def _import_validator():
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import importlib

    try:
        return importlib.import_module("source.validate_intake")
    except ModuleNotFoundError:
        return importlib.import_module("validate_intake")


def _write_card(tmp_path: Path, card: dict) -> Path:
    p = tmp_path / "claim_card.json"
    p.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def _run_validator(mod, card_path: Path):
    # Prefer a direct API if available; otherwise use CLI-style main().
    for name in (
        "validate_claim_card_file",
        "validate_claim_card_path",
        "validate_file",
        "validate_path",
    ):
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn(card_path)

    main = getattr(mod, "main", None)
    if callable(main):
        return main([str(card_path)])

    raise RuntimeError("validate_intake: no supported entrypoint found")


def _assert_invalid(mod, card_path: Path, *needles: str):
    try:
        _run_validator(mod, card_path)
    except SystemExit as e:
        assert int(getattr(e, "code", 1) or 0) != 0
        msg = str(e)
    except Exception as e:
        msg = str(e)

    low = msg.lower()
    for n in needles:
        assert n.lower() in low, f"Expected '{n}' in error message. Got: {msg!r}"


def _pilot_valid_card() -> dict:
    return {
        "id": "pilot-ukb-001",
        "claim_text_verbatim": "Higher BMI is associated with higher systolic blood pressure in adults.",
        "dataset": {
            "name": "UK Biobank",
            "link": "https://www.ukbiobank.ac.uk/",
        },
        "provenance_anchors": {
            "dataset_name": "UK Biobank",
            "dataset_link": "https://www.ukbiobank.ac.uk/",
        },
        "context": {
            "who": "Intake analyst",
            "when": "2025-12-25",
            "where": "UK Biobank online documentation",
        },
    }
def test_valid_pilot_claim_passes(tmp_path: Path):
    mod = _import_validator()
    card = _pilot_valid_card()
    p = _write_card(tmp_path, card)
    _run_validator(mod, p)


def test_missing_verbatim_claim_text_fails(tmp_path: Path):
    mod = _import_validator()
    card = _pilot_valid_card()
    card.pop("claim_text_verbatim", None)
    p = _write_card(tmp_path, card)
    _assert_invalid(mod, p, "claim", "verbatim", "claim_text")


def test_missing_dataset_and_fallback_anchors_blocks_work(tmp_path: Path):
    mod = _import_validator()
    card = _pilot_valid_card()
    card.pop("dataset", None)
    card.pop("provenance_anchors", None)
    # Also ensure no fallback is present.
    card.pop("research_area", None)
    card.pop("seed_papers", None)
    p = _write_card(tmp_path, card)
    _assert_invalid(mod, p, "dataset", "doi", "link")


def test_missing_context_metadata_blocks_work(tmp_path: Path):
    mod = _import_validator()
    card = _pilot_valid_card()
    card["context"] = {"who": "Intake analyst"}  # missing when/where
    p = _write_card(tmp_path, card)
    _assert_invalid(mod, p, "context", "when", "where")
