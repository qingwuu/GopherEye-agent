---
title: Frontier Agent System
page_type: workflow_page
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Frontier Agent System

The frontier agent system is the app-facing evolution of the root-level wiki app.
It keeps the curated wiki, schemas, prompts, and session memory, but makes the
model backend interchangeable.

## Purpose

```text
same GopherEye app behavior
-> OpenAI / Claude / Kimi / local Qwen can be swapped by config
-> outputs can be compared on the same images and questions
-> failures become data for future prompts, evals, and fine-tuning
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
  Inspects attached image pixels, checks whether the image is a leaf, assesses
  image quality, estimates leaf side, and extracts visible symptoms.

retrieval_agent
  Selects relevant `wiki/` pages for the current request.

diagnosis_agent
  Produces conservative diagnosis output from image evidence, session memory,
  selected wiki pages, and schemas.

data_agent
  Explains and records data collection, data ingestion, label review, model
  output auditing, and evaluation needs.

chat_agent
  Handles follow-up questions from the current diagnosis state and selected
  wiki pages.
```

## Provider Switching

Provider switching should happen below the agent layer:

```text
agent pipeline
-> provider registry
-> OpenAI Responses / Anthropic Messages / OpenAI-compatible Kimi / local Qwen
```

The app should not rewrite diagnosis logic when a model changes. It should
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
selected wiki pages
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
  reusable wiki retrieval
  OpenAI / Claude / Kimi / local Qwen adapter structure
  benchmark runner
  session storage

not yet implemented:
  strict JSON Schema validation in the frontier runner
  human review UI
  persistent database
  cost dashboard
  active-learning selection
  production authentication and privacy controls
```

See [Evidence Sufficiency](../../wiki/workflows/evidence_sufficiency.md),
[Whole Diagnosis Process](../../wiki/procedures/whole_diagnosis_process.md), and
[Model Choice](../models/model_choice.md).
