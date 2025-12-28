# Task Taxonomy Codebook v0.1

Purpose: Provide consistent annotation guidance for task taxonomy records (single user request + expected assistant behavior).

## Record unit
Annotate the *primary* task implied by the user request. If multiple tasks exist, choose the dominant end-goal; list secondary intents only if the schema supports it (otherwise ignore).

## Core fields (what annotators label)
- **task_type**: what the user wants done (intent).
- **domain**: subject area used to complete the task.
- **interaction_mode**: how the user expects to work (single-shot vs iterative vs tool/automation).
- **output_format**: dominant expected artifact type.
- **safety_sensitivity**: whether special caution is required.
- **difficulty**: estimated complexity for a competent assistant.

## task_type (single label)
Definitions, decision rules, and examples.

Allowed values:
1. **information_exploration** — Explain, summarize, compare, or answer questions; user mainly wants understanding.
   - Choose when the best response is primarily *explanatory* (even if it includes small examples).
   - Example: “Explain the difference between TCP and UDP.”
2. **how_to_guidance** — Step-by-step instructions to accomplish something.
   - Choose when the user wants a procedure, checklist, or troubleshooting steps.
   - Example: “How do I reset a forgotten Windows password?”
3. **creative_generation** — Create novel content (stories, marketing copy, names, prompts).
   - Choose when originality/style is central; factuality is secondary.
   - Example: “Write a short sci-fi story about a lost probe.”
4. **editing_transformation** — Rewrite, translate, summarize *provided* text, change tone/format.
   - Choose when input text is supplied or clearly implied (e.g., “rewrite my email”).
   - Example: “Rewrite this paragraph to be more formal: …”
5. **coding_software** — Write/debug/explain code, design APIs, implement scripts, review code.
   - Choose when the response should include code or software-engineering guidance.
   - Example: “Write a Python script to deduplicate a CSV.”
6. **data_analysis** — Analyze/interpret data, compute metrics, create tables/plots (data-centric).
   - Choose when data (numbers, dataset, logs) is central and analysis is expected.
   - Example: “Given these sales numbers, compute MoM growth and flag outliers.”
7. **planning_decision_support** — Recommendations, tradeoffs, prioritization, strategy, next steps.
   - Choose when the user wants a decision and rationale rather than instructions alone.
   - Example: “Help me choose between two job offers.”
8. **transactional_assistance** — Compose or perform a specific practical action (emails, forms, scheduling, templates).
   - Choose when the output is meant to be *used directly* to execute an action.
   - Example: “Draft a complaint email to my landlord.”

Tie-breakers:
- If user asks “explain X” + “give steps to do X”, choose **how_to_guidance** when steps are the primary ask; otherwise **information_exploration**.
- If user provides text to rewrite, prefer **editing_transformation** even if the topic is technical.
- If the user wants runnable code/scripts, prefer **coding_software** over **how_to_guidance**.

## domain (single label)
Pick the domain most necessary to solve the task (not merely mentioned).

Allowed values:
- **general** (no specialized domain required)
- **software_it**
- **data_science**
- **business_finance**
- **health_medical**
- **legal_policy**
- **education**
- **science_engineering**
- **arts_media**
- **personal_life**

Decision rules:
- Prefer **software_it** for programming, systems, security basics, devops.
- Prefer **data_science** for statistics/ML/experiments/SQL analytics even if coded.
- Prefer **legal_policy** for laws, contracts, compliance, immigration, taxes (when legal framing is required).
- If multiple apply, choose the one that constrains correctness most (e.g., medical dosage ⇒ **health_medical**).

## interaction_mode (single label)
Allowed values:
- **single_turn** — one response likely sufficient.
- **iterative_collaboration** — user expects back-and-forth refinement (draft/revise, brainstorming with feedback).
- **tool_or_automation** — request implies executing steps via tools, scripts, pipelines, or agentic workflows.

Decision rules:
- If user asks for a script/automation to run repeatedly, choose **tool_or_automation**.
- If user asks “ask me questions” / “let’s iterate”, choose **iterative_collaboration**.

## output_format (single label)
Allowed values:
- **freeform_text**
- **bulleted_list**
- **table**
- **code**
- **json**
- **csv**
- **markdown_document**
- **plan_checklist**

Decision rules:
- Choose **code** when the main artifact is executable/source code.
- Choose **markdown_document** for structured docs (README, spec, codebook).
- If multiple formats appear, pick the dominant deliverable (largest/primary).

## safety_sensitivity (single label)
Allowed values:
- **low** — benign topics.
- **medium** — could cause harm if wrong; needs cautious phrasing (finance, mild medical, security best-practices).
- **high** — self-harm, violence, explicit illegal wrongdoing, medical/legal advice with high stakes, weapons.

Decision rules:
- Choose **high** if instructions could materially enable harm or illegal activity.
- Choose **medium** for health/legal/finance info framed generally (not urgent or extreme).

## difficulty (single label)
Allowed values:
- **easy** — straightforward, common knowledge, minimal constraints.
- **moderate** — multiple steps, some nuance, requires synthesis.
- **hard** — complex constraints, specialized expertise, significant reasoning/edge cases.

## Labeled examples (v0.1)
Each example shows: task_type | domain | interaction_mode | output_format | safety_sensitivity | difficulty

1) “Summarize this research abstract in 5 bullets: …”
- editing_transformation | science_engineering | single_turn | bulleted_list | low | easy

2) “Write a Python validator that checks required JSON fields and prints clear errors.”
- coding_software | software_it | tool_or_automation | code | low | moderate

3) “Compare Roth vs Traditional IRA and recommend based on my income and goals.”
- planning_decision_support | business_finance | iterative_collaboration | freeform_text | medium | moderate

4) “How do I treat a burn blister at home?”
- how_to_guidance | health_medical | single_turn | plan_checklist | medium | moderate

5) “Draft a polite email asking for a refund and include order details placeholders.”
- transactional_assistance | general | single_turn | freeform_text | low | easy

6) “Generate 20 brand name ideas for an eco-friendly detergent; include slogans.”
- creative_generation | business_finance | single_turn | bulleted_list | low | easy

7) “Here’s a CSV of churn; compute cohort retention and visualize trends.”
- data_analysis | data_science | tool_or_automation | table | low | hard

8) “Explain how public-key cryptography works at a high level.”
- information_exploration | software_it | single_turn | freeform_text | low | moderate

## Quality checks (annotator self-audit)
- Does task_type reflect the *primary* user intent (not the assistant method)?
- Does domain reflect the expertise needed to be correct?
- Is output_format the dominant deliverable?
- Are safety and difficulty conservative but not inflated?
