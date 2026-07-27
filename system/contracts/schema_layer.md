---
title: Schema Layer
page_type: schema_explanation
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Schema Layer

Schemas define the machine-readable contracts that model outputs must follow.

## Why Schemas Are Separate From Wiki Text

Wiki pages are written for humans and models to read. JSON schemas are written
for programs to validate.

This separation allows:

```text
clear app contracts
automatic validation
retry when model output is invalid
consistent dataset fields
easier debugging
```

## Important Schemas

```text
schemas/visual_intake.schema.json
schemas/diagnosis_output.schema.json
schemas/envelopes/assistant_envelope.schema.json
schemas/base/known_image_update.schema.json
schemas/base/memory_update.schema.json
schemas/wiki_update_proposal.schema.json
schemas/wiki_frontmatter.schema.json
schemas/flow_run.schema.json
```

## Assistant Envelope Pattern

User-facing text and session memory must stay separate:

```text
assistant_message
  Natural language shown to the user.

memory_update
  Structured session memory consumed by app code.
```

The current runtime uses one thin top-level envelope:

```text
assistant_envelope
  assistant_message
  memory_update
```

Role profiles decide which payload fields and base schemas are required:

```text
chat
  assistant_envelope + memory_update

frontier_visual_intake_or_diagnosis
  assistant_envelope + memory_update
  visual_intakes must satisfy schemas/visual_intake.schema.json
  visual_intakes must use image_order, not image_id or image_path

frontier_data_management
  assistant_envelope + memory_update
  app code forbids direct wiki or ground-truth writes

frontier_grape_leaf_chat / frontier_knowledge_management / frontier_general_project_chat
  assistant_envelope + memory_update
```

Route, selected agent path, context label, selected pages, and tool/runtime trace
are code-owned turn metadata stored outside the model-owned JSON envelope.

The older role-specific envelope schema files have been removed.
Role-specific requirements now live in runtime validation code.

## Thin Envelope, Strong Payloads

The envelope should stay thin. Domain detail belongs in base schemas:

```text
schemas/visual_intake.schema.json
  visual observation payload used inside memory_update.visual_intakes.

schemas/diagnosis_output.schema.json
  diagnosis status, single-surface sufficiency, next-image, and differential
  diagnosis contract for diagnosis-specific outputs and future exports.

schemas/base/memory_update.schema.json
  session memory payload, including optional evidence_sufficiency,
  single_surface_assessment, and nonblocking_image_limitations.

schemas/data_agent/*.schema.json
  deterministic data pipeline records, human review, and reviewed dataset index.
```

This prevents the assistant envelope from becoming a duplicate diagnosis schema.
The role profile decides which base schemas apply to the current task.

## App Rule

If a model output does not satisfy the schema, the app should not silently accept
it. The app should retry, repair, or send the case to human review.
