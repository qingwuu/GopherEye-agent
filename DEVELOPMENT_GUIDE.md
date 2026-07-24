# GopherEye Wiki App Development Guide

This document explains how to develop the root-level GopherEye wiki app in a strictly
separated and auditable way.

## 1. Core Principle

Do not mix these layers:

```text
raw source evidence
curated wiki knowledge
schemas
prompts
tools
flows
evaluation
model weights
```

Each layer has a different purpose. Mixing them makes the system hard to debug
and hard to explain to a professor, reviewer, or future app developer.

## 2. Directory Responsibilities

### `raw/`

Stores original materials.

Examples:

```text
raw/sources/disease/powdery_mildew.md
raw/sources/meeting/pi_meeting.md
raw/images/powdery_mildew/example_001.jpg
raw/source_manifest.jsonl
```

Rules:

```text
Do not edit raw sources after ingestion.
Do not let the app directly trust raw source text.
Use raw sources to generate reviewed wiki drafts.
```

### `wiki/`

Stores curated plant, grape, grape leaf, diagnosis, procedure, routine, expert
case, and reviewed treatment-resource knowledge.

Do not put model/provider/system architecture pages in `wiki/`.

Examples:

```text
wiki/diseases/powdery_mildew.md
wiki/grape_leaf/anatomy.md
wiki/grape_leaf/leaf_surfaces.md
wiki/grape_leaf/normal_variation.md
wiki/grape_leaf/image_guidance.md
wiki/workflows/evidence_sufficiency.md
wiki/workflows/front_back_request.md
wiki/procedures/whole_diagnosis_process.md
wiki/treatment_resources/treatment_resource_policy.md
```

Rules:

```text
Write concise, reviewed, linkable markdown.
Use hyperlinks to connect related pages.
Keep app-facing rules explicit.
Mention source provenance when possible.
```

### `system/`

Stores implementation-facing documentation.

Examples:

```text
system/models/model_choice.md
system/agents/frontier_agent_system.md
system/contracts/schema_layer.md
system/tools/tool_layer.md
system/data/dataset_memory.md
system/source_requirements/raw_source_intake_rules.md
```

Rules:

```text
Keep model/provider/tool/schema/data-pipeline documentation out of wiki/.
Link from system/ into wiki/ when domain routines are referenced.
Do not include system-only pages in the wiki catalog.
```

### `schemas/`

Stores machine-readable contracts.

Examples:

```text
schemas/diagnosis_output.schema.json
schemas/visual_intake.schema.json
schemas/wiki_update_proposal.schema.json
```

Rules:

```text
Use schemas to validate model outputs.
Do not rely on prompt text alone.
Keep enums aligned with dataset labels.
```

### `prompts/`

Stores reusable instructions.

Examples:

```text
prompts/visual_intake_prompt.md
prompts/diagnosis_decision_prompt.md
prompts/wiki_update_prompt.md
```

Rules:

```text
Keep prompts model-agnostic when possible.
Put stable domain rules in wiki/, machine-readable contracts in schemas/, and
implementation rules in system/.
Version prompts in Git.
```

### `tools/`

Stores deterministic actions.

Examples:

```text
tools/wiki_tools.py
tools/read_wiki_page.py
tools/check_links.py
tools/validate_json.py
```

Rules:

```text
Tools do actions.
Models decide or propose.
Code enforces permissions and validation.
```

### `flows/`

Stores repeatable procedures.

Examples:

```text
flows/wiki_update_flow.md
flows/image_diagnosis_flow.md
flows/followup_chat_flow.md
```

Rules:

```text
Flows define step order.
Flows call prompts, tools, schemas, and models.
Human review is required before curated wiki changes.
```

### `eval/`

Stores behavior checks.

Examples:

```text
eval/wiki_qa_questions.jsonl
eval/diagnosis_behavior_cases.jsonl
```

Rules:

```text
Every important behavior should have a regression test.
Test both strong cloud models and local models.
Record model failures for later prompt improvement or fine-tuning.
```

## 3. Wiki Update Flow

Use this when a new source, meeting note, disease note, or paper appears.

```text
1. Add raw source.
2. Classify source type.
3. Select related wiki pages.
4. Generate draft update.
5. Add or suggest markdown hyperlinks.
6. Validate frontmatter and links.
7. Write update report.
8. Human reviews draft.
9. Human accepts and edits curated wiki.
10. Rebuild catalog.
11. Commit to GitHub.
```

Important constraint:

```text
The model can write drafts.
The model should not directly overwrite reviewed wiki pages.
```

## 4. Image Diagnosis Flow

Use this when a user uploads a grape leaf image.

```text
1. Load user image.
2. VLM performs visual intake.
3. VLM outputs side, quality, visible symptoms, candidate disease.
4. Select related wiki disease, grape leaf foundation, and workflow pages.
5. VLM performs diagnosis decision using wiki rules.
6. Validate output against diagnosis schema.
7. If evidence is insufficient, request next image.
8. If evidence is sufficient, provide provisional or confirmed result.
9. Save session state and diagnosis output.
```

Important constraint:

```text
If evidence is insufficient, the system must not present a definitive diagnosis.
```

## 5. Follow-Up Chat Flow

Use this after diagnosis.

```text
1. Receive user follow-up question.
2. Check whether question is in scope.
3. Load current diagnosis state.
4. Load selected wiki pages.
5. Answer only from image evidence, session state, and wiki knowledge.
6. If out of scope, politely redirect.
```

Allowed follow-up questions can be stored in the diagnosis JSON:

```json
[
  "Why do you need the underside?",
  "What symptoms suggest powdery mildew?",
  "How is this different from downy mildew?",
  "What image should I upload next?"
]
```

## 6. ChatGPT/Claude Development Role

Strong cloud models can be used during development to create high-quality
system behavior:

```text
write disease page drafts
generate schema examples
design prompts
suggest tool interfaces
create flow diagrams
generate eval cases
compare local model outputs
find wiki contradictions
```

This does not mean the final app must use ChatGPT or Claude.

Transferable artifacts:

```text
rules
schemas
prompts
tool interfaces
flow definitions
few-shot examples
evaluation sets
```

Not directly transferable:

```text
cloud model reasoning quality
cloud model long-context ability
cloud model JSON reliability
```

## 6.1 Frontier Agent Prototype

Use `../Frontier_model/` when the goal is to run the app flow through
interchangeable frontier providers:

```text
OpenAI / ChatGPT
Claude
Kimi / Moonshot
local Qwen baseline
```

The frontier prototype should preserve the wiki app boundaries:

```text
curated wiki remains in wiki/
model/provider docs remain in system/
schemas remain in schemas/
session and benchmark outputs stay outside curated wiki pages
provider switching stays below the agent pipeline
```

The first comparison target is not raw answer fluency. Compare:

```text
JSON parse rate
schema validity
evidence sufficiency behavior
recommended next image
latency
cost or usage metadata
human-review disagreement
```

## 7. Local Model Usage

The local model does not need to memorize all wiki content. It receives relevant
knowledge at inference time:

```text
system prompt
selected wiki page
schema
tool output
user image or question
```

If the local model does not follow instructions reliably:

```text
add schema validation
add retry prompts
split one complex task into smaller steps
add few-shot examples
fine-tune on reviewed examples
```

## 8. GitHub Storage Recommendation

Store these in GitHub:

```text
wiki/
system/
schemas/
prompts/
tools/
flows/
eval/
small examples
```

Do not put large or private data directly in GitHub:

```text
large raw images
large datasets
model checkpoints
private user uploads
API keys
cloud credentials
```

Use S3, database storage, DVC, or Git LFS for larger artifacts.

## 9. Minimal Demonstration

A good professor-facing demo is:

```text
1. Add raw powdery mildew source.
2. Generate a wiki update draft.
3. Add links to related workflow pages.
4. Check links and schema.
5. Ask a diagnosis question.
6. Show the model requests abaxial image when evidence is insufficient.
7. Show Git diff or update report.
```

This demonstrates:

```text
LLM Wiki
agentic update behavior
controlled tool use
evidence-grounded diagnosis
versionable knowledge
```
