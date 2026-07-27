---
title: Whole Grape Leaf Diagnosis Process
page_type: procedure_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Whole Grape Leaf Diagnosis Process

This procedure describes the botanical reasoning sequence for grape leaf image
diagnosis. It is a domain procedure, not an implementation workflow.

## Diagnostic Order

Use this order before naming a disease:

```text
1. Confirm that the visible plant part is a leaf.
2. Check whether the leaf is plausibly a grape leaf.
3. Check whether diagnostic visibility allows inspection of the symptomatic area.
4. Identify the visible surface: adaxial, abaxial, mixed, uncertain, or not_leaf.
5. Locate visible structures: blade, margin, midrib, primary veins, secondary
   veins, petiole, apex, and base when visible.
6. Separate normal grape leaf structures from abnormal signs.
7. Describe abnormal signs without naming a disease too early.
8. Compare the signs against disease-specific evidence requirements.
9. Decide whether evidence is insufficient, sufficient from one surface,
   provisional, or strong enough for a more confident diagnosis.
10. If evidence is missing, request the most useful next image or observation.
11. Keep management or treatment advice separate from diagnosis unless reviewed
    treatment resources are available.
```

## Observation Before Interpretation

The first pass should be descriptive. Record what is visible:

```text
leaf side
image quality limits
nonblocking image limitations
surface texture
color changes
fungal growth or lack of fungal growth
lesion shape and edge
relationship to veins
distribution across the blade
whether symptoms are local, scattered, vein-bounded, marginal, or widespread
```

Only after this observation pass should the assistant compare findings against
candidate diseases.

## Evidence Status

Use conservative diagnostic status language:

```text
not_leaf
not_enough_image_quality
insufficient_botanical_evidence
provisional_diagnosis
strong_provisional_diagnosis
reviewed_or_confirmed_diagnosis
```

A confirmed diagnosis should not be claimed from one weak image. Many grape leaf
diseases need surface-specific evidence, lesion pattern, and differential
comparison.

One image is not automatically weak just because it shows one side. A single
surface can be sufficient when it shows high-signal disease-specific features
such as powdery mildew colonies, webby mycelium, chasmothecia, downy mildew oil
spots, angular vein-limited lesions, or underside cottony sporulation.

## Missing Evidence

When evidence is incomplete, ask for the single most useful next input:

```text
clearer image of the same surface
close-up of the symptomatic area
adaxial surface of the same leaf
abaxial surface of the same leaf
wider image showing distribution across the leaf
image of another symptomatic leaf on the same plant
human note about whether spots are powdery, fuzzy, raised, wet, dry, or necrotic
```

Do not ask broad lists of questions when one image would resolve the main
uncertainty.

## Resource Links By Diagnostic Need

```text
Observation sequence:
  wiki/procedures/visual_observation_sequence.md

Symptom localization:
  wiki/procedures/symptom_localization_procedure.md
  wiki/grape_leaf/anatomy.md
  wiki/grape_leaf/leaf_surfaces.md
  wiki/grape_leaf/normal_variation.md

Evidence sufficiency:
  wiki/workflows/evidence_sufficiency.md
  wiki/workflows/front_back_request.md
  wiki/workflows/front_back_leaf_process.md

Differential diagnosis:
  wiki/procedures/differential_diagnosis_procedure.md
  wiki/diagnosis/diagnosis_scripts.md
  wiki/diseases/disease_page_template.md

Treatment boundary:
  wiki/treatment_resources/treatment_resource_policy.md
  wiki/treatment_resources/resource_index.md
```

See [Visual Observation Sequence](visual_observation_sequence.md),
[Symptom Localization Procedure](symptom_localization_procedure.md),
[Differential Diagnosis Procedure](differential_diagnosis_procedure.md), and
[Evidence Sufficiency](../workflows/evidence_sufficiency.md).
