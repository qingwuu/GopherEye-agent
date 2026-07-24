# Flows

Flows define ordered procedures. They are the practical meaning of "agentic
flow" in this project.

A flow is not a free-form chatbot. A flow is a constrained sequence of steps
that may call models and tools.

## Current Flow Documents

```text
wiki_update_flow.md
  How raw sources become reviewed wiki updates.

image_diagnosis_flow.md
  How user images become structured diagnosis outputs.

followup_chat_flow.md
  How user follow-up questions are answered safely.
```

## Flow Pattern

```text
input
-> deterministic tool checks
-> model call with prompt and schema
-> validation
-> retry or human review
-> versioned output
```

## Important Constraint

The model may propose. The flow decides whether the proposal is allowed.

