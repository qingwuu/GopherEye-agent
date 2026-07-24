---
title: Schema Layer
page_type: schema_explanation
review_status: draft
last_updated: 2026-07-24
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
schemas/envelopes/chat_envelope.schema.json
schemas/envelopes/frontier_visual_diagnosis_envelope.schema.json
schemas/envelopes/frontier_data_management_envelope.schema.json
schemas/envelopes/frontier_chat_envelope.schema.json
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

The top-level envelope is shared, but schemas are role-specific:

```text
chat_envelope
  Basic chat response and memory update.

frontier_visual_diagnosis_envelope
  Frontier visual diagnosis response, agent trace, and visual memory fields.

frontier_data_management_envelope
  Frontier data-management response and memory update.

frontier_chat_envelope
  Frontier grape-leaf chat, knowledge-management, and general project chat.
```

## App Rule

If a model output does not satisfy the schema, the app should not silently accept
it. The app should retry, repair, or send the case to human review.

