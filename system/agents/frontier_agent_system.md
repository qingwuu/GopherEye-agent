---
title: Frontier Agent System
page_type: workflow_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Frontier Agent System

The frontier agent system is the provider-switchable app layer for GopherEye.
It routes requests, selects context, calls the configured model backend, parses
outputs, and stores session state.

Botanical diagnosis procedure does not live in this system document. It lives
in `wiki/`.

## Purpose

```text
same GopherEye app behavior
-> OpenAI / Claude / Kimi / local Qwen can be swapped by config
-> outputs can be compared on the same images and questions
-> failures become data for future prompts, evals, and review workflows
```

The implementation entry point is:

```text
Frontier_model/
```

## Agent Roles

```text
router
  Classifies the request as visual diagnosis, grape-leaf chat, knowledge
  management, data management, or general project chat.

vision_agent
  Uses attached image pixels to produce visual observations. For botanical
  diagnosis behavior, it must rely on selected wiki procedure pages.

retrieval_agent
  Selects context from the correct knowledge boundary:
    visual/grape diagnosis -> wiki/
    model/data/system questions -> system/

diagnosis_agent
  Produces conservative diagnosis output from image evidence, session memory,
  and selected wiki botanical procedure pages.

data_agent
  Explains data collection, ingestion, label review, model output auditing, and
  evaluation using system pages. It should not write unreviewed model claims
  into wiki.

chat_agent
  Handles follow-up questions using the current diagnosis state and selected
  context pages.
```

## Botanical Procedure Boundary

The frontier prompt should not hard-code detailed plant diagnostic procedure.
Instead, visual diagnosis turns should read selected wiki pages such as:

```text
wiki/procedures/whole_diagnosis_process.md
wiki/procedures/visual_observation_sequence.md
wiki/procedures/symptom_localization_procedure.md
wiki/workflows/evidence_sufficiency.md
wiki/workflows/front_back_leaf_process.md
wiki/diseases/powdery_mildew.md
wiki/diseases/downy_mildew.md
```

Code may require these page paths as core context, but the botanical reasoning
steps should remain editable in wiki.

## Provider Switching

Provider switching should happen below the agent layer:

```text
agent pipeline
-> provider registry
-> OpenAI Responses / Anthropic Messages / OpenAI-compatible Kimi / local Qwen
```

The app should not rewrite diagnosis procedure when a model changes. It should
change only the selected model profile.

## Evaluation Targets

Compare providers on:

```text
JSON parse rate
schema validity
image evidence accuracy
grape leaf / non-grape leaf handling
front/back evidence sufficiency
diagnosis conservativeness
recommended next image correctness
latency
token usage or cost metadata
human-review disagreement rate
```

## Data Loop

The system should store:

```text
raw uploaded image
image metadata
model profile and model output
selected context pages
parsed memory update
human expert correction
final accepted label
eval-case inclusion decision
```

This makes the app useful beyond chat: it becomes a data collection and
evaluation system for future one-shot, few-shot, and fine-tuning work.

## Current Implementation Boundary

`Frontier_model` is currently a prototype layer:

```text
implemented:
  provider registry
  deterministic router
  wiki/system context retrieval
  OpenAI / Claude / Kimi / local Qwen adapter structure
  JSON envelope validation, one retry, and fallback formatting
  benchmark runner
  session storage
  deterministic Data Agent CLI sidecar for capture/review/indexing

not yet implemented:
  human review UI
  persistent database
  cost dashboard
  active-learning selection
  production authentication and privacy controls
```

See [Agent Context Reading Policy](context_reading_policy.md),
[Evidence Sufficiency](../../wiki/workflows/evidence_sufficiency.md),
[Whole Grape Leaf Diagnosis Process](../../wiki/procedures/whole_diagnosis_process.md), and
[Model Choice](../models/model_choice.md).
