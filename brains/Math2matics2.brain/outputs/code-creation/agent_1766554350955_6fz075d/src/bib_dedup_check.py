#!/usr/bin/env python3
import argparse, re, sys, unicodedata
from pathlib import Path
from difflib import SequenceMatcher
def _strip_outer(s: str) -> str:
    s = s.strip()
    if (s.startswith('{') and s.endswith('}')) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1].strip()
    return s
def _norm_text(s: str) -> str:
    s = _strip_outer(s)
    s = s.replace('\\&', '&').replace('\\%', '%')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'\s+', ' ', s).strip()
    return s
def norm_key(k: str) -> str:
    k = _norm_text(k).lower()
    k = re.sub(r'[^a-z0-9]+', '_', k)
    k = re.sub(r'_+', '_', k).strip('_')
    return k or 'ref'
def title_fingerprint(title: str) -> str:
    t = _norm_text(title).lower()
    t = re.sub(r'[{}`"\'“”‘’]', '', t)
    t = re.sub(r'[^a-z0-9 ]+', ' ', t)
    toks = [w for w in t.split() if len(w) > 2 and w not in {'the','and','for','with','from','into','using','via','over'}]
    return ' '.join(toks)
def parse_bibtex(text: str):
    i, n = 0, len(text)
    entries = []
    while True:
        m = re.search(r'@([A-Za-z]+)\s*([({])', text[i:])
        if not m: break
        etype = m.group(1).lower()
        opench = m.group(2)
        closech = ')' if opench == '(' else '}'
        j = i + m.end()
        # scan to matching close for the whole entry
        depth, in_str, esc = 1, None, False
        k = j
        while k < n and depth > 0:
            ch = text[k]
            if in_str:
                if esc: esc = False
                elif ch == '\\': esc = True
                elif ch == in_str: in_str = None
            else:
                if ch in ('"', "'"): in_str = ch
                elif ch == opench: depth += 1
                elif ch == closech: depth -= 1
            k += 1
        body = text[j:k-1].strip()
        # key is up to first comma at top level
        key, rest = body, ''
        depth2, in_str2, esc2 = 0, None, False
        for idx, ch in enumerate(body):
            if in_str2:
                if esc2: esc2 = False
                elif ch == '\\': esc2 = True
                elif ch == in_str2: in_str2 = None
            else:
                if ch in ('"', "'"): in_str2 = ch
                elif ch == '{': depth2 += 1
                elif ch == '}': depth2 = max(0, depth2-1)
                elif ch == ',' and depth2 == 0:
                    key = body[:idx].strip()
                    rest = body[idx+1:].strip()
                    break
        fields = {}
        if rest:
            # parse field=value pairs at top level separated by commas
            parts = []
            buf = []
            depth3, in_str3, esc3 = 0, None, False
            for ch in rest:
                if in_str3:
                    buf.append(ch)
                    if esc3: esc3 = False
                    elif ch == '\\': esc3 = True
                    elif ch == in_str3: in_str3 = None
                    continue
                if ch in ('"', "'"):
                    in_str3 = ch; buf.append(ch); continue
                if ch == '{': depth3 += 1
                elif ch == '}': depth3 = max(0, depth3-1)
                if ch == ',' and depth3 == 0:
                    part = ''.join(buf).strip()
                    if part: parts.append(part)
                    buf = []
                else:
                    buf.append(ch)
            tail = ''.join(buf).strip()
            if tail: parts.append(tail)
            for p in parts:
                if '=' not in p: continue
                fn, fv = p.split('=', 1)
                fn = fn.strip().lower()
                fv = fv.strip()
                fields[fn] = fv
        entries.append({'type': etype, 'key': key.strip(), 'fields': fields})
        i = k
    return entries
def canonicalize_entry(e):
    f = {k.lower().strip(): v.strip() for k, v in e['fields'].items() if k and v}
    doi = _norm_text(f.get('doi',''))
    doi = doi.lower().strip()
    if doi.startswith('http'): doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi).strip()
    year = re.findall(r'\d{4}', _norm_text(f.get('year','') or f.get('date','')))
    year = year[0] if year else ''
    title = _norm_text(f.get('title',''))
    auth = _norm_text(f.get('author',''))
    fp = title_fingerprint(title)
    url = _norm_text(f.get('url',''))
    return {
        'type': e['type'],
        'orig_key': e['key'],
        'key': norm_key(e['key']),
        'fields': f,
        'doi': doi,
        'year': year,
        'title': title,
        'author': auth,
        'title_fp': fp,
        'url': url,
    }
def sim(a: str, b: str) -> float:
    if not a or not b: return 0.0
    return SequenceMatcher(None, a, b).ratio()
def find_duplicates(items, min_score=0.88):
    pairs = []
    by_doi = {}
    for it in items:
        if it['doi']:
            by_doi.setdefault(it['doi'], []).append(it)
    for doi, grp in by_doi.items():
        if len(grp) > 1:
            for i in range(len(grp)):
                for j in range(i+1, len(grp)):
                    pairs.append((grp[i], grp[j], 1.0, f"same DOI: {doi}"))
    # title+year similarity (skip same DOI already flagged)
    seen = {(a['orig_key'], b['orig_key']) for a,b,_,_ in pairs} | {(b['orig_key'], a['orig_key']) for a,b,_,_ in pairs}
    n = len(items)
    for i in range(n):
        for j in range(i+1, n):
            a, b = items[i], items[j]
            if (a['orig_key'], b['orig_key']) in seen: continue
            if a['year'] and b['year'] and a['year'] != b['year']: continue
            s1 = sim(a['title_fp'], b['title_fp'])
            s2 = sim(_norm_text(a['author']).lower(), _norm_text(b['author']).lower())
            score = 0.75*s1 + 0.25*s2
            if score >= min_score and (a['title_fp'] and b['title_fp']):
                why = f"title/author similarity {score:.2f}" + (f", year={a['year']}" if a['year'] else "")
                pairs.append((a, b, score, why))
    pairs.sort(key=lambda t: (-t[2], t[0]['orig_key'], t[1]['orig_key']))
    return pairs
def checklist(items, dups):
    lines = []
    # key collisions after normalization
    by_key = {}
    for it in items:
        by_key.setdefault(it['key'], []).append(it)
    collisions = {k:v for k,v in by_key.items() if len(v) > 1}
    # missing core fields
    missing = []
    for it in items:
        f = it['fields']
        need = []
        if 'title' not in f: need.append('title')
        if 'year' not in f and 'date' not in f: need.append('year/date')
        if 'author' not in f and 'editor' not in f: need.append('author/editor')
        if need: missing.append((it, need))
    lines.append('BIB DEDUP/CHECK v1')
    lines.append(f'Entries parsed: {len(items)}')
    lines.append('')
    lines.append('1) Likely duplicates to review')
    if not dups:
        lines.append('  - none detected')
    else:
        for a,b,score,why in dups[:50]:
            lines.append(f"  - {a['orig_key']}  <->  {b['orig_key']}  [{why}]")
    lines.append('')
    lines.append('2) Normalized-key collisions to resolve')
    if not collisions:
        lines.append('  - none')
    else:
        for k, grp in sorted(collisions.items()):
            lines.append(f"  - {k}: " + ', '.join(g['orig_key'] for g in grp))
    lines.append('')
    lines.append('3) Missing core fields (title, year/date, author/editor)')
    if not missing:
        lines.append('  - none')
    else:
        for it, need in missing[:80]:
            lines.append(f"  - {it['orig_key']}: missing {', '.join(need)}")
    lines.append('')
    lines.append('4) Quick manual checklist (v1)')
    lines.append('  - If duplicate: keep the most complete record; merge DOI/URL, fix title casing.')
    lines.append('  - Ensure DOI is bare (no https://doi.org/ prefix) and lowercase.')
    lines.append('  - Ensure year is 4 digits (or date=YYYY-MM-DD).')
    lines.append('  - Verify author list uses "Last, First and Last, First".')
    return '\n'.join(lines) + '\n'
def main(argv=None):
    ap = argparse.ArgumentParser(description='Parse references.bib, normalize keys/fields, detect likely duplicates, and print a v1 checklist report.')
    ap.add_argument('--bib', default=str(Path('outputs')/'references.bib'), help='Path to .bib file (default: outputs/references.bib)')
    ap.add_argument('--min-score', type=float, default=0.88, help='Duplicate threshold for title/author similarity (default: 0.88)')
    args = ap.parse_args(argv)
    bib_path = Path(args.bib)
    if not bib_path.exists():
        print(f'ERROR: bib file not found: {bib_path}', file=sys.stderr)
        return 2
    text = bib_path.read_text(encoding='utf-8', errors='replace')
    raw = parse_bibtex(text)
    items = [canonicalize_entry(e) for e in raw]
    dups = find_duplicates(items, min_score=args.min_score)
    sys.stdout.write(checklist(items, dups))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
