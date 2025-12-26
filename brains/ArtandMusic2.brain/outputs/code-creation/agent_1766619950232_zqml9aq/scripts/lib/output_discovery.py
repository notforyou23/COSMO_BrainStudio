from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import os, re, hashlib
from typing import Iterable, Optional, List, Dict, Any, Tuple

SKIP_DIRS = {'.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'node_modules', '.venv', 'venv', 'dist', 'build'}
ROOT_MARKERS = (
    'code-creation', 'document-creation', 'data-creation', 'image-creation',
    'agent', 'agents', 'agent_outputs', 'outputs', 'runtime'
)

EXT_CLASS = {
    'source': {'.py', '.js', '.ts', '.java', '.c', '.cc', '.cpp', '.h', '.hpp', '.rs', '.go', '.rb', '.php', '.cs', '.swift', '.kt', '.m', '.mm'},
    'document': {'.md', '.txt', '.rst', '.pdf', '.docx', '.pptx', '.xlsx', '.html', '.htm'},
    'data': {'.json', '.jsonl', '.csv', '.tsv', '.yaml', '.yml', '.toml', '.ini', '.xml', '.parquet', '.feather'},
    'image': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff', '.svg', '.webp'},
    'audio': {'.wav', '.mp3', '.m4a', '.flac', '.ogg'},
    'video': {'.mp4', '.mov', '.mkv', '.avi', '.webm'},
}

_AGENT_RE = re.compile(r'(agent(?:[_-][\w\d]+)?)', re.IGNORECASE)
_AGENT_STAMP_RE = re.compile(r'agent_\d+(?:_[\w\d]+)?', re.IGNORECASE)
_TS_RE = re.compile(r'\d{4}[-_]?\d{2}[-_]?\d{2}T\d{2}[-_]?\d{2}[-_]?\d{2}')

@dataclass(frozen=True)
class OutputRecord:
    path: str
    relpath: str
    category: str
    root_hint: str
    agent: Optional[str]
    size: int
    mtime: float
    sha1_8: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
def _classify(p: Path) -> str:
    ext = p.suffix.lower()
    for k, exts in EXT_CLASS.items():
        if ext in exts:
            return k
    return 'other'

def _sha1_8(p: Path, max_bytes: int = 1024 * 1024) -> str:
    h = hashlib.sha1()
    try:
        with p.open('rb') as f:
            h.update(f.read(max_bytes))
        return h.hexdigest()[:8]
    except Exception:
        return '00000000'

def _agent_from_parts(parts: Tuple[str, ...]) -> Optional[str]:
    for part in parts:
        m = _AGENT_STAMP_RE.search(part)
        if m:
            return m.group(0)
    joined = '/'.join(parts)
    m = _AGENT_RE.search(joined)
    return m.group(1) if m else None

def _root_hint(parts: Tuple[str, ...]) -> str:
    for part in parts:
        pl = part.lower()
        if pl in ('code-creation', 'document-creation', 'data-creation', 'image-creation'):
            return pl
    # fall back to common buckets
    for part in parts:
        pl = part.lower()
        if pl in ('runtime', 'outputs', 'agent_outputs'):
            return pl
    return 'unknown'

def _looks_like_agent_output(path_parts: Tuple[str, ...]) -> bool:
    low = [p.lower() for p in path_parts]
    if any(p in ('code-creation', 'document-creation', 'data-creation', 'image-creation') for p in low):
        return True
    if any(_AGENT_STAMP_RE.search(p) for p in path_parts):
        return True
    # heuristic: outputs folder nested under agent-ish path
    if 'outputs' in low or 'runtime' in low:
        joined = '/'.join(low)
        return ('agent' in joined) or ('creation' in joined)
    return False
def discover_outputs(repo_root: Path, *, include_hidden: bool = False, max_file_size: int = 200 * 1024 * 1024) -> List[Dict[str, Any]]:
    """Scan repo_root for likely agent-generated deliverables and return structured records.
    Only files under agent-stamped or known output roots are returned.
    """
    repo_root = Path(repo_root).resolve()
    out: List[OutputRecord] = []
    for root, dirs, files in os.walk(repo_root):
        root_p = Path(root)
        # prune
        pruned = []
        for d in list(dirs):
            if d in SKIP_DIRS:
                pruned.append(d); continue
            if not include_hidden and d.startswith('.'):
                pruned.append(d); continue
        for d in pruned:
            dirs.remove(d)

        rel_root = root_p.relative_to(repo_root)
        parts = rel_root.parts
        if parts and (not include_hidden) and any(p.startswith('.') for p in parts):
            continue
        if parts and not _looks_like_agent_output(parts):
            # Still traverse; but only record files when they look like outputs.
            pass

        for fn in files:
            if (not include_hidden) and fn.startswith('.'):
                continue
            p = root_p / fn
            try:
                st = p.stat()
            except OSError:
                continue
            if not p.is_file():
                continue
            if st.st_size > max_file_size:
                continue
            rel = p.relative_to(repo_root)
            rel_parts = rel.parts
            if not _looks_like_agent_output(rel_parts):
                continue
            rec = OutputRecord(
                path=str(p),
                relpath=str(rel).replace('\\', '/'),
                category=_classify(p),
                root_hint=_root_hint(rel_parts),
                agent=_agent_from_parts(rel_parts),
                size=int(st.st_size),
                mtime=float(st.st_mtime),
                sha1_8=_sha1_8(p),
            )
            out.append(rec)
    out.sort(key=lambda r: (r.root_hint, r.agent or '', r.relpath))
    return [r.to_dict() for r in out]

def discover_outputs_from_cwd(*, include_hidden: bool = False) -> List[Dict[str, Any]]:
    return discover_outputs(Path.cwd(), include_hidden=include_hidden)
