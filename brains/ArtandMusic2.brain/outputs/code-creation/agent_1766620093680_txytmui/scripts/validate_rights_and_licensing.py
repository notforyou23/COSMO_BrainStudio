import csv
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

REQUIRED_COLS = ["URL", "license type", "rights holder", "permission status", "allowed uses"]

URL_RE = re.compile(r"https?://[^\s<>()\"']+")

def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    url = url.split("#", 1)[0].strip()
    while url and url[-1] in ".,;:!?)\]}>\"'":
        url = url[:-1]
    while url and url[0] in "(\[<{\"'":
        url = url[1:]
    try:
        parts = urlsplit(url)
    except Exception:
        return url
    scheme = (parts.scheme or "").lower()
    netloc = (parts.netloc or "").lower()
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    path = parts.path or ""
    query = parts.query or ""
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urlunsplit((scheme, netloc, path, query, ""))

def is_external_url(url: str) -> bool:
    u = normalize_url(url)
    if not u.startswith(("http://", "https://")):
        return False
    parts = urlsplit(u)
    host = (parts.hostname or "").lower()
    if host in {"localhost"} or host.startswith("127.") or host.startswith("0.0.0.0"):
        return False
    return True

def find_case_study_files(repo_root: Path):
    candidates = []
    for rel in ["case_studies", "case-studies", "case_study", "docs", "outputs"]:
        p = repo_root / rel
        if p.exists() and p.is_dir():
            candidates.append(p)
    if not candidates:
        candidates = [repo_root]
    exts = {".md", ".markdown", ".txt", ".json", ".yml", ".yaml"}
    files = []
    for root in candidates:
        for fp in root.rglob("*"):
            if fp.is_file() and fp.suffix.lower() in exts and "RIGHTS_LOG" not in fp.name:
                files.append(fp)
    return files

def extract_urls_from_text(text: str):
    return [m.group(0) for m in URL_RE.finditer(text or "")]

def load_rights_log(csv_path: Path):
    if not csv_path.exists():
        return None, f"Missing required rights log: {csv_path}"
    rows = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return None, f"Empty rights log header: {csv_path}"
        field_map = {fn.strip().lower(): fn for fn in reader.fieldnames if fn}
        missing = [c for c in REQUIRED_COLS if c.lower() not in field_map]
        if missing:
            return None, f"Rights log missing required columns: {missing}"
        for r in reader:
            rows.append(r)
    by_url = {}
    for r in rows:
        raw_url = (r.get(field_map["url"]) or "").strip()
        nurl = normalize_url(raw_url)
        if not nurl:
            continue
        by_url.setdefault(nurl, []).append(r)
    return (by_url, field_map), None

def validate(repo_root: Path) -> int:
    outputs_dir = repo_root / "outputs"
    checklist = outputs_dir / "RIGHTS_AND_LICENSING_CHECKLIST.md"
    rights_csv = outputs_dir / "RIGHTS_LOG.csv"

    errors = []
    if not checklist.exists():
        errors.append(f"Missing checklist: {checklist}")
    rights_data, err = load_rights_log(rights_csv)
    if err:
        errors.append(err)
        print("\n".join(errors), file=sys.stderr)
        return 2
    (rights_by_url, field_map) = rights_data

    files = find_case_study_files(repo_root)
    exemplar_urls = set()
    for fp in files:
        try:
            txt = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                txt = fp.read_text(encoding="latin-1")
            except Exception:
                continue
        for u in extract_urls_from_text(txt):
            if is_external_url(u):
                exemplar_urls.add(normalize_url(u))

    missing = []
    incomplete = []
    for u in sorted(exemplar_urls):
        rows = rights_by_url.get(u) or []
        if not rows:
            missing.append(u)
            continue
        ok = False
        for r in rows:
            def get(col):
                return (r.get(field_map[col.lower()]) or "").strip()
            if all(get(c) for c in REQUIRED_COLS):
                ok = True
                break
        if not ok:
            incomplete.append(u)

    if missing or incomplete or errors:
        if errors:
            print("\n".join(errors), file=sys.stderr)
        if missing:
            print(f"Missing RIGHTS_LOG entries for {len(missing)} exemplar URL(s):", file=sys.stderr)
            for u in missing[:200]:
                print(f"- {u}", file=sys.stderr)
            if len(missing) > 200:
                print(f"... ({len(missing)-200} more)", file=sys.stderr)
        if incomplete:
            print(f"Incomplete RIGHTS_LOG entries for {len(incomplete)} exemplar URL(s) (one or more required fields blank):", file=sys.stderr)
            for u in incomplete[:200]:
                print(f"- {u}", file=sys.stderr)
            if len(incomplete) > 200:
                print(f"... ({len(incomplete)-200} more)", file=sys.stderr)
        return 1

    print(f"OK: {len(exemplar_urls)} exemplar URL(s) validated against outputs/RIGHTS_LOG.csv")
    return 0

def main():
    repo_root = Path(__file__).resolve().parents[1]
    sys.exit(validate(repo_root))

if __name__ == "__main__":
    main()
