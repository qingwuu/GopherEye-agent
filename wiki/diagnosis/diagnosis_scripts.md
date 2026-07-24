---
title: Diagnosis Scripts
page_type: procedure_page
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Diagnosis Scripts

Diagnosis scripts are reusable question and response patterns. They are not
code; they describe the checks an expert or app should perform.

## First-Turn Image Script

```text
Check whether the image contains a grape leaf.
Check image quality.
Identify visible side: adaxial, abaxial, mixed, uncertain, or not_leaf.
List visible symptoms and normal structures separately.
List candidate diseases conservatively.
Do not make a confirmed diagnosis before evidence sufficiency is checked.
```

## Quality Retry Script

Use when image quality is unusable:

```text
I cannot reliably inspect the leaf because the image is blurry or low
resolution. Please upload a clearer image of the same leaf surface with the
symptomatic area in focus.
```

## Front/Back Request Script

Use when the other side is required:

```text
This image shows only one side of the leaf. Please upload the other side of the
same leaf so I can compare surface symptoms before making a stronger diagnosis.
```

If the missing side is known:

```text
Please upload the underside of the same leaf.
Please upload the upper side of the same leaf.
```

## Differential Diagnosis Script

Use when symptoms overlap:

```text
This evidence could fit more than one condition. I will keep the diagnosis
provisional and compare the visible symptoms against the most likely
differentials.
```

The output should state:

```text
reason to consider each differential
reason against each differential
evidence still missing
next image or question needed
```

## Treatment Question Script

Use when the user asks what to do:

```text
I can discuss management only from reviewed treatment resources in the wiki. The
current diagnosis and selected pages do not include a reviewed treatment
resource, so I should not recommend chemical treatment here.
```

If a reviewed resource is selected, cite it and keep the diagnosis status clear.

## Expert Review Script

Use when routing a case to human review:

```text
Send the images, visual intake JSON, provisional diagnosis, evidence present,
evidence missing, and assistant uncertainty to the reviewer. Ask the reviewer to
confirm the label, explain the visual rationale, and identify any missing
front/back or treatment source requirements.
```

See [Evidence Sufficiency](../workflows/evidence_sufficiency.md),
[Front/Back Leaf Process](../workflows/front_back_leaf_process.md),
[Grape Leaf Diagnosis Dialog Tree](../dialogs/grape_leaf_diagnosis_dialog_tree.md), and
[Treatment Resource Policy](../treatment_resources/treatment_resource_policy.md).
