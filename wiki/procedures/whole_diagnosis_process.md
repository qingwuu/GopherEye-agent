---
title: Whole Diagnosis Process
page_type: procedure_page
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Whole Diagnosis Process

This procedure links the user-facing diagnosis flow with wiki pages, schemas,
raw sources, expert examples, and treatment resources.

## Procedure

```text
1. User sends a grape leaf image or question.
2. App assigns session, turn, and image IDs.
3. VLM performs visual intake.
4. Code validates visual intake JSON.
5. App selects relevant wiki pages.
6. Diagnosis step applies evidence sufficiency rules.
7. Code validates diagnosis output JSON.
8. If evidence is incomplete, ask for the exact missing image.
9. If evidence is sufficient, return provisional or confirmed diagnosis.
10. Save state for follow-up chat.
11. If user asks about management or treatment, answer only when reviewed
    treatment resource pages are selected.
12. Store unresolved expert or source gaps in the manual source backlog.
```

## Resource Links By Step

```text
Visual intake:
  wiki/grape_leaf/anatomy.md
  wiki/grape_leaf/leaf_surfaces.md
  wiki/grape_leaf/image_guidance.md
  schemas/visual_intake.schema.json
  prompts/visual_intake_prompt.md

Evidence sufficiency:
  wiki/workflows/evidence_sufficiency.md
  wiki/workflows/front_back_request.md
  wiki/workflows/front_back_leaf_process.md

Diagnosis decision:
  wiki/diagnosis/diagnosis_scripts.md
  schemas/diagnosis_output.schema.json
  prompts/diagnosis_decision_prompt.md

Dialogue:
  wiki/dialogs/grape_leaf_diagnosis_dialog_tree.md
  prompts/multiturn_chat_prompt.md

Expert examples:
  wiki/expert_information/expert_information_and_examples.md
  wiki/expert_information/case_example_structure.md
  dataset/examples/

Treatment resources:
  wiki/treatment_resources/treatment_resource_policy.md
  wiki/treatment_resources/resource_index.md

Source gaps:
  system/source_requirements/manual_source_backlog.md
  raw/sources/
```

## Output Principle

The system should keep three outputs separate:

```text
visual observations
diagnostic interpretation
management or treatment guidance
```

Visual observations can be made from the image. Diagnostic interpretation must
use selected wiki rules. Management or treatment guidance requires reviewed
treatment resources.

See [Procedure Structures](procedure_structures.md) and
[Diagnosis Scripts](../diagnosis/diagnosis_scripts.md).
