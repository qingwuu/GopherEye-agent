---
title: Agent Context Reading Policy
page_type: system_page
review_status: draft
last_updated: 2026-07-29
sources: []
---

# Agent Context Reading Policy

This page defines how agents should read context without moving botanical
procedure knowledge into code.

## Boundary

```text
wiki/
  Botanical grape leaf procedure, visual diagnosis routines, symptom evidence,
  front/back leaf comparison, treatment boundaries, and reviewed resources.

system/
  Router behavior, provider switching, prompt assembly, schema validation,
  memory handling, data pipeline design, and evaluation.
```

Code may reference wiki page paths, but it should not duplicate the botanical
procedure text inside frontier prompts or Python rules.

## Context Selection By Request Type

```text
visual diagnosis request:
  read wiki botanical procedure pages
  read relevant grape leaf anatomy, surface, and symptom pages
  include image manifest and session memory

grape leaf chat request:
  read wiki pages relevant to the botanical question
  include recent diagnosis memory when available

data ingestion or label workflow request:
  read system data, agent, schema, and source-intake pages
  do not treat system pages as botanical truth

model/provider/router request:
  read system model and agent pages
  do not mix provider details into wiki

knowledge update request:
  read selected wiki target pages
  edit wiki directly for simple updates
  use raw/source-intake workflow only when provenance or review is needed
```

## Core Wiki Pages For Visual Diagnosis

For image-based diagnosis, the retrieval layer should prefer these botanical
procedure pages:

```text
wiki/procedures/diagnosis_sop.md
wiki/procedures/image_and_evidence_sop.md
wiki/disease/powdery_mildew/index.md
wiki/disease/downy_mildew/index.md
wiki/disease/healthy/index.md
wiki/disease/others/index.md
```

Additional pages should be selected by the current question and image context,
for example reference terminology, grape leaf anatomy, treatment pages, or
newly promoted disease pages.

## Prompt Assembly Principle

The prompt builder may say:

```text
Use the selected wiki botanical procedure pages.
Do not invent facts outside selected pages and image evidence.
```

The prompt builder should not restate detailed botanical procedure steps such
as lesion sequence, front/back comparison logic, or disease-specific evidence.
Those details belong in `wiki/`.

## Future Agent Routing

The current deterministic router can later become hybrid:

```text
Python hard rules
-> optional LLM router for ambiguous requests
-> context selector
-> prompt builder
-> validator
```

Even after that upgrade, the source boundary remains the same:

```text
LLM decides which role/context is needed.
Python assembles allowed context.
Botanical procedure comes from wiki pages.
System behavior comes from system pages.
```

See [Frontier Agent System](frontier_agent_system.md) and
[Dataset Memory Direction](../data/dataset_memory.md).
