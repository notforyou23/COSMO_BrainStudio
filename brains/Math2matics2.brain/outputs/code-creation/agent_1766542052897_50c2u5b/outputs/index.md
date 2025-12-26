# Outputs index

This directory is the canonical landing zone for promoted artifacts so automated audits can reliably find deliverables under `outputs/`.

`outputs/index.md` is designed to be **regenerated** by the artifact-promotion tooling (e.g., `tools/promote_artifacts.py`) to reflect the current contents of this folder, with stable Markdown links.
## Files

_No files are currently present in `outputs/` besides this index._
## Link conventions

- Links are relative (`./filename`) so they remain stable when the repository root changes.
- Only files directly under `outputs/` are indexed here (no recursive traversal).
