---
title: Diagnosis SOP
page_type: procedure_page
review_status: draft
last_updated: 2026-07-29
sources: []
related:
  image_evidence_sop: image_and_evidence_sop.md
  terminology: ../reference/terminology.md
  anatomy: ../reference/grape_leaf_anatomy.md
  source_policy: ../reference/source_policy.md
---

# Diagnosis SOP

Use this procedure before naming a grape leaf disease.

## Diagnostic Order

```text
1. Confirm that the visible plant part is a leaf.
2. Check whether the leaf is plausibly a grape leaf.
3. Check diagnostic visibility for the symptomatic area.
4. Identify the visible surface: adaxial, abaxial, mixed, uncertain, or not_leaf.
5. Locate visible structures: blade, margin, midrib, primary veins, secondary
   veins, petiole, apex, and base when visible.
6. Separate normal grape leaf structures from abnormal signs.
7. Describe abnormal signs without naming a disease too early.
8. Compare signs against disease-specific evidence requirements.
9. Decide evidence status.
10. If evidence is missing, request the single most useful next image or note.
11. Keep treatment separate unless reviewed treatment resources are available.
```

## Observation Before Interpretation

Record what is visible before choosing a disease label:

```text
leaf or non-leaf status
grape leaf plausibility
image quality limits
leaf surface
visible structures
surface texture
color changes
fungal growth or lack of fungal growth
lesion shape and edge
relationship to veins
distribution across the blade
normal features that should not be over-read
evidence still missing
```

Use [Grape Leaf Anatomy](../reference/grape_leaf_anatomy.md) and
[Terminology](../reference/terminology.md) for controlled vocabulary.

## Differential Frame

For each candidate, compare:

```text
evidence supporting the candidate
evidence arguing against the candidate
evidence still missing
most useful next observation
```

Prioritize these canonical disease pages:

```text
powdery_mildew: ../disease/powdery_mildew/index.md
downy_mildew: ../disease/downy_mildew/index.md
healthy_or_normal_variation: ../disease/healthy/index.md
other_or_unresolved: ../disease/others/index.md
```

Do not treat generic yellowing, brown spots, normal vein contrast, glare, dust,
or mechanical tearing as enough for a strong disease diagnosis by themselves.

## Evidence Status

Use conservative status language:

```text
not_leaf
not_enough_image_quality
insufficient_botanical_evidence
provisional_diagnosis
strong_provisional_diagnosis
reviewed_or_confirmed_diagnosis
```

A confirmed diagnosis should not be claimed from weak image evidence. A single
surface is not automatically weak when it contains high-signal
disease-specific evidence.

## Dialog States

```text
start:
  perform observation pass

not_leaf:
  ask for a grape leaf image

poor_quality:
  ask for a clearer same view

side_uncertain:
  ask for a clearer image or both sides if side matters

only_adaxial:
  diagnose from one side when evidence is sufficient
  otherwise request underside of the same leaf when needed

only_abaxial:
  diagnose from one side when evidence is sufficient
  otherwise request upper side of the same leaf when needed

both_sides_available:
  compare lesion location, surface growth, vein relationship, and alignment

treatment_question:
  open the matching treatment page and follow source policy

expert_review_needed:
  summarize visible evidence, provisional label, uncertainty, and missing input
```

## Response Scripts

```text
first_image:
  First I will check whether this is a grape leaf, whether the image is clear
  enough, which leaf surface is visible, and what symptoms are actually visible.

missing_surface:
  This image shows only one side of the leaf. Please upload the other side of
  the same leaf so I can compare surface symptoms before making a stronger
  diagnosis.

single_surface_sufficient:
  This side of the leaf shows enough specific evidence for a diagnosis. The
  opposite side could help confirm the pattern, but it is not required for this
  assessment.

differential_overlap:
  This evidence could fit more than one condition. I will keep the diagnosis
  provisional and compare the visible symptoms against the most likely
  differentials.

not_enough_evidence:
  I cannot make a reliable disease diagnosis from this evidence alone. The main
  missing evidence is: [specific missing evidence]. The most useful next image
  is: [specific next image].
```

## Treatment Boundary

Treatment and management advice must come from the matching treatment page:

```text
../treatment/powdery_mildew.md
../treatment/downy_mildew.md
../treatment/healthy_or_normal_variation.md
../treatment/others.md
```

Follow [Source Policy](../reference/source_policy.md) for reviewed resource
requirements.
