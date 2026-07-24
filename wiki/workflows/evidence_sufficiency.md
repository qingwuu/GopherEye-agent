---
title: Evidence Sufficiency
page_type: workflow_page
review_status: draft
last_updated: 2026-07-24
sources: []
---

# Evidence Sufficiency

Evidence sufficiency means deciding whether the visible botanical evidence is
enough for a useful diagnosis, or whether another image or observation is
needed.

## Core Rule

Do not give a definitive diagnosis when key botanical evidence is missing.

Evidence may be insufficient because:

```text
the image does not show a leaf
the leaf is not clearly a grape leaf
the symptomatic area is blurry or poorly lit
the visible surface is uncertain
only one surface is available when surface comparison matters
symptoms are too vague to separate disease from normal variation
fungal growth is suspected but not visible enough to describe
lesion geometry or vein relationship cannot be inspected
```

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
the visible surface is known or not essential for the candidate
abnormal signs are localized and described
at least one candidate disease has supporting evidence
important alternatives are considered
missing evidence is stated
```

Use provisional language when the opposite leaf surface, close-up detail, or
human confirmation is still needed.

## Stronger Diagnostic Evidence

Stronger evidence usually requires:

```text
clear image of the symptomatic area
surface-specific signs
front/back comparison when needed
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
adaxial_surface_same_leaf
abaxial_surface_same_leaf
both_sides_same_leaf
close_up_symptomatic_area
wider_leaf_context
description_of_surface_texture
```

## Example: Upper Surface Only

If only the adaxial side is visible and the image shows pale spots or powdery
growth, the assistant may describe those signs and give a provisional
comparison. If underside evidence is needed to distinguish likely candidates,
request the abaxial surface of the same leaf.

See [Front/Back Image Request](front_back_request.md),
[Front/Back Leaf Process](front_back_leaf_process.md),
[Visual Observation Sequence](../procedures/visual_observation_sequence.md), and
[Differential Diagnosis Procedure](../procedures/differential_diagnosis_procedure.md).
