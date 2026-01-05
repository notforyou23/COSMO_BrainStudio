# Task Taxonomy Codebook v0.1

Purpose: Provide consistent, human-annotatable categories for describing tasks and their evaluation context. Use this codebook with the accompanying annotation schema/validator.

General rules
- Annotate what the user is asking the system to do (the *primary task*), not what the system actually outputs.
- Prefer the narrowest category that fully fits; if unsure, choose the closest broader category and note ambiguity in `notes`.
- If multiple tasks exist, choose the highest-level *dominant* task; record secondary tasks in `secondary_tasks` if your schema supports it.
- For “meta” requests about the assistant (policies, capabilities), classify as `task_type=meta_assistant`.
## 1) task_type (required)
Pick exactly one primary task category.

1. **qa_fact**: Answer factual questions; retrieve/recall/explain facts.
   - Include: definitions, historical facts, “what is X”, “when did Y”.
   - Exclude: advice/choices (see `recommendation`), computations (see `math_calc`).

2. **qa_explanation**: Conceptual explanation or teaching without a specific artifact.
   - Include: “explain how…”, “why…”, “compare A vs B”.
   - Rule: If the user requests an output artifact (plan, code, email), prefer those task types.

3. **summarization**: Condense provided content.
   - Include: “summarize this article/transcript”, executive summary.
   - Rule: If also extracting fields, choose `extraction_structuring` unless summary is clearly primary.

4. **translation**: Translate text between languages.
   - Rule: If also rewriting tone/length, use `rewrite_editing` and specify original/target language in `notes`.

5. **rewrite_editing**: Rewrite, proofread, change tone/clarity, or edit text.
   - Include: grammar fixes, style changes, shorten/expand, convert to bullet points (without strict schema).

6. **information_extraction**: Extract specific facts/entities from content without enforcing a structured schema.
   - Include: “what dates are mentioned?”, “list all people”.
   - Rule: If output must conform to a schema/table/JSON, use `extraction_structuring`.

7. **extraction_structuring**: Convert content into a structured form (JSON, CSV, table with defined columns).
   - Include: “convert to JSON with fields…”, “make a table with columns…”.

8. **classification_tagging**: Assign labels/categories to items.
   - Include: sentiment, topic labels, spam/not spam.
   - Rule: If labeling is about safety/policy compliance, still classify here; note in `domain=safety_policy`.

9. **planning**: Produce a plan/steps/schedule/checklist.
   - Include: project plans, study plans, itineraries.
   - Rule: If user requests a decision among options, use `recommendation`.

10. **recommendation**: Choose or rank options, advise on what to do/buy, personalized suggestions.
   - Include: “which laptop should I get?”, “best approach”.
   - Rule: If only providing pros/cons without choosing, still use this if intent is decision support.

11. **math_calc**: Compute numeric answers, solve equations, perform quantitative reasoning.
   - Include: unit conversions, probability, budgeting math.
   - Rule: If coding is requested to compute, use `coding` if code artifact is primary.

12. **data_analysis**: Analyze data (tables/CSVs) for insights, stats, trends.
   - Include: interpret charts, compute summary stats, A/B test reasoning.
   - Rule: If asked to build a model/pipeline in code, may be `coding` with `domain=data_science`.

13. **coding**: Write/modify/debug code or scripts.
   - Include: implement functions, fix bugs, write CLI, refactor.
   - Rule: If request is “explain this code”, use `qa_explanation`.

14. **creative_generation**: Create novel content (stories, poems, slogans, images prompts).
   - Include: fiction, marketing copy when creativity is primary.
   - Rule: If constrained business artifact (email, report) is requested, consider `writing_composition`.

15. **writing_composition**: Compose functional writing artifacts.
   - Include: emails, memos, reports, resumes, cover letters.
   - Rule: If rewriting provided draft, use `rewrite_editing`.

16. **roleplay_simulation**: Simulate a persona, interview, dialogue, or scenario.
   - Include: mock interviews, customer roleplay, therapy-style conversation (non-clinical).

17. **meta_assistant**: Questions about the assistant/tools/system, prompts, policies, or capabilities.
   - Include: “what can you do?”, “write a system prompt”, “are you allowed to…”.

18. **other**: Use only if none apply; describe in `notes` and consider updating taxonomy.
## 2) domain (required)
Choose the primary subject area.

Allowed values
- general
- business_finance
- legal
- medical_health
- education
- software_it
- data_science
- science_engineering
- arts_entertainment
- social_science_humanities
- safety_policy
- personal_life

Decision rules
- Use `medical_health` for diagnosis/treatment/medical decisions; wellness tips without medical claims may be `personal_life` or `general`.
- Use `legal` for interpreting laws/contracts or legal strategy; otherwise `business_finance` for general corporate matters.
- Use `safety_policy` for content moderation, compliance, or policy interpretation tasks.
## 3) input_modality (required) and output_modality (required)
Indicate the primary modalities involved.

Allowed values (both fields)
- text
- code
- table_data
- image
- audio
- multimodal

Rules
- If multiple inputs are essential (e.g., text + image), set `input_modality=multimodal`.
- If producing code as the main artifact, set `output_modality=code` (even if surrounded by text explanation).
## 4) outcome_type (required)
What kind of real-world impact is implied by the user’s goal?

Allowed values
- intangible: low direct real-world consequence (learning, curiosity, entertainment).
- tangible: could directly affect money, health, legal status, safety, employment, infrastructure, or irreversible actions.

Rules
- If the user intends to act on the answer (purchase, medical action, legal filing, operational change), prefer `tangible`.
- If purely informational/educational without action stakes, prefer `intangible`.
## 5) stake_magnitude (conditionally required)
Required if `outcome_type=tangible`. Not allowed/leave empty if `outcome_type=intangible`.

Allowed values
- low: minor inconvenience or small cost; easily reversible.
- medium: meaningful cost or moderate risk; partially reversible.
- high: significant financial/health/legal/safety risk; hard to reverse.

Rules
- Choose the highest reasonable stake implied by the task.
- If ambiguity exists, choose `medium` and note why in `notes`.
## 6) autonomy_level (required)
How much independent action is requested?

Allowed values
- advise_only: provide info/suggestions; user executes actions.
- draft_artifact: produce an artifact (email, code, plan) for user review.
- execute_actions: explicitly asked to run commands, make purchases, contact people, deploy changes.

Rules
- If the assistant is asked to “send”, “buy”, “deploy”, “delete”, or “make changes”, use `execute_actions` even if you cannot actually execute.
## 7) context_sensitivity (required)
How sensitive is the content regarding privacy, identity, or confidential data?

Allowed values
- none: no personal or confidential data.
- personal: includes personal preferences, non-sensitive personal info.
- sensitive: includes credentials, medical details, financial account info, legal cases, minors, or secrets.

Rule: If user provides identifiers (full name + address, account numbers, SSN), mark `sensitive`.
## 8) ambiguity_level (required)
Annotate how clear the request is.

Allowed values
- clear: single, well-specified task.
- some_ambiguity: missing details but likely intent.
- unclear: intent or success criteria cannot be inferred.

Rule: If `unclear`, the best assistant response would primarily ask clarifying questions; note missing info in `notes`.
## 9) Decision checklist (quick)
- Identify primary `task_type` by requested output.
- Set `domain` by subject matter (not by format).
- Set modalities by what is essential to solve/provide.
- If real-world action/impact: `outcome_type=tangible` and require `stake_magnitude`.
- If asked to take actions: raise `autonomy_level` accordingly.
- Mark `context_sensitivity` based on provided/required personal data.
## 10) Examples (minimal)
1) “Summarize the pasted meeting notes into 5 bullets.” -> task_type=summarization; domain=business_finance; outcome_type=intangible.
2) “Which medication is best for my symptoms?” -> task_type=recommendation; domain=medical_health; outcome_type=tangible; stake_magnitude=high.
3) “Convert this resume into JSON with fields {name, experience[]}.” -> task_type=extraction_structuring; output_modality=table_data (or text if JSON in text); outcome_type=intangible.
4) “Write a Python script to validate a CSV of labels.” -> task_type=coding; domain=software_it; autonomy_level=draft_artifact.
