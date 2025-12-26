# refactor-modularize

A small Python CLI/library for **refactoring and modularizing reusable artifacts** (e.g., repeated README sections, duplicated configuration snippets, or shared prompt templates) across a set of input files. It loads artifacts, normalizes them, detects repeated fragments, and produces **deduplicated, modular outputs** suitable for reuse/export.

## Features

- Load multiple artifact files (Markdown/text/TOML/etc.) with metadata.
- Normalize content (line endings, trimming, lightweight canonicalization).
- Detect reusable fragments (exact/near-duplicate blocks) and centralize them.
- Export rewritten artifacts and a small “module” bundle of shared fragments.
- Usable as a library (`refactor_modularize.*`) or via CLI (`refactor-modularize`).

## Installation

### From source (recommended in this repo)

```bash
python -m venv .venv
# macOS/Linux:
. .venv/bin/activate
# Windows:
# .venv\Scripts\activate

python -m pip install -U pip
pip install -e .
```

### Verify

```bash
refactor-modularize --help
```
## Quickstart (CLI)

Refactor a set of artifacts and write outputs to a directory:

```bash
refactor-modularize \
  analyze /path/to/artifacts \
  --include "**/*.md" "**/*.txt" "**/*.toml" \
  --out out/
```

Export modularized fragments (and rewritten artifacts) to a bundle:

```bash
refactor-modularize \
  export /path/to/artifacts \
  --out out/ \
  --bundle out/bundle/
```

If your inputs are specific files (instead of a directory), pass them directly:

```bash
refactor-modularize analyze README.md pyproject.toml prompts/*.txt --out out/
```
## Typical workflow

1. **Analyze**: scan inputs, compute normalized forms, find repeated blocks.
2. **Refactor**: rewrite artifacts to reference shared fragments.
3. **Export**: write:
   - rewritten artifacts (same filenames by default, under `--out`)
   - shared fragment modules (under `--bundle`, if provided)
   - a machine-readable summary (JSON) describing what changed

## Configuration

The CLI is designed to be “flags-first”. Common options (names may vary slightly by command):

- `--include PATTERN...`: glob patterns to include.
- `--exclude PATTERN...`: glob patterns to ignore.
- `--out PATH`: output directory for rewritten artifacts and reports.
- `--bundle PATH`: directory for extracted shared fragments/modules.
- `--min-lines N`: minimum block size (in lines) to consider reusable.
- `--min-occurrences N`: require N repeats before extracting a fragment.
- `--format {md,text}`: output style for extracted modules (when applicable).

Run `refactor-modularize <command> --help` for the definitive list.

## Library usage

Use the package programmatically when you want tighter integration:

```python
from refactor_modularize.artifacts import load_artifacts
from refactor_modularize.refactor import RefactorEngine

artifacts = load_artifacts(["README.md", "pyproject.toml"])
engine = RefactorEngine(min_lines=4, min_occurrences=2)

result = engine.run(artifacts)

# result.fragments: extracted reusable blocks
# result.rewrites: per-file rewritten text
```

Write outputs:

```python
from pathlib import Path

out = Path("out")
out.mkdir(exist_ok=True)

for rewrite in result.rewrites:
    (out / rewrite.relpath).write_text(rewrite.text, encoding="utf-8")
```
## Examples

### Example: deduplicate repeated README sections

Input: multiple `README.md`-like files contain the same “Installation” section.

Command:

```bash
refactor-modularize export docs/ --include "**/*.md" --min-lines 6 --min-occurrences 2 --out out/ --bundle out/bundle/
```

Output:
- `out/docs/...` rewritten to reference a shared fragment (or replaced with a canonical copy)
- `out/bundle/fragments/installation.md` (name depends on the engine’s labeling)

### Example: unify prompt templates

Input: repeated prompt blocks across `*.txt` files.

```bash
refactor-modularize analyze prompts/ --include "**/*.txt" --min-lines 5 --min-occurrences 3 --out out/
```

Review `out/report.json` to see:
- which blocks were considered duplicates
- where they were found
- proposed module names/identifiers

## Output layout (convention)

When `--out out/` is used, the tool typically writes:
- `out/report.json` – summary of detected fragments and rewrites
- `out/<original tree>/...` – rewritten copies of the input artifacts
- `out/bundle/` – extracted fragments/modules (when `--bundle` is set)

## Notes

- The tool favors **safe, minimal rewrites**: it only extracts blocks that meet the configured thresholds.
- Artifact parsing is intentionally lightweight; it treats most inputs as text and focuses on block-level reuse.

## Development

```bash
pip install -e ".[dev]"
python -m pytest
```

## License

See repository license (if provided).
