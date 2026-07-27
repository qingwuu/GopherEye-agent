---
title: Evidence Sufficiency
page_type: workflow_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Evidence Sufficiency

Evidence sufficiency means deciding whether the visible botanical evidence is
enough for a useful diagnosis, or whether another image or observation is
needed.

## Core Rule

Do not give a definitive diagnosis when key botanical evidence is missing.
Do not treat a missing opposite leaf surface as missing evidence by default.
The missing surface matters only when it changes the differential diagnosis or
the disease-specific page says the visible surface cannot carry the decision.

Evidence may be insufficient because:

```text
the image does not show a leaf
the leaf is not clearly a grape leaf
the symptomatic area cannot be inspected
the visible surface is uncertain
only one surface is available and surface comparison matters for this specific case
symptoms are too vague to separate disease from normal variation
fungal growth is suspected but not visible enough to describe
lesion geometry or vein relationship cannot be inspected
```

Lighting, shadows, angle, and partial occlusion are evidence limits only when
they prevent inspection of the relevant leaf surface, lesion edge, surface
growth, or vein relationship.

## Sufficient For Observation

Evidence is sufficient for observation when the assistant can describe:

```text
leaf or non-leaf status
image quality
visible surface, or why surface is uncertain
visible structures
visible abnormal signs, if any
normal features that should not be over-read
```

Observation sufficiency does not automatically mean diagnostic sufficiency.

## Sufficient For Provisional Diagnosis

Evidence may support a provisional diagnosis when:

```text
the image is clear enough
the visible surface is known, or surface identity is not essential for the candidate
abnormal signs are localized and described
at least one candidate disease has supporting evidence
important alternatives are considered
missing evidence is stated
```

Use provisional language when the opposite leaf surface, close-up detail, or
human confirmation is still needed.

## Sufficient From One Surface

One surface can be diagnostically sufficient when the visible signs are
high-signal and surface-specific.

```text
powdery mildew:
  superficial white-gray powdery colonies, dusty conidia, fine webby mycelium,
  or dark chasmothecia on a visible leaf surface

downy mildew:
  adaxial oil spots, angular vein-limited yellow-to-brown lesions, or abaxial
  white cottony/downy sporulation
```

When one surface is sufficient:

```text
evidence_sufficiency: sufficient_single_surface
recommended_next_image: none
single_surface_decision: diagnostic
opposite_surface_role: not_needed or optional_confirmation
```

Do not request the opposite side only to make the app workflow symmetrical.
Request it when the visible signs are weak, generic, hidden, or confusable.

## Stronger Diagnostic Evidence

Stronger evidence usually requires:

```text
clear image of the symptomatic area
surface-specific signs
front/back comparison when needed for this differential
lesion shape and distribution
relationship to veins
comparison against normal variation and likely alternatives
```

Do not treat a single generic symptom, such as yellowing or brown spots, as
enough for a strong diagnosis.

## Common Missing Evidence Requests

Ask for the most useful next input:

```text
clearer_same_view
close_up_symptomatic_area
adaxial_surface_same_leaf
abaxial_surface_same_leaf
both_sides_same_leaf
wider_leaf_context
description_of_surface_texture
```

## Example: Upper Surface Only

If only the adaxial side is visible and the image shows pale spots or powdery
growth, the assistant should decide whether the visible signs are diagnostic.
Clear superficial white-gray powdery colonies can support powdery mildew from
that single surface. Clear oil spots or angular vein-limited lesions can support
downy mildew from that single surface. If the signs are faint, generic, or
cannot separate powdery mildew from downy mildew or non-disease artifacts,
request the abaxial surface of the same leaf.

See [Front/Back Image Request](front_back_request.md),
[Front/Back Leaf Process](front_back_leaf_process.md),
[Visual Observation Sequence](../procedures/visual_observation_sequence.md), and
[Differential Diagnosis Procedure](../procedures/differential_diagnosis_procedure.md).
