---
title: Schema Layer
page_type: schema_explanation
review_status: draft
last_updated: 2026-07-12
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
schemas/wiki_update_proposal.schema.json
schemas/wiki_frontmatter.schema.json
schemas/flow_run.schema.json
```

## App Rule

If a model output does not satisfy the schema, the app should not silently accept
it. The app should retry, repair, or send the case to human review.

