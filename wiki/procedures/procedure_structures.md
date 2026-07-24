---
title: Procedure Structures
page_type: procedure_page
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Procedure Structures

Procedures can be organized in several ways. Use the structure that matches the
question being answered.

## User-Facing Procedure

Use when designing the app experience.

```text
user action
system check
system response
next user action
```

Example:

```text
upload upper side
-> system detects only adaxial evidence
-> system asks for underside of same leaf
-> user uploads underside
-> system updates diagnosis
```

## App-Facing Procedure

Use when designing prompts and validation.

```text
input payload
selected wiki pages
schema
assistant output
validator result
retry or accept
```

## Expert-Review Procedure

Use when converting expert knowledge into wiki content.

```text
raw expert note
source manifest row
draft update
reviewed wiki claim
linked example case
eval oracle
```

## Disease-Centric Procedure

Use inside disease pages.

```text
required visual evidence
front-side clues
back-side clues
differential diagnosis checks
evidence insufficiency behavior
treatment resources
```

## Treatment-Resource Procedure

Use when a user asks what to do after a diagnosis.

```text
check diagnosis status
check selected treatment pages
check review status
answer with citation or refuse to recommend
record source gap if resource is missing
```

See [Whole Diagnosis Process](whole_diagnosis_process.md),
[Treatment Resource Policy](../treatment_resources/treatment_resource_policy.md), and
[Disease Page Template](../diseases/disease_page_template.md).
