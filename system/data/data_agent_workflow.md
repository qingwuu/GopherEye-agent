---
title: Data Agent Workflow
page_type: system_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Data Agent Workflow

The first Data Agent implementation is a deterministic Python sidecar around
existing sessions. It does not replace the router, prompt builder, chat agent,
vision agent, or diagnosis agent.

## Reuse Boundary

```text
reused:
  route_task
  build_frontier_prompt
  frontier provider call
  vision / diagnosis model output
  JSON envelope validation
  session memory

new:
  per-instance data folders
  upload records
  machine_generated / unreviewed model_label files
  human_review.template.json
  human_review.submitted.json import
  reviewed dataset index
```

The existing agents keep their app-facing behavior. Data Agent reads their
stored outputs after the turn is complete.

## Write Boundary

The Data Agent can write to:

```text
data_agent/instances/
data_agent/uploads/
data_agent/indexes/
data_agent/review_queue/
```

It must not write to:

```text
wiki/
```

Unreviewed model claims stay in `model_label.json` with:

```text
generation_status = machine_generated
review_status = unreviewed
is_ground_truth = false
```

Human-reviewed labels become ground truth only after import:

```text
human_review.submitted.json
-> reviewed_dataset_index.jsonl
```

Only `accept_model_label` and `correct_label` enter the reviewed dataset index.
`needs_more_evidence`, `reject_not_leaf`, and `reject_unusable_image` remain
recorded but are not ground-truth disease labels.

## Evidence Insufficiency

Evidence-insufficient cases are still first-class data. They support:

```text
review queue triage
missing-image analysis
front/back request improvement
active-learning selection
future data collection planning
```

They do not become wiki knowledge or final training labels without human
review.

## Single-Surface Sufficient Labels

Some machine-generated labels may be supported by one visible leaf surface when
the disease-specific evidence is high-signal. Store these separately from
insufficient cases so later review can distinguish:

```text
single_surface_sufficient_label:
  one visible side contains enough evidence for a diagnosis
  opposite side may be optional confirmation
  missing side is not automatically treated as a data defect

insufficient_evidence:
  the visible evidence cannot separate likely differentials
  the next needed image or observation should be explicit
```

## Human Review V1

The first review workflow is file based:

```text
1. capture-turn creates one instance folder.
2. Human copies human_review.template.json to human_review.submitted.json.
3. Human edits review_status, reviewer, reviewed_at, decision, and label fields.
4. import-review validates and imports the submitted JSON.
5. build-reviewed-index exports reviewed ground-truth records.
```

This can later be replaced by a web UI while keeping the same schema contracts.
