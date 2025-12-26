#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

REQ = {
  "claim_text": ("claim_text_verbatim", "claim", "verbatim_claim", "claim_text"),
  "speaker": ("speaker", "claim_speaker"),
  "date": ("date", "claim_date"),
  "link": ("link", "url", "source_link"),
  "anchor": ("provenance_anchor", "anchor", "source_anchor", "provenance"),
}

URL_RE = re.compile(r"^https?://\S+$", re.I)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _pick(d, keys):
  for k in keys:
    if isinstance(d, dict) and k in d and d[k] not in (None, "", [], {}):
      return d[k]
  return None

def _norm_str(x):
  if x is None: return None
  if isinstance(x, (int, float)): return str(x)
  if isinstance(x, str): return x.strip()
  return None

def _anchor_ok(s: str) -> bool:
  s = (s or "").strip()
  if len(s) < 5: return False
  return (":" in s) or ("#" in s) or ("@" in s) or ("loc" in s.lower())

def _md_extract(text: str) -> dict:
  out = {}
  lines = text.splitlines()
  def grab(label):
    # Accept forms: "Label: value" OR a section header containing label then next non-empty lines until blank/header
    rx = re.compile(r"^\s*"+re.escape(label)+r"\s*:\s*(.+?)\s*$", re.I)
    for i,l in enumerate(lines):
      m = rx.match(l)
      if m: return m.group(1).strip()
    # Header form
    hx = re.compile(r"^\s{0,3}#{1,6}\s*"+re.escape(label)+r"\s*$", re.I)
    for i,l in enumerate(lines):
      if hx.match(l):
        buf = []
        for j in range(i+1, len(lines)):
          lj = lines[j]
          if re.match(r"^\s{0,3}#{1,6}\s+\S", lj): break
          if lj.strip()=="":
            if buf: break
            continue
          buf.append(lj.rstrip())
        return "\n".join(buf).strip()
    return None

  # Preferred labels (template-aligned)
  out["claim_text"] = grab("Claim (verbatim)") or grab("Verbatim claim") or grab("Claim")
  out["speaker"] = grab("Speaker") or grab("Who said it")
  out["date"] = grab("Date") or grab("When")
  out["link"] = grab("Link") or grab("Source link") or grab("URL")
  out["anchor"] = grab("Provenance anchor") or grab("Anchor") or grab("Provenance")
  return out

def validate_card(obj: dict, path: Path) -> list[str]:
  errs = []
  claim_text = _norm_str(_pick(obj, REQ["claim_text"]))
  ctx = obj.get("context") if isinstance(obj, dict) else None
  prov = obj.get("provenance") if isinstance(obj, dict) else None
  speaker = _norm_str(_pick(ctx, REQ["speaker"]) if isinstance(ctx, dict) else _pick(obj, REQ["speaker"]))
  date = _norm_str(_pick(ctx, REQ["date"]) if isinstance(ctx, dict) else _pick(obj, REQ["date"]))
  link = _norm_str(_pick(ctx, REQ["link"]) if isinstance(ctx, dict) else _pick(obj, REQ["link"]))
  anchor = _pick(prov, REQ["anchor"]) if isinstance(prov, dict) else _pick(obj, REQ["anchor"])
  anchor = _norm_str(anchor)

  if not claim_text:
    errs.append("missing required field: verbatim claim text (claim_text_verbatim)")
  else:
    # Stronger intake rule: must look like exact quoted text or multi-line excerpt
    if len(claim_text) < 8:
      errs.append("verbatim claim text too short; provide the exact claim text as stated")
  if not speaker: errs.append("missing required field: context.speaker")
  if not date: errs.append("missing required field: context.date (YYYY-MM-DD)")
  elif not DATE_RE.match(date): errs.append(f"invalid context.date '{date}' (expected YYYY-MM-DD)")
  if not link: errs.append("missing required field: context.link (http(s) URL)")
  elif not URL_RE.match(link): errs.append(f"invalid context.link '{link}' (expected http(s) URL)")
  if not anchor: errs.append("missing required field: provenance anchor")
  elif not _anchor_ok(anchor): errs.append(f"provenance anchor too weak '{anchor}'; include a precise locator (e.g., timestamp, page/paragraph, quote-id)")
  return [f"{path}: {e}" for e in errs]

def load_and_validate(path: Path) -> list[str]:
  try:
    if path.suffix.lower() == ".json":
      obj = json.loads(path.read_text(encoding="utf-8"))
      if not isinstance(obj, dict):
        return [f"{path}: JSON root must be an object"]
      return validate_card(obj, path)
    if path.suffix.lower() == ".md":
      md = path.read_text(encoding="utf-8")
      obj = _md_extract(md)
      return validate_card(obj, path)
    return []
  except Exception as e:
    return [f"{path}: failed to parse ({type(e).__name__}: {e})"]

def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description="Validate claim cards against updated intake checklist (verbatim claim + context + provenance anchor).")
  ap.add_argument("root", nargs="?", default=".", help="Root directory to scan (default: .)")
  ap.add_argument("--glob", dest="glob_", default="**/*", help="Glob under root (default: **/*)")
  ap.add_argument("--max-errors", type=int, default=200, help="Max errors to print (default: 200)")
  args = ap.parse_args(argv)

  root = Path(args.root).resolve()
  paths = [p for p in root.glob(args.glob_) if p.is_file() and p.suffix.lower() in (".md",".json")]
  errors = []
  for p in sorted(paths):
    errors.extend(load_and_validate(p))
    if len(errors) >= args.max_errors:
      break

  if errors:
    print("ABSTAIN: missing/invalid required intake fields; fix the errors below.", file=sys.stderr)
    for e in errors[:args.max_errors]:
      print(e, file=sys.stderr)
    return 2
  print(f"OK: validated {len(paths)} claim card file(s).")
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
