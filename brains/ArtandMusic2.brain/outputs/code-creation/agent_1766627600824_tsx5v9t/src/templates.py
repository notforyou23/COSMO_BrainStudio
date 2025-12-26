"""Canonical templates for generating rights & licensing outputs.

This module is the single source of truth for:
- Markdown checklist content for rights/licensing verification.
- CSV fieldnames and starter rows for a rights log.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List, Optional


RIGHTS_LOG_FIELDS: List[str] = [
    "asset_id",
    "url",
    "rightsholder",
    "license type",
    "usage permissions",
    "attribution text",
    "restrictions",
    "verification date",
    "reviewer",
]


@dataclass(frozen=True)
class RightsLogRow:
    asset_id: str = "ASSET_001"
    url: str = "https://example.com/asset"
    rightsholder: str = "Rightsholder / Author / Publisher"
    license_type: str = "License type (e.g., CC BY 4.0, Standard, Custom permission)"
    usage_permissions: str = "Permitted uses (e.g., web, print, social, internal, paid ads)"
    attribution_text: str = "Attribution to use (if required), including link/credit line"
    restrictions: str = "Restrictions (e.g., no edits, editorial-only, territory, expiry)"
    verification_date: str = ""
    reviewer: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {
            "asset_id": self.asset_id,
            "url": self.url,
            "rightsholder": self.rightsholder,
            "license type": self.license_type,
            "usage permissions": self.usage_permissions,
            "attribution text": self.attribution_text,
            "restrictions": self.restrictions,
            "verification date": self.verification_date,
            "reviewer": self.reviewer,
        }


def csv_fieldnames() -> List[str]:
    """Return the canonical fieldnames for RIGHTS_LOG.csv."""
    return list(RIGHTS_LOG_FIELDS)


def csv_header_line() -> str:
    """Return the CSV header line (comma-separated)."""
    return ",".join(csv_fieldnames())


def seed_rows(
    *,
    today: Optional[date] = None,
    reviewer: str = "",
    include_example: bool = True,
) -> List[Dict[str, str]]:
    """Return sensible starter rows for a new rights log.

    Set include_example=False to emit an empty dataset (header only).
    """
    if not include_example:
        return []
    d = today.isoformat() if today else ""
    row = RightsLogRow(verification_date=d, reviewer=reviewer).as_dict()
    return [row]


def checklist_markdown(
    *,
    project_name: str = "Rights & Licensing Review",
    reviewer: str = "",
    generated_on: Optional[date] = None,
) -> str:
    """Return the canonical markdown checklist for RIGHTS_AND_LICENSING_CHECKLIST.md."""
    gen = generated_on.isoformat() if generated_on else ""
    rev = reviewer or "________________"
    return f"""# RIGHTS AND LICENSING CHECKLIST

Project: **{project_name}**
Generated on: **{gen or '________________'}**
Reviewer: **{rev}**

## 1) Asset Inventory (Scope)
- [ ] Create/confirm a complete list of assets (images, icons, fonts, audio, video, datasets, code snippets, brand marks).
- [ ] Assign a unique **asset_id** for each item and enter it into `RIGHTS_LOG.csv`.
- [ ] Record the canonical source URL (or internal path) and any alternate sources/mirrors.

## 2) Identify the Rightsholder
For each asset:
- [ ] Identify the rightsholder (creator, publisher, agency, employer, or platform).
- [ ] Confirm whether the uploader is authorized to grant rights (especially for social/platform uploads).
- [ ] If multiple contributors exist, confirm rights for all relevant components (e.g., photo + model + trademark).

## 3) License / Permission Verification
- [ ] Record the **license type** in the log (e.g., Creative Commons, public domain, commercial stock, custom written permission).
- [ ] Save evidence (license page screenshot, invoice/receipt, email permission, contract clause reference).
- [ ] Confirm the license version and any platform-specific terms that apply.
- [ ] Confirm whether sublicensing is allowed (client, partners, affiliates).

## 4) Usage Permissions (Intended Use vs. Allowed Use)
Confirm for each asset:
- [ ] Where it will be used (web/app, print, broadcast, social, ads, email, internal).
- [ ] Whether commercial use is permitted.
- [ ] Whether modification/derivatives/cropping is permitted.
- [ ] Whether attribution is required and in what format.
- [ ] Whether AI training/ML usage is permitted (if applicable to your context).

## 5) Restrictions & Risk Flags
- [ ] Editorial-only restrictions (no commercial/promotional use).
- [ ] Territory limitations (country/region).
- [ ] Term/expiry date and renewal requirements.
- [ ] Exclusivity constraints and conflicts.
- [ ] “No resale,” “no templates,” “no redistribution,” “no standalone use,” or “no use in logos” clauses.
- [ ] Trademark/brand/logo appearances that may require additional permission.
- [ ] Privacy/publicity concerns (identifiable people, private locations).

## 6) Releases (When Applicable)
- [ ] Model releases for identifiable individuals (including minors—guardian consent).
- [ ] Property releases for private property, interiors, or restricted locations.
- [ ] Event/venue terms (tickets, credentials, posted policies).

## 7) Attribution & Notice Requirements
- [ ] Prepare exact attribution text (credit line) and required links.
- [ ] Verify placement requirements (caption, footer, credits page, metadata).
- [ ] Note any “share-alike” or “copyleft” obligations (including downstream distribution requirements).

## 8) Documentation & Storage
- [ ] Store proof of permission/license in an accessible location (with the asset_id).
- [ ] Ensure the rights log is up to date and reflects the current planned usage.
- [ ] Record the verification date and reviewer for each asset.

## 9) Final Review & Sign-off
- [ ] Spot-check high-risk assets (faces, brands, editorial sources, unclear provenance).
- [ ] Remove or replace any asset with unclear/insufficient rights.
- [ ] Confirm outputs match the approved scope and distribution channels.

### Reviewer Sign-off
I confirm that the rights and licensing entries in `RIGHTS_LOG.csv` have been verified to the best of my knowledge for the intended use.

Name: _______________________
Date: _______________________
Signature/Initials: __________

"""


def normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    """Return a row dict containing exactly the canonical CSV fields."""
    out: Dict[str, str] = {}
    for k in RIGHTS_LOG_FIELDS:
        out[k] = str(row.get(k, "") if row.get(k, "") is not None else "")
    return out


def normalize_rows(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    return [normalize_row(r) for r in rows]
