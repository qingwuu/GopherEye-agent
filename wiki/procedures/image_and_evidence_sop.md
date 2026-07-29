---
title: Image And Evidence SOP
page_type: procedure_page
review_status: draft
last_updated: 2026-07-29
sources: []
related:
  diagnosis_sop: diagnosis_sop.md
  terminology: ../reference/terminology.md
  anatomy: ../reference/grape_leaf_anatomy.md
---

# Image And Evidence SOP

Use this procedure to decide whether an image is usable, whether one surface is
enough, and what follow-up image is needed.

## Minimum Useful Image

```text
same leaf clearly visible
relevant surface visible: adaxial or abaxial
symptomatic region in focus
enough surrounding lamina to judge pattern
primary veins visible if lesion geometry matters
lighting that does not hide symptoms
```

The goal is diagnostic visibility, not photographic neatness. Imperfect
lighting, angle, background, or partial occlusion is acceptable when the
relevant leaf surface and symptomatic area remain inspectable.

## Blocking Image Limits

Request a better image when:

```text
blur prevents symptom inspection
lighting hides surface texture
overexposure removes color details
leaf is occluded over the symptomatic region
only petiole or background is visible
the visible side is impossible to identify and side matters
lesion edge or fungal growth is out of frame
```

Do not request a better image when the limitation is nonblocking:

```text
minor shadow away from the lesion
uneven lighting that does not hide color or surface texture
partial occlusion outside the symptomatic region
background clutter not confused with leaf symptoms
slight angle if surface side and lesion geometry remain clear
```

## Surface Labels

```text
adaxial: upper surface
abaxial: lower surface
mixed: both surfaces visible in one image
uncertain: surface cannot be judged
not_leaf: image does not contain a leaf
```

Surface matters because fungal growth, vein relief, chlorosis, and sporulation
may be more visible on one side than the other.

## Single-Surface Sufficiency

Do not request the opposite leaf surface automatically. The missing surface
matters only when it changes the differential diagnosis or the disease page says
the visible surface cannot carry the decision.

One surface can be sufficient when signs are high-signal:

```text
powdery_mildew:
  superficial white-gray powdery colonies, dusty conidia, fine webby mycelium,
  or dark chasmothecia on a visible leaf surface

downy_mildew:
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

## When To Request The Opposite Surface

```text
request_abaxial_surface_same_leaf:
  only adaxial surface is available
  underside fungal growth or sporulation would change the diagnosis
  upper-surface yellowing needs underside comparison
  powdery vs downy surface evidence remains uncertain
  visible signs are generic or faint

request_adaxial_surface_same_leaf:
  only abaxial surface is available
  upper-surface lesion shape is needed
  chlorosis, halos, or vein-bounded patterns must be inspected
  underside growth is too faint or nonspecific
```

When asking for the opposite side, request the same leaf whenever possible. Do
not silently treat unrelated leaves as a front/back pair.

## Same-Leaf Pair Comparison

Compare:

```text
surface label
same or different symptom location
lesion shape on each side
presence or absence of fungal growth
strength of chlorosis or necrosis on each side
relationship to veins
whether one side explains the other
same-leaf pairing evidence or uncertainty
```

Same-leaf support can include user confirmation, matching leaf shape, similar
lesion position, matching petiole or margin shape, or reviewer confirmation.

## Next Input Vocabulary

Ask for the single most useful next input:

```text
clearer_same_view
close_up_symptomatic_area
adaxial_surface_same_leaf
abaxial_surface_same_leaf
both_sides_same_leaf
wider_leaf_context
description_of_surface_texture
```

## Request Templates

```text
abaxial request:
  Please upload the underside of the same leaf. Keep the spotted area in frame
  and keep the symptomatic area visible.

adaxial request:
  Please upload the upper side of the same leaf so I can compare the surface
  pattern with the underside evidence.

same-surface retry:
  Please upload a clearer image of the same surface and keep the symptomatic
  area in focus.

single-surface sufficient:
  This side of the leaf shows enough disease-specific evidence for a diagnosis.
  The opposite side is optional and would mainly help confirm the pattern.
```

Use [Diagnosis SOP](diagnosis_sop.md) after image sufficiency is established.
