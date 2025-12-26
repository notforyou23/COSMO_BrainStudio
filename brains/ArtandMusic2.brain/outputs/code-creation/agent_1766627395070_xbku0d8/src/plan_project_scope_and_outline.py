from __future__ import annotations
from pathlib import Path
import hashlib
import re

BASE_DIR = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')
OUT_DIR = BASE_DIR / 'runtime' / 'outputs'
PATH_PLAN = OUT_DIR / 'plan_project_scope_and_outline.md'
PATH_OUTLINE = OUT_DIR / 'REPORT_OUTLINE.md'
PATH_DRAFT = OUT_DIR / 'DRAFT_REPORT_v0.md'

def _norm_newlines(s: str) -> str:
    return s.replace('\r\n', '\n').replace('\r', '\n')

def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _norm_newlines(text).strip() + '\n'
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8', newline='\n')
    tmp.replace(path)

def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9\s\-]+', '', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s or 'section'

def _sec_id(path_titles: list[str]) -> str:
    key = ' > '.join(path_titles).strip()
    h = hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]
    return f'sec-{h}-{_slug(path_titles[-1])[:32]}'

def _outline_tree():
    # Canonical outline: edit here only; all outputs are derived from this structure.
    return [
        ('Executive Summary', []),
        ('Introduction', [
            ('Background & problem framing', []),
            ('Audience, goals, and non-goals', []),
            ('Key terms and definitions', []),
        ]),
        ('Core Research Questions', [
            ('Measurement design as an equity lever', []),
            ('Validity, reliability, and unintended impacts', []),
            ('Governance and accountability', []),
        ]),
        ('Method & Evidence Plan', [
            ('Data sources and inclusion criteria', []),
            ('Analytic approach and evaluation rubric', []),
            ('Limitations and risk management', []),
        ]),
        ('Findings & Discussion', [
            ('Where bias enters the system', []),
            ('Equity and access implications', []),
            ('Tradeoffs and decision points', []),
        ]),
        ('Recommendations', [
            ('Principles and guardrails', []),
            ('Implementation roadmap', []),
            ('Monitoring and continuous improvement', []),
        ]),
        ('Project Plan (4-week agent schedule)', [
            ('Week 1: scope, questions, and evidence inventory', []),
            ('Week 2: analysis and synthesis', []),
            ('Week 3: draft narrative and review', []),
            ('Week 4: finalize, QA, and publish', []),
        ]),
        ('Appendices', [
            ('References', []),
            ('Glossary', []),
            ('Change log', []),
        ]),
    ]

def _flatten(tree, prefix=None):
    prefix = prefix or []
    out = []
    for title, children in tree:
        path = prefix + [title]
        sid = _sec_id(path)
        out.append({'title': title, 'path': path, 'id': sid, 'children': []})
        if children:
            out.extend(_flatten(children, path))
    return out

def _outline_fingerprint(secs) -> str:
    payload = '\n'.join(f"{s['id']}|{' > '.join(s['path'])}" for s in secs)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]

def _render_outline(secs, fp: str) -> str:
    lines = [
        '# REPORT_OUTLINE',
        '',
        f'- Outline fingerprint: `{fp}`',
        '',
        '## Sections',
    ]
    for s in secs:
        level = 2 + (len(s['path']) - 1)
        hdr = '#' * min(level, 6)
        lines.append(f"{hdr} {s['title']} {{#{s['id']}}}")
    lines.append('')
    return '\n'.join(lines)

def _render_draft_skeleton(secs, fp: str) -> str:
    lines = [
        '# DRAFT_REPORT_v0',
        '',
        f'- Outline fingerprint: `{fp}`',
        '- Status: section skeleton only (deterministic; fill content later).',
        '',
    ]
    for s in secs:
        level = 2 + (len(s['path']) - 1)
        hdr = '#' * min(level, 6)
        lines.extend([
            f"{hdr} {s['title']} {{#{s['id']}}}",
            '',
            '_Write this section._',
            '',
            '**Key points to cover:**',
            '- ( )',
            '',
            '**Notes / citations:**',
            '-',
            '',
        ])
    return '\n'.join(lines).rstrip() + '\n'

def _render_plan(secs, fp: str) -> str:
    # Explicitly maps the plan to the canonical outline via IDs and fingerprint.
    rq = [
        'How does measurement design act as a hidden equity lever (and risk)?',
        'Where can bias enter (data, instruments, evaluation, governance), and how do we detect it?',
        'What guardrails and accountability mechanisms reduce unintended harms?',
        'What tradeoffs must decision-makers explicitly choose (fairness vs. validity, access vs. rigor)?',
    ]
    lines = [
        '# plan_project_scope_and_outline',
        '',
        f'- Deterministic mapping fingerprint: `{fp}`',
        f'- Maps to: `{PATH_OUTLINE.name}` and `{PATH_DRAFT.name}`',
        '',
        '## Scope',
        '- Deliverable: a structured report with clear research questions, method plan, findings synthesis, and actionable recommendations.',
        '- Intended audience: stakeholders deciding how to define/measure performance in high-stakes contexts.',
        '- Non-goals: implement production systems; produce definitive causal estimates beyond available evidence.',
        '',
        '## Core research questions',
    ]
    lines += [f'- {q}' for q in rq]
    lines += [
        '',
        '## Deterministic outline mapping',
        'The following table is the canonical section list; IDs must match exactly across all generated files.',
        '',
        '| Section path | Section ID |',
        '|---|---|',
    ]
    for s in secs:
        lines.append(f"| {' > '.join(s['path'])} | `{s['id']}` |")
    lines += [
        '',
        '## 4-week execution schedule (agent-friendly)',
        '- Week 1: confirm scope, finalize questions, assemble evidence inventory, lock outline.',
        '- Week 2: analyze evidence, identify bias entry points, draft findings bullets per section.',
        '- Week 3: write full narrative, peer review for coherence and equity risks, revise.',
        '- Week 4: QA (citations, consistency, formatting), finalize recommendations, publish.',
        '',
    ]
    return '\n'.join(lines)

def _parse_ids(md: str) -> list[str]:
    return re.findall(r'\{#(sec-[a-f0-9]{10}-[a-z0-9\-]+)\}', md)

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    secs = _flatten(_outline_tree())
    fp = _outline_fingerprint(secs)

    outline = _render_outline(secs, fp)
    draft = _render_draft_skeleton(secs, fp)
    plan = _render_plan(secs, fp)

    _atomic_write(PATH_OUTLINE, outline)
    _atomic_write(PATH_DRAFT, draft)
    _atomic_write(PATH_PLAN, plan)

    # Deterministic mapping validation (IDs + fingerprint).
    expected = [s['id'] for s in secs]
    got_outline = _parse_ids(PATH_OUTLINE.read_text(encoding='utf-8'))
    got_draft = _parse_ids(PATH_DRAFT.read_text(encoding='utf-8'))
    if got_outline != expected or got_draft != expected:
        raise SystemExit('Deterministic mapping validation failed: section IDs mismatch.')

    for p in (PATH_OUTLINE, PATH_DRAFT, PATH_PLAN):
        txt = p.read_text(encoding='utf-8')
        if f'`{fp}`' not in txt:
            raise SystemExit(f'Deterministic mapping validation failed: fingerprint missing in {p.name}.')

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
