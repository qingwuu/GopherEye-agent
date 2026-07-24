# Prompts

This folder stores reusable prompts for cloud and local models.

Prompts should not be the only place where important rules live. Stable
diagnostic rules belong in `wiki/`, and output contracts belong in `schemas/`.

## Prompt Types

```text
page_selection_prompt.md
  Ask a model to select relevant wiki pages from a catalog.

visual_intake_prompt.md
  Ask a VLM to describe user-uploaded image evidence.

diagnosis_decision_prompt.md
  Ask a VLM/LLM to combine image evidence and wiki rules.

wiki_update_prompt.md
  Ask a model to draft wiki updates from raw sources.

followup_answer_prompt.md
  Ask a model to answer controlled user follow-up questions.
```

