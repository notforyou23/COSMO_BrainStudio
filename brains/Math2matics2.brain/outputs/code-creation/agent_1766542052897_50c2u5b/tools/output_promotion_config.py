"""Default configuration for the artifact promotion tool.

The audit expects generated documents under the canonical ``outputs/`` directory.
Agents often write artifacts into agent-specific directories (e.g. ``agent_*``),
so the promotion CLI discovers those artifacts, copies them into ``outputs/``,
and regenerates ``outputs/index.md`` linking to everything promoted.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Sequence
@dataclass(frozen=True)
class PromotionConfig:
    # Discovery: where to look for agent outputs relative to project root.
    agent_dir_globs: Sequence[str]
    # Discovery: which files inside those dirs are considered artifacts.
    allow_filenames: Sequence[str]
    allow_extensions: Sequence[str]
    deny_globs: Sequence[str]

    # Canonical destination.
    outputs_dirname: str
    index_filename: str

    # Destination naming policy.
    # If True: prefix promoted filenames with the agent directory name to avoid collisions.
    prefix_with_agent_dir: bool
    # If True: preserve relative subdirectories under agent dir (sanitized) in outputs/.
    preserve_subdirs: bool

    # Index formatting.
    index_title: str
    index_preamble: str

    def outputs_dir(self, project_root: Path) -> Path:
        return project_root / self.outputs_dirname

    def index_path(self, project_root: Path) -> Path:
        return self.outputs_dir(project_root) / self.index_filename
DEFAULT_CONFIG = PromotionConfig(
    agent_dir_globs=(
        "agent_*",
        "**/agent_*",
        "**/agents/agent_*",
        "**/.agents/agent_*",
    ),
    # Common artifact names used by agent scaffolds.
    allow_filenames=(
        "README.md",
        "readme.md",
        "first_artifact.md",
        "research_template.md",
        "final.md",
        "report.md",
        "summary.md",
        "index.md",
    ),
    allow_extensions=(
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".csv",
    ),
    # Avoid copying bulky/irrelevant content into outputs/ by default.
    deny_globs=(
        "**/__pycache__/**",
        "**/.git/**",
        "**/.venv/**",
        "**/venv/**",
        "**/node_modules/**",
        "**/.pytest_cache/**",
        "**/.mypy_cache/**",
        "**/.ruff_cache/**",
        "**/.DS_Store",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        "**/*.so",
        "**/*.dylib",
        "**/*.exe",
    ),
    outputs_dirname="outputs",
    index_filename="index.md",
    prefix_with_agent_dir=True,
    preserve_subdirs=False,
    index_title="Outputs",
    index_preamble=(
        "This folder contains promoted artifacts consolidated from agent-specific "
        "directories. The promotion tool regenerates this index.\n"
    ),
)
_SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_segment(text: str) -> str:
    \"\"\"Sanitize a path segment for use in a filename.\"\"\"
    cleaned = _SAFE_CHARS_RE.sub("-", text.strip())
    cleaned = cleaned.strip("-.")
    return cleaned or "artifact"


def choose_destination_name(
    *,
    src_path: Path,
    agent_dir: Path,
    config: PromotionConfig = DEFAULT_CONFIG,
) -> str:
    \"\"\"Return the destination filename for a discovered artifact.

    The CLI may still apply collision resolution (e.g., appending -2, -3).
    \"\"\"
    name = src_path.name
    if config.prefix_with_agent_dir:
        prefix = sanitize_segment(agent_dir.name)
        name = f\"{prefix}__{name}\"

    if config.preserve_subdirs:
        try:
            rel = src_path.relative_to(agent_dir).parent
        except ValueError:
            rel = Path()
        if rel != Path():
            safe_parts = [sanitize_segment(p) for p in rel.parts]
            name = \"__\".join(safe_parts + [name])
    return name
def should_consider_file(
    *,
    src_path: Path,
    config: PromotionConfig = DEFAULT_CONFIG,
) -> bool:
    \"\"\"Fast allow/deny check used during discovery.\"\"\"
    if not src_path.is_file():
        return False

    s = src_path.as_posix()
    for pat in config.deny_globs:
        # Path.match anchors to start; emulate glob-anywhere via '**/' patterns in config.
        if src_path.match(pat) or (pat.startswith("**/") and Path(s).match(pat)):
            return False

    if src_path.name in config.allow_filenames:
        return True
    return src_path.suffix.lower() in {e.lower() for e in config.allow_extensions}
def render_index_markdown(
    *,
    entries: Iterable[tuple[str, str]],
    config: PromotionConfig = DEFAULT_CONFIG,
) -> str:
    \"\"\"Render outputs/index.md content.

    entries: iterable of (display_name, relative_link) pairs.
    \"\"\"
    lines: list[str] = [f\"# {config.index_title}\", \"\", config.index_preamble.strip(), \"\"]
    items = sorted(entries, key=lambda x: (x[0].lower(), x[1]))
    if not items:
        lines.append(\"(No promoted outputs yet.)\")
        lines.append(\"\")
        return \"\\n\".join(lines).rstrip() + \"\\n\"

    for display, link in items:
        lines.append(f\"- [{display}]({link})\")
    lines.append(\"\")
    return \"\\n\".join(lines)
__all__ = [
    "PromotionConfig",
    "DEFAULT_CONFIG",
    "sanitize_segment",
    "choose_destination_name",
    "should_consider_file",
    "render_index_markdown",
]
