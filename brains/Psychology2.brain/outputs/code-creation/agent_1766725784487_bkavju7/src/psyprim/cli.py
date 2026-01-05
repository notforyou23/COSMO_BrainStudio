"""psyprim CLI: standardized primary-source workflows + lightweight tooling."""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from datetime import date, datetime
from pathlib import Path

REQUIRED = {
  "title": str, "authors": list, "year": int, "source_type": str,
  "repository": dict, "access_date": str, "local_path": str
}
REPO_REQUIRED = {"type": str, "url": str, "id": str}

CHECKLIST = [
  ("identification", "Record full bibliographic details; link to stable repository ID/URL."),
  ("acquisition", "Save raw primary file; compute checksum; store access date + retrieval method."),
  ("provenance", "Flag scan/photograph/OCR/transcription and any normalization; record who/when."),
  ("transcription", "Specify transcription method (manual/OCR/double-key); retain raw text + edits."),
  ("varianting", "Assign variant numbers for each derived file; never overwrite raw; log diffs."),
  ("citation", "Generate repository-linked citation string; embed in notes/manuscript."),
  ("auditability", "Ensure metadata + checksums allow independent re-fetch and byte-level verification."),
]

PROV_FLAGS = ["primary_source_checked","scan_verified","ocr_used","transcription_manual",
              "transcription_doublekeyed","normalization_applied","redaction_applied","uncertainty_noted"]

def _load(p: Path)->dict:
  d = json.loads(p.read_text(encoding="utf-8"))
  if not isinstance(d, dict): raise SystemExit("metadata must be a JSON object")
  return d

def _save(p: Path, d: dict):
  p.write_text(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def sha256_file(p: Path)->str:
  h=hashlib.sha256()
  with p.open("rb") as f:
    for b in iter(lambda: f.read(1024*1024), b""): h.update(b)
  return h.hexdigest()

def validate_meta(d: dict)->list[str]:
  errs=[]
  for k,t in REQUIRED.items():
    if k not in d: errs.append(f"missing:{k}"); continue
    if not isinstance(d[k], t): errs.append(f"type:{k}:{t.__name__}")
  if "authors" in d and any(not isinstance(a,str) or not a.strip() for a in d.get("authors",[])): errs.append("authors:nonempty strings")
  if "year" in d and (d["year"]<1400 or d["year"]>datetime.now().year+1): errs.append("year:range")
  r=d.get("repository",{})
  if not isinstance(r,dict): errs.append("type:repository:dict")
  else:
    for k,t in REPO_REQUIRED.items():
      if k not in r: errs.append(f"missing:repository.{k}")
      elif not isinstance(r[k],t) or not r[k].strip(): errs.append(f"type:repository.{k}:{t.__name__}")
  for k in ("access_date","local_path"):
    if k in d and isinstance(d[k],str) and d[k].strip()=="" : errs.append(f"{k}:nonempty")
  return errs

def build_citation(d: dict)->str:
  a=d.get("authors",[])
  auth = (a[0] + (" et al." if len(a)>1 else "")) if a else "Unknown"
  r=d.get("repository",{})
  return f"{auth} ({d.get('year','n.d.')}). {d.get('title','Untitled')}. {r.get('type','repo')}:{r.get('id','')}. {r.get('url','')} (accessed {d.get('access_date','')})."

def cmd_checklist(a):
  out = {"checklist":[{"id":i,"item":t} for i,t in CHECKLIST],
         "provenance_flags":PROV_FLAGS,
         "metadata_schema":{"required":list(REQUIRED.keys()),"repository_required":list(REPO_REQUIRED.keys())}}
  txt = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
  (Path(a.out).write_text(txt,encoding="utf-8") if a.out else sys.stdout.write(txt))

def cmd_init(a):
  d={"title":"","authors":[],"year":0,"source_type":"primary_source",
     "repository":{"type":"","url":"","id":""},"access_date":str(date.today()),
     "local_path":a.local_path,"checksum":"","provenance":{k:False for k in PROV_FLAGS},
     "variants":[],"citation":""}
  _save(Path(a.meta), d); print("OK:init")

def cmd_validate(a):
  d=_load(Path(a.meta)); errs=validate_meta(d)
  if a.compute_checksum and d.get("local_path"):
    lp=Path(d["local_path"])
    if lp.exists(): d["checksum"]=sha256_file(lp); _save(Path(a.meta), d)
  if a.update_citation:
    d["citation"]=build_citation(d); _save(Path(a.meta), d)
  if errs: sys.stderr.write("\n".join(errs)+"\n"); raise SystemExit(2)
  print("OK:valid")

def cmd_provenance(a):
  p=Path(a.meta); d=_load(p); prov=d.setdefault("provenance",{})
  for f in a.set_true: prov[f]=True
  for f in a.set_false: prov[f]=False
  d["provenance"]=prov; _save(p,d); print("OK:prov")

def cmd_variant(a):
  p=Path(a.meta); d=_load(p); vs=d.setdefault("variants",[])
  n=max([v.get("n",0) for v in vs]+[0])+1
  v={"n":n,"created":datetime.now().isoformat(timespec="seconds"),"notes":a.notes or ""}
  if a.file:
    fp=Path(a.file); v["file"]=str(fp)
    if fp.exists(): v["checksum"]=sha256_file(fp)
  vs.append(v); d["variants"]=vs; _save(p,d)
  sys.stdout.write(str(n)+"\n")

def cmd_cite_link(a):
  p=Path(a.meta); d=_load(p)
  if a.repo_type: d.setdefault("repository",{})["type"]=a.repo_type
  if a.repo_url: d.setdefault("repository",{})["url"]=a.repo_url
  if a.repo_id: d.setdefault("repository",{})["id"]=a.repo_id
  d["citation"]=build_citation(d); _save(p,d)
  (Path(a.out).write_text(d["citation"]+"\n",encoding="utf-8") if a.out else sys.stdout.write(d["citation"]+"\n"))

def cmd_eval_export(a):
  od=Path(a.outdir); od.mkdir(parents=True, exist_ok=True)
  survey=od/"survey_template.csv"
  audit=od/"audit_template.csv"
  with survey.open("w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["construct","question","scale","notes"])
    w.writerow(["effort","Minutes to locate primary source in repository","numeric","baseline vs tool"])
    w.writerow(["effort","Minutes to produce complete metadata + checksum","numeric",""])
    w.writerow(["effort","Minutes to generate citation and integrate in manuscript","numeric",""])
    w.writerow(["usability","Tool/protocol ease of use","1-7 Likert",""])
    w.writerow(["confidence","Confidence citation points to the exact consulted artifact","1-7 Likert",""])
  with audit.open("w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["study_id","condition","meta_path","citation_in_paper","citation_matches_repo_id","repo_url_resolves","checksum_present","checksum_matches","variant_log_present","repro_fetch_success","effort_minutes"])
  plan = od/"evaluation_design.json"
  plan.write_text(json.dumps({
    "design":{"type":"mixed_methods","components":["survey","audit_study"],"comparison":["baseline","with_protocol_tooling"]},
    "audit_procedure":["Sample papers/notes; extract citations","Resolve repository URL/ID; verify access_date",
                       "Re-fetch artifact; verify checksum; confirm variant trail","Score accuracy+reproducibility+effort"],
    "outcomes":{"citation_accuracy":["repo_id_match","url_resolves"],"reproducibility":["checksum_present","checksum_matches","repro_fetch_success"],"effort":["minutes_self_report","minutes_observed_optional"]},
    "protocol_elements":{"checklist":[i for i,_ in CHECKLIST],"metadata_required":list(REQUIRED.keys()),"provenance_flags":PROV_FLAGS,"variant_numbering":"monotone integer n with timestamps + checksums"}
  }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print("OK:eval_export")

def main(argv=None):
  ap=argparse.ArgumentParser(prog="psyprim", description="Primary-source protocol + metadata tooling for history of psychology")
  sp=ap.add_subparsers(dest="cmd", required=True)
  p=sp.add_parser("checklist"); p.add_argument("--out"); p.set_defaults(func=cmd_checklist)
  p=sp.add_parser("init"); p.add_argument("meta"); p.add_argument("--local-path", default=""); p.set_defaults(func=cmd_init)
  p=sp.add_parser("validate"); p.add_argument("meta"); p.add_argument("--compute-checksum", action="store_true"); p.add_argument("--update-citation", action="store_true"); p.set_defaults(func=cmd_validate)
  p=sp.add_parser("provenance"); p.add_argument("meta"); p.add_argument("--set-true", nargs="*", default=[] , choices=PROV_FLAGS); p.add_argument("--set-false", nargs="*", default=[], choices=PROV_FLAGS); p.set_defaults(func=cmd_provenance)
  p=sp.add_parser("variant"); p.add_argument("meta"); p.add_argument("--file"); p.add_argument("--notes"); p.set_defaults(func=cmd_variant)
  p=sp.add_parser("cite-link"); p.add_argument("meta"); p.add_argument("--repo-type"); p.add_argument("--repo-url"); p.add_argument("--repo-id"); p.add_argument("--out"); p.set_defaults(func=cmd_cite_link)
  p=sp.add_parser("eval-export"); p.add_argument("--outdir", required=True); p.set_defaults(func=cmd_eval_export)
  a=ap.parse_args(argv); a.func(a)

if __name__ == "__main__": main()
