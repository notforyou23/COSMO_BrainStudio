from __future__ import annotations
from pathlib import Path
import csv

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = BASE_DIR / "outputs"

GUIDE_MD = """# Customer Discovery + Pricing Validation Guide

## Goal
Validate: (1) the problem/use case and urgency, (2) buying process and decision criteria, (3) willingness-to-pay (WTP) and pricing/packaging, (4) objections and regulatory/compliance concerns.

## Target participants (edit as needed)
- Economic buyer (budget owner)
- Champion / day-to-day user
- Technical evaluator / IT / security
- Compliance / legal (if regulated)

## Research hypotheses (to validate/falsify)
H1. The primary job-to-be-done is time/cost reduction or risk reduction in a repeatable workflow.
H2. Buyers decide based on ROI, time-to-value, integration effort, and risk/compliance fit.
H3. There is an identifiable trigger event that increases urgency (audit, deadline, incident, growth, staffing change).
H4. WTP correlates with: volume/throughput, risk exposure, and number of stakeholders.
H5. Packaging should map to: (a) usage/volume, (b) compliance features, (c) support/SLA, (d) integration depth.

## Interview structure (45–60 minutes)
1) Warm-up + context (5–10)
2) Current workflow + pain (10–15)
3) Buying process + decision criteria (10–15)
4) Pricing/WTP module (10–15)
5) Objections + compliance/regulatory (5–10)
6) Wrap-up + referrals (2–5)

## Interview script (copy/paste)
### 1) Warm-up / firmographics
- What is your role and what outcomes are you responsible for?
- Who else is involved in this workflow? (teams, vendors, stakeholders)
- How do you measure success today?

### 2) Current workflow + pain discovery
- Walk me through the last time you did this, step by step.
- Where does it get slow, risky, or expensive?
- What tools/vendors do you use today? Why those?
- What happens if nothing changes for 6–12 months?
- What would make this a “must fix now”?

### 3) Use case definition + value
- Which part of the workflow matters most to improve: speed, quality, compliance, cost, or visibility?
- What does an ideal solution do on day 1?
- What are non-negotiable requirements?
- What would make you stop using a new solution after a trial?

### 4) Buying process + decision criteria
- When you buy something like this, what is the process?
- Who has veto power? Who signs? Who uses?
- What are the top 3 decision criteria?
- What security/compliance checks are required (SOC2, HIPAA, GDPR, ISO, vendor risk, data residency)?

### 5) Pricing / WTP module (choose 2–4 techniques)
**A. Van Westendorp (price sensitivity)**
- At what price would this be so cheap you’d question quality?
- At what price would it be a bargain?
- At what price would it start to feel expensive but still worth it?
- At what price would it be too expensive to consider?

**B. Reference pricing + anchors**
- What do you pay today (tools, labor, vendors)? Rough order of magnitude is fine.
- If this replaced part of that spend, what budget line would it come from?

**C. Package preference**
- Which matters more: lower price or higher certainty (SLA/support/compliance)?
- Would you prefer per-user, per-workflow, per-usage, or flat annual pricing? Why?

**D. Commitment + procurement**
- Would you buy monthly, annual, or multi-year if there were clear ROI?
- What purchase amount triggers procurement/security review?

### 6) Objections + compliance/regulatory
- What would make this a “no” even if it worked?
- What data cannot leave your environment? Any retention/deletion requirements?
- Any regulations that shape your choices (HIPAA/FINRA/SEC/GDPR/FERPA, etc.)?

### 7) Wrap-up
- If we built the ideal solution, who else should we talk to?
- Can we follow up to validate pricing/packaging and a pilot plan?

## Notes template
- Segment:
- Use case:
- Current solution:
- Trigger event / urgency:
- Decision criteria (ranked):
- Budget / WTP:
- Objections:
- Regulatory/compliance:
- Next steps:
"""

def write_tracker_csv(path: Path) -> None:
    fields = ["date","company","name","title","email","segment","use_case","decision_criteria","budget","objections","regulatory_concerns","notes","follow_up_date","status"]
    sample = {
        "date":"","company":"","name":"","title":"","email":"",
        "segment":"", "use_case":"", "decision_criteria":"",
        "budget":"", "objections":"", "regulatory_concerns":"",
        "notes":"","follow_up_date":"","status":"scheduled"
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for _ in range(8):
            w.writerow(sample)

def write_pricing_sheet(out_path: Path) -> str:
    rows = [
        ["section","field","value","notes"],
        ["meta","product_name","(edit)",""],
        ["meta","pricing_model_hypothesis","Usage-based + tiers",""],
        ["segments","segment_1","SMB / Mid-market / Enterprise","edit"],
        ["use_cases","use_case_1","Primary workflow being improved","edit"],
        ["van_westendorp","too_cheap","",""],
        ["van_westendorp","bargain","",""],
        ["van_westendorp","expensive_but_worth_it","",""],
        ["van_westendorp","too_expensive","",""],
        ["anchors","current_spend_tools","","$/mo or $/yr"],
        ["anchors","current_spend_labor","","hrs/mo * $/hr"],
        ["procurement","approval_threshold","","e.g., >$10k requires review"],
        ["packaging","tier_1_name","Starter",""],
        ["packaging","tier_1_price","", "e.g., $499/mo"],
        ["packaging","tier_1_limits","", "usage/users/volume"],
        ["packaging","tier_2_name","Pro",""],
        ["packaging","tier_2_price","", ""],
        ["packaging","tier_2_limits","", ""],
        ["packaging","tier_3_name","Enterprise",""],
        ["packaging","tier_3_price","", ""],
        ["packaging","tier_3_limits","", ""],
        ["discounts","annual_discount","", "e.g., 10-20%"],
        ["objections","top_objection_1","",""],
        ["regulatory","requirements","","SOC2, HIPAA, GDPR, etc."],
        ["decision","top_criteria_ranked","","ROI; integration; compliance; time-to-value"]
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import xlsxwriter  # type: ignore
        xlsx_path = out_path.with_suffix(".xlsx")
        wb = xlsxwriter.Workbook(str(xlsx_path))
        ws = wb.add_worksheet("WTP_Pricing")
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                ws.write(r, c, val)
        ws.freeze_panes(1, 0)
        wb.close()
        return str(xlsx_path)
    except Exception:
        csv_path = out_path.with_suffix(".csv")
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerows(rows)
        return str(csv_path)

def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "customer_discovery_guide.md").write_text(GUIDE_MD, encoding="utf-8")
    pricing_written = write_pricing_sheet(OUTPUTS_DIR / "wtp_pricing_sheet")
    write_tracker_csv(OUTPUTS_DIR / "interview_tracker.csv")
    print("WROTE:", str(OUTPUTS_DIR / "customer_discovery_guide.md"))
    print("WROTE:", pricing_written)
    print("WROTE:", str(OUTPUTS_DIR / "interview_tracker.csv"))

if __name__ == "__main__":
    main()
