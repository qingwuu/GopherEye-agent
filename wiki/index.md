# GopherEye Plant Knowledge Wiki

This wiki is the curated domain knowledge layer for grape leaf diagnosis.
It should contain plant, grape leaf, disease-evidence, procedure, routine, and
reviewed resource knowledge.

## Purpose

The wiki answers app-facing questions from curated grape leaf knowledge:

```text
plant and grape leaf anatomy
leaf surface and image quality routines
diagnosis evidence sufficiency
front/back image procedure
expert case structure
treatment resource guardrails
```

System implementation details live outside `wiki/` in `system/`, `schemas/`,
`prompts/`, `tools/`, `flows/`, `Cloud_model/`, and `Frontier_model/`.

## Grape Leaf Foundation

- [Grape Leaf Anatomy](grape_leaf/anatomy.md)
- [Grape Leaf Surfaces](grape_leaf/leaf_surfaces.md)
- [Normal Grape Leaf Variation](grape_leaf/normal_variation.md)
- [Grape Leaf Image Guidance](grape_leaf/image_guidance.md)

## Diagnosis Procedures And Routines

- [Evidence Sufficiency](workflows/evidence_sufficiency.md)
- [Front/Back Image Request](workflows/front_back_request.md)
- [Front/Back Leaf Process](workflows/front_back_leaf_process.md)
- [Whole Diagnosis Process](procedures/whole_diagnosis_process.md)
- [Procedure Structures](procedures/procedure_structures.md)
- [Diagnosis Scripts](diagnosis/diagnosis_scripts.md)
- [Grape Leaf Diagnosis Dialog Tree](dialogs/grape_leaf_diagnosis_dialog_tree.md)

## Expert Knowledge And Sources

- [Expert Information And Examples](expert_information/expert_information_and_examples.md)
- [Case Example Structure](expert_information/case_example_structure.md)
- [Disease Page Template](diseases/disease_page_template.md)

## Treatment Resources

- [Treatment Resource Policy](treatment_resources/treatment_resource_policy.md)
- [Treatment Resource Index](treatment_resources/resource_index.md)
