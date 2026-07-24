---
title: Normal Grape Leaf Variation
page_type: workflow_page
review_status: draft
last_updated: 2026-07-12
sources: []
---

# Normal Grape Leaf Variation

GopherEye should separate normal leaf variation from disease evidence.

## Normal Structures

The following are usually normal grape leaf features:

```text
lobed blade shape
serrated margins
prominent primary veins
secondary vein network
petiole attachment at the leaf base
surface color differences between adaxial and abaxial sides
minor shape asymmetry
```

## Normal Variation That Can Confuse Diagnosis

These patterns should not be over-diagnosed by themselves:

```text
natural vein contrast
minor shadow from raised veins
leaf gloss on the upper surface
folding or curling caused by handling
small mechanical tears
lighting-induced pale areas
background soil, dust, or water spots
```

## Disease Evidence Requires More Than Leaf Structure

The assistant should avoid treating normal leaf anatomy as disease. Disease evidence
should be based on visible abnormal patterns, such as:

```text
chlorosis
necrosis
powdery growth
downy fuzzy growth
vein-bounded spots
water-soaked areas
yellow halos
insect damage
galls
wilting
```

## App-Facing Rule

If the assistant sees only normal structures and no abnormal symptoms, it should say
that there is no visible disease evidence in the image, while still noting image
quality and side.

See [Grape Leaf Anatomy](anatomy.md).

