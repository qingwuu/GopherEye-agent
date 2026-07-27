---
title: Grape Leaf Anatomy
page_type: workflow_page
review_status: draft
last_updated: 2026-07-12
sources: []
---

# Grape Leaf Anatomy

This page defines basic grape leaf structures that GopherEye should use when
describing image evidence. It is part of the visual intake foundation.

![Grape leaf anatomy diagram](../assets/grape leaf anatomy_2.png)

Image reference:

```text
image_id: grape_leaf_anatomy_001
path: wiki/assets/grape leaf anatomy_2.png
caption: Simplified grape leaf anatomy diagram labeling blade, lobes, serrated margin, petiole, midrib, primary veins, secondary veins, apex, base, adaxial surface, and abaxial surface.
purpose: Helps the assistant and human reviewers use consistent location terms during visual intake.
```

## Core Parts

Use these terms when localizing symptoms:

```text
blade / lamina
adaxial surface
abaxial surface
midrib
primary veins
secondary veins
serrated margin
lobes
leaf apex
leaf base / petiolar sinus
petiole
```

## Diagnostic Importance

GopherEye should not only say that a symptom is present. It should describe
where it appears.

Examples:

```text
chlorosis near primary veins
powdery growth on the adaxial lamina
white web-like mycelium on the abaxial surface
necrosis along the serrated margin
vein-bounded lesions between primary veins
```

Location matters because grape diseases can differ in surface, lesion geometry,
and association with veins.

## App-Facing Use

During visual intake, the assistant should extract:

```text
leaf side
visible structures
symptom locations
whether important structures are hidden or out of frame
```

For example:

```json
{
  "side_assessment": {
    "side_label": "adaxial",
    "confidence": 0.82
  },
  "visible_structures": ["blade", "primary_veins", "serrated_margin"],
  "symptom_locations": ["upper_lamina", "near_primary_veins"]
}
```

See [Leaf Surfaces](leaf_surfaces.md), [Normal Grape Leaf Variation](normal_variation.md), and [Front/Back Image Request](../workflows/front_back_request.md).
