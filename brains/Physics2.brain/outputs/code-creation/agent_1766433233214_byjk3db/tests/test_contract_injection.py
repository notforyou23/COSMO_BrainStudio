import re
from textwrap import dedent

import pytest

from cosmo_contracts.markdown import upsert_contract_sections


REQUIRED_SUBSECTIONS = [
    r"^\*\*Required metadata\*\*$",
    r"^\*\*Reference algorithm / pseudocode\*\*$",
    r"^\*\*Output invariants\*\*$",
    r"^\*\*Tolerance policy\*\*$",
    r"^\*\*Canonical test vector\*\*$",
    r"^\*\*Contract compliance reporting\*\*$",
]


def _contract_blocks(md: str):
    """Return list of (benchmark_id, contract_text|None) for each `## ...` section."""
    bench = re.compile(r"^##\s+(.+?)\s*$", re.M)
    out = []
    starts = [(m.start(), m.end(), m.group(1)) for m in bench.finditer(md)]
    if not starts:
        return out
    starts.append((len(md), len(md), "__END__"))
    for (_, e, bid), (ns, _, _) in zip(starts, starts[1:]):
        section = md[e:ns]
        m = re.search(r"(?m)^###\s+Contract\s*$", section)
        if not m:
            out.append((bid, None))
            continue
        c_start = e + m.start()
        rest = md[c_start:ns]
        m2 = re.search(r"(?m)^###\s+(?!Contract\b).+$", rest)
        c_end = c_start + (m2.start() if m2 else len(rest))
        out.append((bid, md[c_start:c_end].strip("\n")))
    return out


def _assert_contract_has_required_parts(contract: str):
    assert contract is not None
    lines = contract.splitlines()
    assert lines[0].strip() == "### Contract"
    for pat in REQUIRED_SUBSECTIONS:
        assert any(re.match(pat, ln.strip()) for ln in lines), f"missing subsection {pat}"
    assert "```json" in contract
    assert contract.count("```") >= 2
    assert re.search(r"(?m)^- `pass`:\s*boolean\s*$", contract)
    assert re.search(r"(?m)^- `diagnostics`:\s*list of human-readable strings", contract)
def test_inserts_contracts_and_is_idempotent():
    md = dedent('''
        # COSMO Benchmarks v0.1

        ## BM001: toy
        Some description.

        ### Notes
        - blah

        ## BM002: other
        More text.
    ''').strip() + "\n"

    res1 = upsert_contract_sections(md)
    assert set(res1.updated_ids) == {"BM001: toy", "BM002: other"}
    out1 = res1.text
    assert "### Contract" in out1

    blocks = dict(_contract_blocks(out1))
    assert set(blocks) == {"BM001: toy", "BM002: other"}
    _assert_contract_has_required_parts(blocks["BM001: toy"])
    _assert_contract_has_required_parts(blocks["BM002: other"])

    res2 = upsert_contract_sections(out1)
    assert res2.text == out1
    assert set(res2.updated_ids) == {"BM001: toy", "BM002: other"}
def test_replaces_existing_contract_deterministically():
    md = dedent('''
        # COSMO Benchmarks v0.1

        ## BM003: replace-me

        ### Contract
        **Required metadata**
        - junk: true

        ### Details
        Something.
    ''').lstrip()

    out = upsert_contract_sections(md).text
    blocks = dict(_contract_blocks(out))
    c = blocks["BM003: replace-me"]
    _assert_contract_has_required_parts(c)
    assert "junk: true" not in c

    sec = re.search(r"(?s)##\s+BM003: replace-me\s*(.+)", out).group(1)
    assert sec.index("### Contract") < sec.index("### Details")
