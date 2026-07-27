---
title: Grape Leaf Diagnosis Dialog Tree
page_type: dialog_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Grape Leaf Diagnosis Dialog Tree

The dialog tree controls what the assistant should ask or answer during
multi-turn grape leaf diagnosis.

## Main States

```text
start
not_leaf
poor_quality
side_uncertain
only_adaxial
only_abaxial
both_sides_available
diagnosis_provisional
diagnosis_confirmed
treatment_question
expert_review_needed
follow_up
```

## State Rules

| State                  | Condition                                                      | Assistant action                                                                             | Linked resources                                                                   |
| ---------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `not_leaf`             | Image does not contain a grape leaf                            | Ask for a grape leaf image                                                                   | [Visual Observation Sequence](../procedures/visual_observation_sequence.md)        |
| `poor_quality`         | Blur, darkness, occlusion, or low resolution blocks inspection | Ask for clearer same view                                                                    | [Evidence Sufficiency](../workflows/evidence_sufficiency.md)                       |
| `side_uncertain`       | Side cannot be identified                                      | Ask for a clearer image or both sides                                                        | [Grape Leaf Surfaces](../grape_leaf/leaf_surfaces.md)                              |
| `only_adaxial`         | Upper side only                                                | Diagnose from one side when evidence is sufficient, otherwise request underside when needed  | [Front/Back Image Request](../workflows/front_back_request.md)                     |
| `only_abaxial`         | Lower side only                                                | Diagnose from one side when evidence is sufficient, otherwise request upper side when needed | [Front/Back Leaf Process](../workflows/front_back_leaf_process.md)                 |
| `both_sides_available` | Same-leaf pair is available                                    | Compare evidence and update diagnosis                                                        | [Front/Back Leaf Process](../workflows/front_back_leaf_process.md)                 |
| `treatment_question`   | User asks what to do                                           | Answer only from reviewed treatment resources                                                | [Treatment Resource Policy](../treatment_resources/treatment_resource_policy.md)   |
| `expert_review_needed` | Assistant uncertainty remains high or source gap blocks answer | Send structured case to review                                                               | [Manual Source Backlog](../../system/source_requirements/manual_source_backlog.md) |

## Transition Sketch

```text
start
-> not_leaf
-> poor_quality
-> side_uncertain
-> only_adaxial
   -> diagnosis_provisional or diagnosis_confirmed when single-surface evidence is sufficient
   -> request abaxial only when needed
   -> both_sides_available
   -> diagnosis_provisional
-> only_abaxial
   -> diagnosis_provisional or diagnosis_confirmed when single-surface evidence is sufficient
   -> request adaxial only when needed
   -> both_sides_available
   -> diagnosis_provisional
-> both_sides_available
   -> diagnosis_provisional
   -> diagnosis_confirmed
-> treatment_question
   -> reviewed treatment answer
   -> source gap response
-> follow_up
```

## Allowed Follow-Up Categories

```text
why another image is needed
what evidence supports the diagnosis
how this differs from a likely confusion disease
what image to upload next
what information is missing
what reviewed management resources are available
```

See [Diagnosis Scripts](../diagnosis/diagnosis_scripts.md),
[Whole Grape Leaf Diagnosis Process](../procedures/whole_diagnosis_process.md),
[Symptom Localization Procedure](../procedures/symptom_localization_procedure.md), and
[Differential Diagnosis Procedure](../procedures/differential_diagnosis_procedure.md).
