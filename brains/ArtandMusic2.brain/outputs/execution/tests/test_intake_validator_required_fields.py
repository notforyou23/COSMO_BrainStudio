import pytest

from src.claims.intake_validator import validate_claim_card
def _valid_claim_card():
    return {
        "claim_id": "C-001",
        "claim_text": "District X increased graduation rates from 2019 to 2023.",
        "dataset_anchor": {
            "dataset_id": "district_x_admin_records_v3",
            "anchor": "graduation_rates.csv#row=12..24;cols=year,rate",
        },
        "primary_source_verification": {
            "source_type": "dataset",
            "source_citation": "District X admin dataset (v3), Graduation Rates table.",
            "verification_steps": [
                "Open referenced file and navigate to anchored rows/columns.",
                "Confirm rates for 2019 and 2023 and compute change.",
            ],
        },
    }
def test_validator_fails_when_claim_text_missing():
    card = _valid_claim_card()
    card.pop("claim_text", None)
    with pytest.raises(ValueError, match=r"claim_text"):
        validate_claim_card(card)
def test_validator_fails_when_claim_text_blank():
    card = _valid_claim_card()
    card["claim_text"] = "   "
    with pytest.raises(ValueError, match=r"claim_text"):
        validate_claim_card(card)
def test_validator_fails_when_dataset_anchor_missing():
    card = _valid_claim_card()
    card.pop("dataset_anchor", None)
    with pytest.raises(ValueError, match=r"dataset_anchor"):
        validate_claim_card(card)
def test_validator_fails_when_dataset_anchor_empty():
    card = _valid_claim_card()
    card["dataset_anchor"] = {}
    with pytest.raises(ValueError, match=r"dataset_anchor"):
        validate_claim_card(card)
def test_validator_passes_when_required_fields_present_and_well_formed():
    card = _valid_claim_card()
    validate_claim_card(card)
