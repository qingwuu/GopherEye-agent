---
title: Front/Back Image Request
page_type: workflow_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Front/Back Image Request

Requesting the opposite leaf surface is a diagnostic action. It should be tied
to a clear botanical uncertainty.

## Leaf Side Labels

```text
adaxial
abaxial
mixed
uncertain
not_leaf
```

## Request The Abaxial Side When

```text
only the adaxial surface is available
underside fungal growth or sporulation would change the diagnosis
upper-surface yellowing needs underside comparison
powdery vs downy surface evidence remains uncertain
lesion alignment across surfaces would strengthen the diagnosis
visible signs are generic or faint and the selected disease page does not allow
  single-surface diagnosis
```

Do not request the abaxial side when clear adaxial powdery mildew colonies,
high-signal downy mildew oil spots, or other disease-specific single-surface
evidence already makes the diagnosis sufficient.

## Request The Adaxial Side When

```text
only the abaxial surface is available
upper-surface lesion shape is needed
chlorosis, halos, or vein-bounded patterns must be inspected
the underside image shows growth but upper lesion context is missing
visible underside growth is too faint or nonspecific to separate likely diseases
```

Do not request the adaxial side when clear abaxial downy sporulation or clear
powdery mildew surface growth is already sufficient for the current diagnostic
decision.

## Request A Clearer Same View When

```text
the symptomatic area is blurry
lighting hides surface texture
the leaf is overexposed
the lesion edge is out of frame
the surface label cannot be judged
```

Do not request a clearer image for lighting, shadow, angle, or partial occlusion
when the relevant leaf symptoms, surface growth, lesion geometry, and vein
relationship remain inspectable.

## Avoid Unnecessary Requests

Do not request both sides automatically. Ask for the opposite surface only when
it would resolve a diagnostic uncertainty or improve comparison against likely
differentials.

Accept a single-surface diagnosis when the selected disease page says the
visible signs are high-signal enough. In that case, set the next image to
`none` or leave it null rather than asking for the other side as a formality.

## User-Facing Language

Use concise language:

```text
This image shows one side of the leaf. I need the underside of the same leaf to
check whether the visible spots correspond to underside growth before making a
stronger diagnosis.
```

See [Evidence Sufficiency](evidence_sufficiency.md) and
[Front/Back Leaf Process](front_back_leaf_process.md).
