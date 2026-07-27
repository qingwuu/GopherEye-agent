---
title: Botanical Procedure Types
page_type: procedure_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Botanical Procedure Types

Grape leaf diagnosis uses several domain procedure types. Each type answers a
different botanical question.

## Observation Procedure

Use when the first task is to inspect the image without jumping to a disease
label.

```text
plant part
grape leaf plausibility
diagnostic visibility
leaf surface
visible anatomical structures
normal structures
abnormal signs
```

See [Visual Observation Sequence](visual_observation_sequence.md).

## Symptom Localization Procedure

Use when symptoms are visible and need to be described precisely.

```text
surface: adaxial or abaxial
blade region: apex, base, margin, interveinal area, near veins
pattern: scattered, clustered, vein-bounded, angular, marginal, widespread
appearance: chlorotic, necrotic, oil spot, powdery, webby, cottony, fuzzy,
  water-soaked, raised, sunken
```

See [Symptom Localization Procedure](symptom_localization_procedure.md).

## Surface Comparison Procedure

Use when one side of the leaf is visible but the opposite surface may contain
important evidence.

```text
identify current surface
decide whether the current single surface is already diagnostic
decide whether the opposite surface is diagnostically important
request the same leaf from the missing side when needed
compare lesion position, vein relation, and surface growth across both sides
```

See [Front/Back Leaf Process](../workflows/front_back_leaf_process.md).

## Evidence Sufficiency Procedure

Use when deciding whether the assistant has enough botanical evidence to answer.

```text
diagnostic visibility sufficient or insufficient
single surface sufficient or missing key evidence
symptom description specific or vague
differentials separated or still overlapping
next image or observation needed
```

See [Evidence Sufficiency](../workflows/evidence_sufficiency.md).

## Differential Diagnosis Procedure

Use when symptoms could fit more than one condition.

```text
candidate condition
evidence supporting it
evidence against it
evidence still missing
most useful next observation
```

See [Differential Diagnosis Procedure](differential_diagnosis_procedure.md).

## Treatment Boundary Procedure

Use when the user asks what to do after a suspected diagnosis.

```text
state diagnosis confidence
avoid management advice when diagnosis is weak
use only reviewed management resources
separate general image guidance from treatment recommendation
```

See [Treatment Resource Policy](../treatment_resources/treatment_resource_policy.md).

## Expert Review Procedure

Use when a case needs human review.

```text
visible evidence summary
provisional diagnosis
main uncertainty
missing surface or missing symptom detail
question for reviewer
reviewed conclusion
```

Expert review turns uncertain observations into reviewed knowledge or case
examples, but unreviewed observations should not become wiki truth.

See [Whole Grape Leaf Diagnosis Process](whole_diagnosis_process.md).
