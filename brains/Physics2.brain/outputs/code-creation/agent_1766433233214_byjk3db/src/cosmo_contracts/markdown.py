from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable, Dict, Iterable, List, Optional


_CONTRACT_TITLE = "### Contract"


@dataclass(frozen=True)
class ContractInsertResult:
    text: str
    updated_ids: List[str]


def _default_contract_md(benchmark_id: str) -> str:
    # A deterministic, benchmark-agnostic contract block; other modules may
    # provide a richer contract generator via `contract_for_id`.
    return "\n".join(
        [
            _CONTRACT_TITLE,
            "",
            "**Required metadata**",
            "",
            "- `benchmark_id`: `" + benchmark_id + "`",
            "- `version`: `v0.1`",
            "- `name`: human-readable name (must be reported by implementations)",
            "- `input_spec`: description of inputs and domains",
            "- `output_spec`: description of outputs, units, and shapes",
            "",
            "**Reference algorithm / pseudocode**",
            "",
            "Implementations MUST document the algorithm used and MUST match the",
            "reference behavior on the canonical test vector(s). If an official",
            "reference is provided for this benchmark, it overrides this generic policy.",
            "",
            "**Output invariants**",
            "",
            "- Output MUST be deterministic for a fixed input.",
            "- Output MUST be serializable as JSON (numbers, strings, lists, dicts).",
            "- NaN/Inf are forbidden unless explicitly specified by the benchmark.",
            "",
            "**Tolerance policy**",
            "",
            "- Exact match for non-floats (strings, integers, booleans).",
            "- For floats: absolute tolerance `1e-9` and relative tolerance `1e-9`, unless",
            "  a benchmark-specific contract states otherwise.",
            "",
            "**Canonical test vector**",
            "",
            "```json",
            "{",
            '  "benchmark_id": "' + benchmark_id + '",',
            '  "version": "v0.1",',
            '  "input": {"seed": 0},',
            '  "expected_output": null',
            "}",
            "```",
            "",
            "**Contract compliance reporting**",
            "",
            "Every contributed implementation MUST report contract compliance as:",
            "",
            "- `pass`: boolean",
            "- `diagnostics`: list of human-readable strings (empty when pass is true)",
        ]
    )


def _find_headings(lines: List[str], pattern: re.Pattern) -> List[tuple[int, str]]:
    out: List[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        m = pattern.match(ln)
        if m:
            out.append((i, m.group(1).strip()))
    return out


def upsert_contract_sections(
    markdown_text: str,
    contract_for_id: Optional[Callable[[str], str]] = None,
    benchmark_heading_re: str = r"^##\s+(.+?)\s*$",
) -> ContractInsertResult:
    \"\"\"Insert/replace a standardized Contract section per v0.1 benchmark.

    Benchmarks are detected as level-2 headings (`## ...`). Within each benchmark
    section, a level-3 heading `### Contract` is inserted after the benchmark
    heading (or replaced if present). The rewrite is idempotent.
    \"\"\"
    contract_for_id = contract_for_id or _default_contract_md
    lines = markdown_text.splitlines()
    bench_pat = re.compile(benchmark_heading_re)
    benches = _find_headings(lines, bench_pat)
    if not benches:
        return ContractInsertResult(text=markdown_text, updated_ids=[])

    # Add sentinel end.
    benches = benches + [(len(lines), "__END__")]
    updated: List[str] = []

    for (start, bench_id), (end, _) in zip(benches, benches[1:]):
        if bench_id == "__END__":
            continue
        section = lines[start:end]
        # Locate an existing contract block within this section.
        contract_start = None
        for j in range(1, len(section)):
            if section[j].strip() == _CONTRACT_TITLE:
                contract_start = j
                break

        new_block = contract_for_id(bench_id).splitlines()
        if not new_block or new_block[0].strip() != _CONTRACT_TITLE:
            raise ValueError("contract_for_id must return markdown starting with '### Contract'")

        if contract_start is None:
            # Insert after heading and an optional following blank line.
            insert_at = 1
            while insert_at < len(section) and section[insert_at].strip() == "":
                insert_at += 1
            section = section[:insert_at] + [""] + new_block + [""] + section[insert_at:]
            updated.append(bench_id)
        else:
            # Replace until next level-3 heading or end-of-section.
            contract_end = len(section)
            h3 = re.compile(r"^###\s+")
            for k in range(contract_start + 1, len(section)):
                if h3.match(section[k]) and section[k].strip() != _CONTRACT_TITLE:
                    contract_end = k
                    break
            before = section[:contract_start]
            after = section[contract_end:]
            # Normalize surrounding blank lines.
            while before and before[-1].strip() == "":
                before.pop()
            while after and after[0].strip() == "":
                after.pop(0)
            section = before + [""] + new_block + [""] + after
            updated.append(bench_id)

        lines[start:end] = section
        # Adjust subsequent indices by recomputing headings would be expensive; instead
        # restart scan by recomputing benches on the mutated lines.
        # The number of benchmarks is small; simplicity > micro-optimizations.
        benches = _find_headings(lines, bench_pat) + [(len(lines), "__END__")]

    return ContractInsertResult(text="\\n".join(lines) + ("" if markdown_text.endswith("\\n") else ""), updated_ids=updated)


def rewrite_benchmarks_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    contract_for_id: Optional[Callable[[str], str]] = None,
) -> List[str]:
    \"\"\"Rewrite `input_path` inserting/updating Contract sections; returns updated ids.\"\"\"
    md = input_path.read_text(encoding="utf-8")
    res = upsert_contract_sections(md, contract_for_id=contract_for_id)
    outp = output_path or input_path
    outp.write_text(res.text if res.text.endswith("\\n") else res.text + "\\n", encoding="utf-8")
    return res.updated_ids
