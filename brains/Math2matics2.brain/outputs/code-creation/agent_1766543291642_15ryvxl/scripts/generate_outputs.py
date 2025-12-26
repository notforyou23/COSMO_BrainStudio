#!/usr/bin/env python3
"""Deterministically generate initial /outputs artifacts.

Creates:
- outputs/README.md
- outputs/roadmap.md
- outputs/bibliography.md
- outputs/coverage_matrix.md

Design goals: idempotent writes, stable ordering, no runtime timestamps.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


def _norm_lf(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")


def _write_if_changed(path: Path, text: str) -> bool:
    text = _norm_lf(text).rstrip("\n") + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == text:
        return False
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def _sha256(text: str) -> str:
    return hashlib.sha256(_norm_lf(text).encode("utf-8")).hexdigest()
def build_readme() -> str:
    return """# /outputs artifact rules & conventions

This directory is reserved for **generated artifacts** produced by pipeline runs and/or local tooling.
Artifacts must be **deterministic** and **diff-friendly** so that CI can reliably detect meaningful changes.

## Conventions

- **Encoding/line endings:** UTF-8, LF (`\n`), final newline required.
- **Determinism:** No timestamps, random IDs, environment-specific paths, or machine-dependent ordering.
- **Stable ordering:** Lists/tables sorted where applicable (e.g., alphabetically or by explicit numeric order).
- **Idempotence:** Re-running generators without input changes must not modify artifacts.
- **Naming:** Lowercase `snake_case.md` unless a stronger convention exists.
- **Structure:** Prefer Markdown with clear headings, tables for matrices, and short, fixed-width identifiers.
- **Change policy:** Update artifacts only via scripts under `/scripts/` (or the pipeline), not by hand.

## Required baseline artifacts

- `roadmap.md` — milestones and cycle plan for artifact evolution.
- `bibliography.md` — sources, links, and citation notes used by the project/agents.
- `coverage_matrix.md` — mapping of requirements to files/tests/CI checks.

## Determinism guarantee (self-check)

Each generator should be able to compute a hash of its rendered output. The expected property is:

- same inputs => same rendered Markdown => same SHA-256

(Generators may print hashes for auditing but must not embed them into artifacts.)
"""
def build_roadmap() -> str:
    return """# Roadmap

This roadmap is an evolving, deterministic snapshot of planned work and delivered artifacts.

## Milestones

1. **Stage 1 (bootstrap outputs)**  
   - Deliver `/outputs/README.md`, `/outputs/roadmap.md`, `/outputs/bibliography.md`, `/outputs/coverage_matrix.md`.
   - Establish conventions for determinism and update cadence.

2. **Stage 2 (CI/CD integration)**  
   - Add checks that verify generators are idempotent (no diff after re-run).
   - Add lint/format checks for Markdown artifacts.

3. **Stage 3 (coverage expansion)**  
   - Expand coverage matrix with additional requirements, tests, and ownership.
   - Track completion status per requirement.

## Cycles (record of intent)

- **Cycle 1:** Establish stable artifact structure and naming conventions.
- **Cycle 2:** Add validation hooks and CI assertions (hash/diff-based).
- **Cycle 3:** Increase requirement coverage and link to concrete checks.

## Deliverables

- Baseline artifacts under `/outputs/` (this file and siblings).
- A deterministic generator script under `/scripts/` used by CI and developers.
"""
def build_bibliography() -> str:
    return """# Bibliography

Curated sources, prompts, and internal references used by the project and its agents.
Entries are stable, human-readable, and may include internal identifiers.

## Internal agent notes (provided as inputs)

- **agent_1766538161484_b5yh91f** — Cycle 1 consistency review (divergence 0.97).  
  Notes: high-level alignment summary across branches.

- **agent_1766538470010_nvdr7ld** — Cycle 4 consistency review (divergence 0.96).  
  Notes: branches largely compatible; minor divergences.

- **agent_1766540049061_an5rb16** — Computational Plan (deterministic `/outputs/` artifacts).  
  Notes: emphasizes reproducible workflow and stable artifacts.

- **Consolidated insight** — Establish a reproducible workflow with coverage matrix and evaluation cadence.  
  Notes: prioritizes CI-verifiable determinism.

- **Introspection log** — `2025-12-24T01-29-38-707Z_scripts_run_pipeline_py_stage1_attempt1_prompt.txt`.  
  Notes: historical prompt snapshot referenced for traceability.

## External sources

None recorded yet. When adding external sources, use this format:

- **Title** — URL  
  Notes: why it is relevant; license/citation expectations.
"""
def build_coverage_matrix() -> str:
    return """# Coverage matrix

Maps requirements to artifacts, checks, and evidence.
Status values are intentionally simple and deterministic.

Legend: **Status** = planned | partial | done

| Requirement | Status | Evidence (files) | Checks (tests/CI) |
|---|---:|---|---|
| documentation | done | `outputs/README.md`, `outputs/roadmap.md`, `outputs/bibliography.md` | Generator produces deterministic Markdown; idempotent re-run (diff = 0) |
| ci cd | partial | `outputs/coverage_matrix.md` | Planned: CI job runs `python scripts/generate_outputs.py` and fails on diff |
"""
def main() -> int:
    changed = []
    artifacts = {
        "README.md": build_readme(),
        "roadmap.md": build_roadmap(),
        "bibliography.md": build_bibliography(),
        "coverage_matrix.md": build_coverage_matrix(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name in sorted(artifacts):
        path = OUT / name
        text = artifacts[name]
        if _write_if_changed(path, text):
            changed.append(str(path.relative_to(ROOT)))
    # Minimal, deterministic console output for CI logs:
    for name in sorted(artifacts):
        print(f"SHA256:{name}:{_sha256(artifacts[name])}")
    if changed:
        print("CHANGED:" + ",".join(changed))
    else:
        print("CHANGED:(none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
