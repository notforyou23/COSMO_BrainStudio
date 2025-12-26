"""Core refactoring + modularization logic.

This module analyzes input source texts (primarily Python) and emits structured
"artifacts" that can be re-used by export helpers (e.g., written as modules).
The heuristics are intentionally lightweight and dependency-free.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
import ast
import hashlib
@dataclass(frozen=True)
class Artifact:
    """A reusable unit produced by analysis (module/function/class/etc.)."""
    name: str
    kind: str  # e.g. module, function, class, entrypoint, text
    content: str
    origin: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def stable_id(self) -> str:
        h = hashlib.sha256((self.kind + "\n" + self.name + "\n" + self.content).encode("utf-8")).hexdigest()
        return h[:16]


@dataclass
class RefactorResult:
    artifacts: List[Artifact]
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
def _language_for_path(path: str) -> str:
    p = path.lower()
    if p.endswith(".py"):
        return "python"
    if p.endswith(".md") or p.endswith(".markdown"):
        return "markdown"
    return "text"


def _slice(text: str, node: ast.AST) -> Optional[str]:
    try:
        return ast.get_source_segment(text, node)
    except Exception:
        return None
def _python_artifacts(text: str, origin: str) -> Tuple[List[Artifact], List[str]]:
    warnings: List[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [Artifact(name=origin, kind="text", content=text, origin=origin, metadata={"syntax_error": str(e)})], [f"{origin}: {e}"]

    lines = text.splitlines()
    imports: List[str] = []
    defs: List[Artifact] = []
    entrypoint: List[str] = []
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            seg = _slice(text, n) or ""
            if seg.strip():
                imports.append(seg.rstrip())
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            seg = _slice(text, n)
            if not seg:
                continue
            kind = "class" if isinstance(n, ast.ClassDef) else "function"
            defs.append(Artifact(name=n.name, kind=kind, content=seg.rstrip() + "\n", origin=origin))
        elif isinstance(n, ast.If):
            # capture common entrypoint pattern
            test = _slice(text, n.test) or ""
            if "__name__" in test and "__main__" in test:
                seg = _slice(text, n) or ""
                if seg.strip():
                    entrypoint.append(seg.rstrip())

    artifacts: List[Artifact] = []
    if imports:
        artifacts.append(Artifact(name="imports", kind="imports", content="\n".join(imports) + "\n", origin=origin))
    artifacts.extend(defs)
    if entrypoint:
        artifacts.append(Artifact(name="__main__", kind="entrypoint", content="\n\n".join(entrypoint) + "\n", origin=origin))

    # If nothing extracted, keep file as-is to avoid data loss
    if not artifacts:
        artifacts.append(Artifact(name=origin, kind="module", content=text if text.endswith("\n") else text + "\n", origin=origin))
    return artifacts, warnings
def analyze_sources(sources: Mapping[str, str]) -> RefactorResult:
    """Analyze path->text mapping and return structured reusable artifacts."""
    artifacts: List[Artifact] = []
    warnings: List[str] = []
    for path, text in sources.items():
        lang = _language_for_path(path)
        if lang == "python":
            a, w = _python_artifacts(text, origin=path)
            artifacts.extend(a)
            warnings.extend(w)
        else:
            artifacts.append(Artifact(name=path, kind=lang, content=text if text.endswith("\n") else text + "\n", origin=path))

    stats = {
        "sources": len(sources),
        "artifacts": len(artifacts),
        "kinds": {k: sum(1 for a in artifacts if a.kind == k) for k in sorted({a.kind for a in artifacts})},
    }
    return RefactorResult(artifacts=artifacts, warnings=warnings, stats=stats)
def propose_modules(result: RefactorResult) -> Dict[str, List[Artifact]]:
    """Group artifacts into suggested module files.

    Heuristic:
    - imports are grouped into a per-origin pseudo-module
    - functions with helper-ish names go to utils.py
    - other defs go to a module derived from origin file name
    - non-python/text artifacts keep their origin-derived names
    """
    grouped: Dict[str, List[Artifact]] = {}
    for a in result.artifacts:
        if a.kind in {"markdown", "text"}:
            mod = a.origin or a.name
        elif a.kind == "imports":
            base = Path(a.origin).stem if a.origin else "module"
            mod = f"{base}.py"
        elif a.kind in {"function", "class", "entrypoint"}:
            nm = a.name.lower()
            if any(t in nm for t in ("util", "helper", "parse_", "read_", "write_", "slug", "normalize")):
                mod = "utils.py"
            else:
                base = Path(a.origin).stem if a.origin else "module"
                mod = f"{base}.py"
        else:  # module/unknown
            mod = Path(a.origin).name if a.origin else "module.py"
        grouped.setdefault(mod, []).append(a)

    # stable ordering: imports first, then classes, then functions, then entrypoint/text
    order = {"imports": 0, "class": 1, "function": 2, "entrypoint": 3, "module": 4, "markdown": 5, "text": 6}
    for mod, items in list(grouped.items()):
        grouped[mod] = sorted(items, key=lambda x: (order.get(x.kind, 99), x.name))
    return grouped
def refactor_and_modularize(sources: Mapping[str, str]) -> Tuple[RefactorResult, Dict[str, str]]:
    """End-to-end helper returning analysis plus rendered module texts."""
    result = analyze_sources(sources)
    modules: Dict[str, str] = {}
    for mod, items in propose_modules(result).items():
        if mod.endswith(".py"):
            body = "\n\n".join(i.content.rstrip("\n") for i in items).rstrip() + "\n"
        else:
            body = "\n".join(i.content.rstrip("\n") for i in items).rstrip() + "\n"
        modules[mod] = body
    return result, modules
