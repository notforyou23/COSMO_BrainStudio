#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

LABEL = "e2e-failure"
UA = "issue_on_failure.py"
FINGERPRINT_RE = re.compile(r"<!--\s*fingerprint:([a-f0-9]{8,40})\s*-->")

def _jget(d: Any, *keys: str, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d[k]
    return default

def load_summary(path: str) -> Dict[str, Any]:
    p = os.path.abspath(path)
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        data = {"failures": data}
    if not isinstance(data, dict):
        raise SystemExit("failure summary must be a JSON object or list")
    failures = data.get("failures")
    if failures is None and "stages" in data:
        failures = [s for s in data.get("stages", []) if s.get("status") == "failed"]
        data["failures"] = failures
    if not isinstance(data.get("failures", []), list):
        data["failures"] = []
    data["_path"] = p
    return data

def normalize_failure(f: Dict[str, Any]) -> Dict[str, Any]:
    stage = str(_jget(f, "stage", "name", default="unknown"))
    msg = str(_jget(f, "message", "error", "summary", default="(no message)"))
    cmd = _jget(f, "command", "cmd", default=None)
    log = _jget(f, "log_path", "log", "stderr_path", default=None)
    return {"stage": stage, "message": msg, "command": cmd, "log_path": log}

def fingerprint(f: Dict[str, Any]) -> str:
    stage = f.get("stage", "unknown")
    first = (f.get("message") or "").strip().splitlines()[:1]
    sig = f"{stage}\n{first[0] if first else ''}".encode("utf-8", "ignore")
    return hashlib.sha1(sig).hexdigest()[:12]

def repro_steps(summary: Dict[str, Any], f: Dict[str, Any]) -> str:
    sha = _jget(summary, "sha", "git_sha", default=os.getenv("GITHUB_SHA", ""))
    run_url = _jget(summary, "run_url", default=os.getenv("GITHUB_SERVER_URL", "") + "/" + os.getenv("GITHUB_REPOSITORY", "") + "/actions/runs/" + os.getenv("GITHUB_RUN_ID", ""))
    cmd = f.get("command") or "make e2e"
    lines = [
        "### Minimal reproduction",
        "1. Check out the failing commit:",
        f"   - `{sha}`" if sha else "   - (unknown SHA)",
        f"2. Run: `{cmd}`",
    ]
    if f.get("log_path"):
        lines.append(f"3. Inspect logs: `{f['log_path']}` (see CI artifacts if available)")
    if run_url and run_url.strip("/"):
        lines.append("")
        lines.append(f"CI run: {run_url}")
    return "\n".join(lines)

def gh_request(method: str, url: str, token: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": UA,
    })
    for _ in range(3):
        r = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2)
            continue
        return r
    return r

def find_existing_issue(repo: str, token: str, fp: str) -> Optional[Dict[str, Any]]:
    q = f"repo:{repo} is:issue is:open label:{LABEL} in:body fingerprint:{fp}"
    url = f"https://api.github.com/search/issues?q={requests.utils.quote(q)}"
    r = gh_request("GET", url, token)
    if r.status_code != 200:
        return None
    items = r.json().get("items", []) or []
    return items[0] if items else None

def create_issue(repo: str, token: str, title: str, body: str) -> Tuple[int, str]:
    url = f"https://api.github.com/repos/{repo}/issues"
    payload = {"title": title, "body": body, "labels": [LABEL]}
    r = gh_request("POST", url, token, json=payload)
    if r.status_code not in (200, 201):
        raise SystemExit(f"failed to create issue: {r.status_code} {r.text[:200]}")
    j = r.json()
    return int(j["number"]), j.get("html_url", "")

def comment_issue(repo: str, token: str, number: int, body: str) -> None:
    url = f"https://api.github.com/repos/{repo}/issues/{number}/comments"
    r = gh_request("POST", url, token, json={"body": body})
    if r.status_code not in (200, 201):
        raise SystemExit(f"failed to comment: {r.status_code} {r.text[:200]}")
def build_issue(title_prefix: str, summary: Dict[str, Any], f: Dict[str, Any]) -> Tuple[str, str, str]:
    nf = normalize_failure(f)
    fp = fingerprint(nf)
    msg = (nf["message"] or "").strip()
    short = (msg.splitlines()[:1] or ["(no message)"])[0]
    short = short[:120]
    title = f"{title_prefix}{nf['stage']}: {short}"
    body = "\n".join([
        f"<!-- fingerprint:{fp} -->",
        "### Failure",
        f"- Stage: `{nf['stage']}`",
        f"- Message:\n\n```text\n{msg.strip()}\n```" if msg else "- Message: (none)",
        "",
        repro_steps(summary, nf),
        "",
        "### Context",
        f"- Summary file: `{summary.get('_path','')}`",
        f"- Workflow: `{os.getenv('GITHUB_WORKFLOW','')}` Run ID: `{os.getenv('GITHUB_RUN_ID','')}`",
    ]).strip() + "\n"
    return fp, title, body

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Open or update GitHub issues for e2e failures.")
    ap.add_argument("--summary", default=os.getenv("FAILURE_SUMMARY", "artifacts/failure_summary.json"))
    ap.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    ap.add_argument("--token", default=os.getenv("GITHUB_TOKEN", ""))
    ap.add_argument("--title-prefix", default="[e2e] ")
    args = ap.parse_args(argv)

    if not args.repo:
        raise SystemExit("GITHUB_REPOSITORY or --repo is required (e.g. owner/repo)")
    if not args.token:
        raise SystemExit("GITHUB_TOKEN or --token is required")

    summary = load_summary(args.summary)
    failures = summary.get("failures", []) or []
    if not failures:
        print("No failures found; nothing to do.")
        return 0

    created = updated = 0
    for f in failures:
        if not isinstance(f, dict):
            continue
        fp, title, body = build_issue(args.title_prefix, summary, f)
        existing = find_existing_issue(args.repo, args.token, fp)
        if existing and existing.get("number"):
            num = int(existing["number"])
            comment = "\n".join([
                f"Reproduced in a new CI run.",
                repro_steps(summary, normalize_failure(f)),
            ])
            comment_issue(args.repo, args.token, num, comment)
            updated += 1
            print(f"UPDATED_ISSUE:{num}")
        else:
            num, url = create_issue(args.repo, args.token, title, body)
            created += 1
            print(f"CREATED_ISSUE:{num}:{url}")
    print(f"STATS:created={created} updated={updated} total={created+updated}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
