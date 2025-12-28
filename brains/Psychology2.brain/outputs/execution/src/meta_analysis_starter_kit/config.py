"""Central configuration for the meta-analysis starter kit.

This module defines canonical output locations, default CSV templates, and
shared plotting/table settings used by the starter kit utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


def _root_dir() -> Path:
    # Repository/runtime root (local execution working directory).
    return Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution').resolve()


ROOT_DIR: Path = _root_dir()
OUTPUTS_DIR: Path = ROOT_DIR / "outputs"
PROJECT_DIR: Path = OUTPUTS_DIR / "meta_analysis_starter_kit"

TEMPLATES_DIR: Path = PROJECT_DIR
EXTRACTION_TEMPLATE_PATH: Path = TEMPLATES_DIR / "extraction_template.csv"
SCREENING_LOG_PATH: Path = TEMPLATES_DIR / "screening_log.csv"

RUNS_DIR: Path = PROJECT_DIR / "runs"
FIGURES_DIR: Path = PROJECT_DIR / "figures"
TABLES_DIR: Path = PROJECT_DIR / "tables"


DEFAULT_EXTRACTION_COLUMNS: List[str] = [
    "study_id",
    "citation",
    "year",
    "design",
    "population",
    "intervention",
    "comparator",
    "outcome",
    "effect_type",      # e.g., RR, OR, SMD, MD; placeholder analysis expects log scale if RR/OR
    "effect",           # numeric effect (log scale if RR/OR)
    "se",               # standard error of effect
    "ci_lower",         # optional
    "ci_upper",         # optional
    "n_treat",          # optional
    "n_control",        # optional
    "notes",
    "include",          # 1/0 include in meta-analysis
]

DEFAULT_SCREENING_LOG_COLUMNS: List[str] = [
    "record_id",
    "citation",
    "source",
    "stage",            # title_abstract / full_text
    "decision",         # include / exclude / maybe
    "reason",           # exclusion reason
    "reviewer",
    "date",
    "notes",
]


@dataclass(frozen=True)
class TableSettings:
    float_format: str = "{:.3f}"
    summary_filename: str = "summary_table.csv"
    columns: Tuple[str, ...] = (
        "study_id",
        "effect_type",
        "effect",
        "se",
        "weight",
        "ci_lower",
        "ci_upper",
    )


@dataclass(frozen=True)
class ForestPlotSettings:
    filename: str = "forest_plot.png"
    dpi: int = 200
    figsize: Tuple[float, float] = (7.5, 5.0)
    point_size: float = 35.0
    line_width: float = 1.2
    alpha: float = 0.9
    title: str = "Forest plot (placeholder pooled estimate)"
    xlabel: str = "Effect (study estimate with 95% CI)"
    show_pooled: bool = True
    xscale: str = "linear"  # "linear" or "log" (caller may override based on effect_type)


TABLE_SETTINGS = TableSettings()
FOREST_PLOT_SETTINGS = ForestPlotSettings()


def ensure_project_dirs() -> Dict[str, Path]:
    """Create expected project directories (idempotent) and return them."""
    dirs = {
        "outputs": OUTPUTS_DIR,
        "project": PROJECT_DIR,
        "runs": RUNS_DIR,
        "figures": FIGURES_DIR,
        "tables": TABLES_DIR,
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    return dirs


def default_paths() -> Dict[str, Path]:
    """Return commonly used paths for templates and outputs."""
    return {
        "extraction_template": EXTRACTION_TEMPLATE_PATH,
        "screening_log": SCREENING_LOG_PATH,
        "runs_dir": RUNS_DIR,
        "figures_dir": FIGURES_DIR,
        "tables_dir": TABLES_DIR,
        "summary_table": TABLES_DIR / TABLE_SETTINGS.summary_filename,
        "forest_plot": FIGURES_DIR / FOREST_PLOT_SETTINGS.filename,
    }
