# GopherEye Wiki App Architecture

The root-level wiki app separates project knowledge from executable control
logic. The goal is to make the system understandable, auditable, and portable
across strong cloud models and local models.

## Layered Design

```text
raw/
  Source evidence. Meeting notes, papers, raw disease documents, raw images.
  Raw files are preserved and should not be treated as final curated knowledge.

wiki/
  Curated domain knowledge. Plant, grape leaf, disease-evidence, diagnosis
  procedure, routine, expert case, and reviewed treatment-resource pages.

system/
  Implementation-facing documentation. Model choice, provider switching,
  agent architecture, schema/tool layer explanations, source ingestion, data
  memory, and evaluation strategy.

schemas/
  Machine-readable contracts. JSON schemas for diagnosis outputs, visual intake
  outputs, wiki update proposals, and flow logs.

prompts/
  Reusable model instructions. These can be used by ChatGPT, Claude, Qwen, or
  another local/cloud model.

tools/
  Deterministic actions. File reading, wiki search, link checking, JSON
  validation, GitHub operations, image loading, database access.

flows/
  Ordered procedures. Wiki update flow, image diagnosis flow, and follow-up chat
  flow. A flow decides when to call a model and when to call tools.

eval/
  Behavior tests. Questions, expected outputs, failure cases, and regression
  checks for the wiki system.

Frontier_model/
  Provider-switchable frontier model orchestration and benchmark code.

Cloud_model/
  OpenAI-only cloud comparison runner retained for parallel testing.

BLIP-Qwen/
  Local model training, historical GopherEye code, configs, and demo assets.
```

## Model Role

The model is a reasoning engine, not the only source of truth.

```text
model
  reads selected wiki pages
  reads schemas and prompts
  reasons over image/text evidence
  proposes outputs

tools/code
  enforce schema
  read files
  check links
  store outputs
  gate write operations
```

## Knowledge Types

```text
Train-time knowledge:
  Learned model ability, especially visual recognition and instruction following.

External wiki knowledge:
  Updatable diagnostic criteria, evidence sufficiency rules, workflows, and
  project decisions.
```

The system should not train every wiki page into the local model by default.
Instead, the local model receives relevant wiki content at inference time.

## Development Strategy

Use strong models such as ChatGPT or Claude to develop:

```text
rules
schemas
prompts
tool interfaces
agentic flows
high-quality examples
evaluation cases
```

Then test whether a local model can follow the same rules and flows. If the
local model fails, improve the prompt, simplify the flow, add validation, or
fine-tune on reviewed examples.
