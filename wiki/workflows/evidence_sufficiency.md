---
title: Evidence Sufficiency
page_type: workflow_page
review_status: draft
last_updated: 2026-07-12
sources: []
---

# Evidence Sufficiency

Evidence sufficiency determines whether GopherEye has enough visual information
to provide a diagnosis or whether it should request more input.

## Core Rule

The system should not give a definitive diagnosis if key evidence is missing.

For grape leaf diagnosis, missing evidence may include:

```text
missing adaxial image
missing abaxial image
unclear leaf side
poor image quality
only vague symptoms
no visible fungal sign
```

## Output Labels

Use these labels in app-facing outputs:

```text
sufficient
insufficient_need_adaxial
insufficient_need_abaxial
insufficient_need_better_quality
uncertain
```

## Powdery Mildew Example

If a user uploads only the adaxial side and the image shows pale yellow spots
with faint white-gray powder, the system may provide a provisional diagnosis of
possible powdery mildew.

However, if abaxial evidence is needed to strengthen the diagnosis, the system
should request:

```text
abaxial_surface_same_leaf
```

See [Front/Back Image Request](front_back_request.md),
[Front/Back Leaf Process](front_back_leaf_process.md), and
[Grape Leaf Diagnosis Dialog Tree](../dialogs/grape_leaf_diagnosis_dialog_tree.md).

