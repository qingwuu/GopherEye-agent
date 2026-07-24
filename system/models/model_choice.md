---
title: Model Choice
page_type: model_page
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Model Choice

The root-level wiki app is designed to compare simple single-model wiki
behavior with larger or more specialized systems.

## Recommended Roles

```text
local instruction model:
  page selection, wiki Q&A, draft updates, lightweight follow-up chat

vision-language model:
  visual intake from uploaded images
  multi-turn image comparison when image pixels are attached

strong cloud model during development:
  teacher examples, draft wiki structure, eval oracle generation, contradiction
  checks, and prompt debugging

frontier model in the app:
  high-quality visual intake, multi-turn diagnosis, data-ingestion guidance,
  and provider comparison
```

## Selection Rule

Prefer the smallest model that reliably follows:

```text
selected wiki context only
schema-constrained JSON output
conservative diagnosis status
front/back evidence rules
treatment guardrails
```

## Failure Handling

If a model fails, improve the system in this order:

```text
schema validation
retry prompt
smaller task split
more reviewed examples
better wiki page selection
fine-tuning on reviewed cases
larger or stronger model
```

See [Single-Model Workflow](../workflows/single_model_workflow.md),
[Frontier Agent System](../agents/frontier_agent_system.md),
[Schema Layer](../contracts/schema_layer.md), and
[Tool Layer](../tools/tool_layer.md).
