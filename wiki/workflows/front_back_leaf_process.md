---
title: Front/Back Leaf Process
page_type: workflow_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Front/Back Leaf Process

This page defines the botanical process for comparing adaxial and abaxial grape
leaf evidence.

## Why Both Sides Matter

Some signs are easier to evaluate on one surface than the other:

```text
adaxial surface:
  upper-surface chlorosis
  yellow halos
  powdery colonies
  lesion outline and distribution

abaxial surface:
  raised vein pattern
  underside fungal growth
  fuzzy or downy sporulation
  whether upper lesions correspond to underside signs
```

One surface may suggest a candidate, while the opposite surface may strengthen
or weaken that interpretation.

Both sides are not a universal prerequisite. For some cases, one surface shows
enough disease-specific evidence for diagnosis:

```text
powdery mildew:
  clear superficial powdery colonies, webby mycelium, dusty conidia, or dark
  chasmothecia on either surface

downy mildew:
  clear adaxial oil spots or angular vein-limited lesions, or clear abaxial
  white cottony/downy sporulation
```

## Comparison Sequence

```text
1. Identify the surface in the first image.
2. Describe visible symptoms on that surface.
3. Decide whether the visible single surface is already diagnostic for the
   suspected condition.
4. If not, decide whether the opposite surface is needed.
5. If needed, request the same leaf from the opposite side.
6. When both sides are available, compare lesion location and pattern.
7. Check whether symptoms align across the two surfaces.
8. Note any surface-specific fungal growth or absence of growth.
9. Update the evidence status and differential diagnosis.
```

## Same-Leaf Pair Requirement

When asking for the opposite side, request the same leaf whenever possible.
Do not silently treat two unrelated leaves as a front/back pair.

Same-leaf support can include:

```text
user confirmation
similar leaf shape
similar lesion position
matching petiole or margin shape
matching background or handling context
reviewer confirmation
```

If same-leaf pairing is uncertain, the assistant should say that comparison is
limited.

## What To Compare

Compare:

```text
surface label
same or different symptom location
lesion shape on each side
presence or absence of fungal growth
strength of chlorosis or necrosis on each side
relationship to veins
whether one side explains the other
```

## Request Language

When one side is sufficient:

```text
This side of the leaf shows enough disease-specific evidence for a diagnosis.
The opposite side is optional and would mainly help confirm the pattern.
```

If the upper surface is shown:

```text
Please upload the underside of the same leaf. Keep the spotted area in frame and
keep the symptomatic area visible.
```

If the underside is shown:

```text
Please upload the upper side of the same leaf so I can compare the surface
pattern with the underside evidence.
```

If pairing is uncertain:

```text
I can compare these images, but I cannot confirm they are the same leaf. If
possible, upload both sides of one leaf.
```

See [Front/Back Image Request](front_back_request.md),
[Evidence Sufficiency](evidence_sufficiency.md),
[Grape Leaf Surfaces](../grape_leaf/leaf_surfaces.md), and
[Symptom Localization Procedure](../procedures/symptom_localization_procedure.md).
