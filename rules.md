# GopherEye Wiki App Rules

This repository is organized as a wiki app plus model-comparison workspace.

## Core Rule

Keep the app-facing knowledge and model-training code separate:

```text
wiki app:
  wiki/
  system/
  schemas/
  prompts/
  tools/
  flows/
  eval/
  dataset/
  Cloud_model/
  Frontier_model/

local model and training code:
  BLIP-Qwen/
```

## Directory Rules

```text
raw/
  Original sources. Do not edit after ingestion.

wiki/
  Curated plant, grape leaf, diagnosis routine, expert case, and treatment
  resource knowledge.

system/
  Model, provider, agent, schema/tool, source-ingestion, data, and workflow
  implementation documentation.

schemas/
  Machine-readable output contracts.

prompts/
  Reusable model instructions.

tools/
  Deterministic operations that code can execute.

flows/
  Ordered workflows that combine models, tools, schemas, and human review.

eval/
  Regression cases and expected behaviors.

catalog/
  Lightweight generated file catalog. It can be rebuilt.

draft_updates/
  Model-generated update drafts waiting for human review.
```

## Separation Rules

```text
Domain diagnostic rules and grape leaf routines belong in wiki/.
Model/provider/system architecture belongs in system/.
Machine-readable contracts belong in schemas/.
Reusable model instructions belong in prompts/.
Executable actions belong in tools/.
Step-by-step procedures belong in flows/.
Behavior tests belong in eval/.
Model training code belongs in BLIP-Qwen/.
```

Important:

```text
Wiki documents rules.
Code and schemas enforce rules.
The model proposes.
Tools and flows decide what is allowed.
```

## Human Review

Model-generated drafts should not be automatically copied into `wiki/`. Review
them first, especially for scientific claims, model performance numbers, disease
descriptions, and PI decisions.

## Secrets

Do not store API keys, cloud credentials, or private tokens in this repository.
