from pathlib import Path
import json
import os
import tempfile
import time
from typing import Any, Dict, Optional, Union

PathLike = Union[str, os.PathLike]


def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def norm_path(path: PathLike, base: Optional[PathLike] = None) -> str:
    p = Path(path).expanduser()
    try:
        p = p.resolve()
    except Exception:
        p = Path(os.path.abspath(str(p)))
    if base is not None:
        b = Path(base).expanduser()
        try:
            b = b.resolve()
        except Exception:
            b = Path(os.path.abspath(str(b)))
        try:
            p = p.relative_to(b)
        except Exception:
            pass
    s = p.as_posix()
    return s[:-1] if s.endswith('/') and s != '/' else s


def dumps_deterministic(obj: Any) -> str:
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(',', ':'),
    )


def _atomic_write_text(dest: Path, text: str, encoding: str = 'utf-8') -> None:
    dest = Path(dest)
    ensure_dir(dest.parent)
    tmp_fd = None
    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=f'.{dest.name}.tmp.',
            dir=str(dest.parent),
            text=True,
        )
        with os.fdopen(tmp_fd, 'w', encoding=encoding, newline='\n') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        tmp_fd = None
        os.replace(tmp_path, dest)
        tmp_path = None
    finally:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except Exception:
                pass
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def atomic_write_json(dest: PathLike, data: Any) -> None:
    dest_p = Path(dest)
    text = dumps_deterministic(data) + '\n'
    _atomic_write_text(dest_p, text)


def atomic_write_md(dest: PathLike, markdown: str) -> None:
    dest_p = Path(dest)
    text = (markdown or '').rstrip('\n') + '\n'
    _atomic_write_text(dest_p, text)


def write_run_metadata(
    json_path: PathLike,
    md_path: PathLike,
    metadata: Dict[str, Any],
    title: str = 'QA Summary',
) -> None:
    atomic_write_json(json_path, metadata)
    lines = [f'# {title}', '']
    run = metadata.get('run', {})
    lines.append(f"- time_utc: {run.get('time_utc', '')}")
    lines.append(f"- git_sha: {run.get('git_sha', '')}")
    inputs = metadata.get('inputs', {})
    if inputs:
        lines.append('- inputs:')
        for k in sorted(inputs.keys()):
            v = inputs[k]
            lines.append(f'  - {k}: {v}')
    outputs = metadata.get('outputs', {})
    if outputs:
        lines.append('- outputs:')
        for k in sorted(outputs.keys()):
            v = outputs[k]
            lines.append(f'  - {k}: {v}')
    atomic_write_md(md_path, '\n'.join(lines))
