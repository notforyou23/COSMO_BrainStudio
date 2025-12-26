# Case Study Template

Use this template to document a single, evidence-backed case study that can be cited in reports and repositories. Write in complete sentences; where uncertainty exists, quantify it and explain why.

## 1) Case Study Header

- **Case study title:**  
- **Short description (1–2 sentences):**  
- **Date range covered (start–end):**  
- **Geography / setting:**  
- **Primary domain / sector:**  
- **Primary audience:**  
- **Confidentiality level:** Public / Internal / Restricted  
- **Primary contact (role, not name if sensitive):**  
- **Version:** v1.0  
- **Last updated (YYYY-MM-DD):**  

## 2) Executive Summary (150–250 words)

Summarize the problem, what was done, the evidence, the outcomes, and any key caveats. Include the most decision-relevant metric(s).

## 3) Context and Problem Statement

### 3.1 Background
Describe the setting, stakeholders, constraints, and why this problem mattered.

### 3.2 Problem statement
State the problem as a testable claim with a clear unit of analysis.
- **Unit of analysis:** (person, household, request, transaction, school, etc.)
- **Baseline condition:** what was true before the intervention/change?
- **Success criteria:** how you would recognize improvement/failure.

### 3.3 Intended users and decision
What decision did this work inform (funding, policy, product, operations)? What alternative options were considered?

## 4) Intervention / Approach

### 4.1 What was done
Describe the intervention, product change, program, policy, or process.
- **Inputs:** people, tooling, budget, time.
- **Activities:** key steps executed.
- **Outputs:** immediate deliverables produced.
- **Assumptions:** what had to be true for this to work.

### 4.2 Implementation details
Include practical details that affect reproducibility:
- Timeline and milestones
- Operational procedures
- Training, onboarding, or communications
- Failure modes encountered and mitigations

## 5) Methodology and Evidence

### 5.1 Study design
Specify the design and justify it:
- Experimental / quasi-experimental / observational / qualitative / mixed-methods
- Comparison group, counterfactual, or rationale for absence of one
- Power, sample size reasoning, and key identification assumptions (if applicable)

### 5.2 Data sources and collection
For each dataset/source, provide:
- **Source name and owner:**  
- **Collection method:** survey, logs, interviews, administrative records, etc.
- **Time window:**  
- **Inclusion/exclusion criteria:**  
- **Missingness and data quality checks:**  
- **Privacy/sensitivity classification:**  

### 5.3 Measures and instruments
Define the measures precisely:
- Primary outcome(s) and units
- Secondary outcome(s)
- Proxy measures (with known limitations)
- Instrument wording or survey items (if any)
- Measurement frequency and aggregation

### 5.4 Analysis
Explain the analysis in a way a peer could replicate:
- Preprocessing steps (cleaning, joins, deduplication)
- Statistical/qualitative techniques used
- Model specs or coding framework (if relevant)
- Robustness checks / sensitivity analyses
- How you handled confounders, seasonality, or selection bias

### 5.5 Evidence artifacts (linkable)
List the concrete artifacts that support claims (files, tables, notebooks, dashboards). Prefer stable paths/IDs.
- Artifact 1:  
- Artifact 2:  
- Artifact 3:  

## 6) Results and Outcomes

### 6.1 Key results (with numbers)
Provide the most important results with effect sizes and uncertainty where possible.
- Result 1 (metric, baseline → post, delta, CI/SE if available):  
- Result 2:  
- Result 3:  

### 6.2 Operational outcomes
Document practical changes (throughput, cost, cycle time, error rates, compliance incidents, staff time).

### 6.3 User/stakeholder outcomes
Include qualitative feedback and adoption metrics. Quote sparingly and protect identities.

### 6.4 Heterogeneity and equity impacts
Report differences across relevant groups or contexts and justify subgroup choices.
- Which groups were assessed and why
- Any observed disparate impact (positive or negative)
- Mitigations or follow-up actions

## 7) Interpretation

### 7.1 What we learned
Interpret results relative to the original success criteria and competing explanations.

### 7.2 Causal claims (if any)
State clearly what is causal vs. correlational and the basis for that claim.

### 7.3 Generalizability
Where does this apply (and not apply)? What contextual factors are necessary?

## 8) Limitations and Risks

Cover at minimum:
- Data limitations (coverage, measurement error, missingness)
- Threats to validity (selection, spillovers, history, instrumentation)
- Unintended consequences and safety risks
- Model/automation risks (if applicable): drift, bias, overreliance, adversarial use

## 9) Recommendations and Next Steps

- Decision recommendation (go/no-go/iterate) with rationale
- What to improve next (methods, implementation, measurement)
- Monitoring plan and leading indicators
- Open questions and proposed experiments

## 10) Rights, Licensing, and Permissions (Required)

This case study should be publishable only if rights are cleared for all included materials (text, charts, images, code, datasets, quotes).
- **Rights basis for this document:** original work / licensed / fair use / permission obtained / mixed (explain)
- **Third-party content included?** Yes/No  
  If yes, enumerate each item (figure/table/image/quote/dataset) and its license/permission status.
- **Attribution requirements:** provide exact attribution text where needed.
- **Privacy and consent:** confirm consent status for any human-subject content, photos, interviews, or quotes.
- **Restricted data handling:** describe how restricted data is stored, accessed, and minimized.

Cross-reference the project’s rights artifacts (expected at the repository level):
- `outputs/RIGHTS_AND_LICENSING_CHECKLIST.md` (completion checklist)
- `outputs/RIGHTS_LOG.csv` (row-per-asset permissions and license tracking)

## 11) Citation and Metadata

### 11.1 Suggested citation
Provide a stable citation format (authoring org, title, version, date, URL/path, access date if relevant).

### 11.2 Metadata fields (align with project schema)
Capture the fields used by your project’s metadata schema (e.g., `outputs/METADATA_SCHEMA.json` or `.yaml`):
- Title
- Abstract
- Keywords/tags
- Authors/roles
- Dates (created, updated)
- Methods
- Data sources
- Rights/license
- Identifiers/links to evidence artifacts

## Appendix A: Definitions (optional)
Define domain-specific terms, acronyms, and measures.

## Appendix B: Change Log (optional)
- YYYY-MM-DD: Summary of edits, author role
