---
title: Grape Leaf Surfaces
page_type: workflow_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Grape Leaf Surfaces

Leaf side is a core input to GopherEye diagnosis.

## Surface Labels

Use the same controlled vocabulary as the dataset:

```text
adaxial
abaxial
mixed
uncertain
not_leaf
```

## Adaxial Surface

The adaxial surface is the upper side of the leaf.

Visual tendencies:

```text
often smoother
often darker or glossier than the underside
main vein pattern may be visible but less raised
upper-surface chlorosis, powder, spots, or halos may be seen
```

Diagnostic examples:

```text
powdery mildew can show white-gray powdery colonies on the upper surface
downy mildew may show yellow oily-looking lesions on the upper surface
chlorosis may be easier to observe on the upper lamina
clear single-surface lesions or colonies can be diagnostically sufficient when
  disease-specific pages allow it
```

## Abaxial Surface

The abaxial surface is the lower side of the leaf.

Visual tendencies:

```text
often lighter or more matte
veins are often more raised
underside texture may be more visible
fungal growth may be easier to inspect for some diseases
```

Diagnostic examples:

```text
powdery mildew may show fine white web-like mycelium or powdery colonies
downy mildew confirmation often depends on underside sporulation
clear underside downy sporulation or powdery growth can be diagnostically
  sufficient when alternatives are addressed
raised veins and underside texture help identify side
```

## Mixed Or Uncertain

Use `mixed` when one image contains both surfaces, such as a curled or folded
leaf showing the top and underside.

Use `uncertain` when image angle, lighting, blur, or occlusion prevents reliable
side assessment.

## Required Behavior

If only one surface is visible and the selected disease page requires the other
surface for stronger diagnosis, the assistant should request the missing side.
If the selected disease page says single-surface evidence is sufficient, the
assistant should not request the missing side automatically.

See [Evidence Sufficiency](../workflows/evidence_sufficiency.md) and
[Front/Back Leaf Process](../workflows/front_back_leaf_process.md).

