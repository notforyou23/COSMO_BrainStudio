"""Mathematics taxonomy for generating a coverage matrix.

This module is intentionally small and deterministic: it defines the set of
domains, subtopics, artifact types, and the default fields for each matrix cell.
Downstream tools should treat these as the single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping


STATUS_VALUES: List[str] = ["missing", "draft", "review", "final"]

ARTIFACT_TYPES: List[str] = [
    "concept_note",
    "worked_example",
    "exercise_set",
    "quiz",
    "proof_outline",
    "cheat_sheet",
    "glossary",
    "visualization",
    "implementation",
    "common_mistakes",
]


# Domains -> ordered subtopics (curated to be broadly useful and stable over time).
DOMAINS: Mapping[str, List[str]] = {
    "Arithmetic & Number Sense": [
        "integers_and_rationals",
        "fractions_and_decimals",
        "ratio_rate_percent",
        "estimation_and_rounding",
        "exponents_and_roots",
        "modular_arithmetic",
    ],
    "Algebra": [
        "expressions_and_equations",
        "inequalities",
        "functions_and_graphs",
        "polynomials",
        "rational_expressions",
        "systems_of_equations",
        "complex_numbers",
    ],
    "Geometry": [
        "euclidean_basics",
        "triangles_and_congruence",
        "similarity_and_trigonometry",
        "circles",
        "coordinate_geometry",
        "area_and_volume",
        "transformations",
    ],
    "Calculus": [
        "limits_and_continuity",
        "derivatives",
        "integrals",
        "series_and_sequences",
        "multivariable_calculus",
        "differential_equations",
    ],
    "Linear Algebra": [
        "vectors_and_spaces",
        "matrices_and_operations",
        "solving_linear_systems",
        "determinants",
        "eigenvalues_eigenvectors",
        "orthogonality_least_squares",
    ],
    "Discrete Mathematics": [
        "logic_and_proofs",
        "set_theory",
        "combinatorics",
        "graph_theory",
        "number_theory",
        "recurrences",
    ],
    "Probability & Statistics": [
        "probability_rules",
        "random_variables",
        "distributions",
        "expectation_variance",
        "sampling_and_estimation",
        "hypothesis_testing",
        "regression",
    ],
}


DEFAULT_STATUS: str = "missing"
DEFAULT_CROSS_LINKS: str = ""


@dataclass(frozen=True)
class CoverageCell:
    """A single coverage matrix cell for (domain, subtopic, artifact_type)."""

    domain: str
    subtopic: str
    artifact_type: str
    status: str = DEFAULT_STATUS
    cross_links: str = DEFAULT_CROSS_LINKS

    @property
    def cell_id(self) -> str:
        return f"{self.domain}::{self.subtopic}::{self.artifact_type}"


def iter_cells(
    domains: Mapping[str, List[str]] = DOMAINS,
    artifact_types: List[str] = ARTIFACT_TYPES,
) -> Iterable[CoverageCell]:
    """Yield all cells in deterministic order."""
    for domain in domains:
        for subtopic in domains[domain]:
            for artifact_type in artifact_types:
                yield CoverageCell(domain=domain, subtopic=subtopic, artifact_type=artifact_type)


def as_rows(
    domains: Mapping[str, List[str]] = DOMAINS,
    artifact_types: List[str] = ARTIFACT_TYPES,
) -> Iterable[Dict[str, str]]:
    """Yield machine-friendly dict rows suitable for CSV/markdown rendering."""
    for cell in iter_cells(domains=domains, artifact_types=artifact_types):
        yield {
            "domain": cell.domain,
            "subtopic": cell.subtopic,
            "artifact_type": cell.artifact_type,
            "status": cell.status,
            "cross_links": cell.cross_links,
            "cell_id": cell.cell_id,
        }
