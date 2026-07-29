---
title: Downy Mildew
page_type: disease_page
disease_id: downy_mildew
review_status: draft
last_updated: 2026-07-29
sources:
  - https://cals.cornell.edu/integrated-pest-management/grapevine-downy-mildew-plasmopara-viticola-fruit-fact-sheet
  - https://agriculture.canada.ca/en/agricultural-production/crop-protection/agricultural-pest-management-resources/identification-guide-major-diseases-grapes
  - https://apsjournals.apsnet.org/doi/10.1094/PHP-01-17-0009-DG
  - https://www.apsnet.org/edcenter/pdlessons/Pages/DownyMildewGrape.aspx
related:
  treatment: ../../treatment/downy_mildew.md
  diagnosis_sop: ../../procedures/diagnosis_sop.md
  image_evidence_sop: ../../procedures/image_and_evidence_sop.md
  anatomy: ../../reference/grape_leaf_anatomy.md
  terminology: ../../reference/terminology.md
  differentials:
    - ../powdery_mildew/index.md
    - ../healthy/index.md
    - ../others/index.md
---

# Downy Mildew

Downy mildew is often a lesion-pattern plus surface-specific sporulation
diagnosis. The underside is highly useful, but not mandatory in every
single-image case.

## Identity

```text
disease_id: downy_mildew
common_names: downy mildew, grapevine downy mildew
pathogen_or_cause: Plasmopara viticola
crop_scope: grape leaves and other green grapevine tissues
review_status: draft
```

## Visual Evidence Thresholds

```text
possible:
  yellow-green, oily-looking, angular, or vein-bounded lesions on the upper
  surface, or white cottony/downy growth on the lower surface

provisional:
  clear oil spots or vein-limited angular yellow-to-brown lesions on the upper
  surface, or visible underside white cottony sporulation associated with leaf
  lesions

strong single-surface:
  high-signal adaxial oil spots or angular vein-limited lesions with lesion
  geometry and differential reasoning, or high-signal abaxial cottony
  sporulation on a grape leaf underside

confirmed visual:
  typical oil spots and/or underside downy sporulation with alternatives
  addressed; lab confirmation is outside image-only diagnosis

expert review:
  only generic yellowing, marginal scorch, or brown spots
  suspected downy mildew with sparse or absent sporulation
  mixed powdery and downy signs
  severe necrosis without enough lesion history or geometry
```

Use [Image And Evidence SOP](../../procedures/image_and_evidence_sop.md) to
decide whether one visible surface is enough.

## Feature Checklist

Record visible fine features when present:

```text
shiny yellow or yellow-green oil spots on the adaxial surface
slightly darker, bruised-looking early spots
round lesions that become angular as they expand
vein-delimited lesion edges
yellow-brown, reddish-brown, or brown necrotic centers as lesions age
small late-season angular lesions
white cottony or downy sporulation on the abaxial surface
sporulation limited to the underside of corresponding lesions
patchy or sparse underside sporulation
dark underside tissue beneath old oil spots
vein tracking or lesion extension along veins in some cultivars
undefined dark olive to black spotted regions on susceptible cultivars
```

Absence of visible underside sporulation in one photo does not rule out downy
mildew when humidity, timing, cultivar, or lesion age may reduce visibility.

## Localization

Use [Grape Leaf Anatomy](../../reference/grape_leaf_anatomy.md) and
[Terminology](../../reference/terminology.md) for surface and leaf-part labels.

```text
adaxial evidence:
  shiny or oily-looking yellow spots
  yellow-green mottled spots that are localized rather than uniform deficiency
  spots that become brown or reddish-brown with age
  angular or vein-limited lesions
  oil spots near older foliage or fruiting-zone leaves
  dark, dry, or black-brown atypical lesions in some cultivars
  vein tracking in cultivars where this pattern is reported

abaxial evidence:
  white cottony/downy sporulation on the lower leaf surface
  sporulation directly under an upper lesion when both sides are available
  patchy or sparse sporulation on older lesions
  darkened tissue under upper oil spots
  raised veins that help identify the underside but are not disease by themselves
```

Generic chlorosis alone is not enough. Describe lesion shape, edge, vein
relationship, and distribution before calling downy mildew.

## Differentials

```text
powdery_mildew:
  consider when white growth and leaf chlorosis overlap in casual descriptions
  reason against downy only: powdery mildew is superficial white-gray powdery
  or webby growth on the epidermis
  link: ../powdery_mildew/index.md

nutrient_deficiency_or_physiological_chlorosis:
  consider when yellowing is interveinal or patchy
  reason against downy: deficiencies usually lack oil-spot sheen, lesion edges,
  cottony sporulation, and localized vein-bounded lesion geometry
  link: ../others/index.md

black_rot_anthracnose_or_other_necrotic_leaf_spot:
  consider when brown spots and necrosis overlap
  reason against downy: downy mildew lesions often begin as oil spots and may
  be angular or vein-delimited
  link: ../others/index.md
```

Use [Diagnosis SOP](../../procedures/diagnosis_sop.md) before naming the final
candidate.

## Image Requests

```text
request adaxial_surface_same_leaf:
  only underside is visible and sporulation is faint, patchy, or not clearly
  associated with lesion pattern

request abaxial_surface_same_leaf:
  upper surface shows generic yellowing, faint oil spots, or lesions where
  powdery mildew, deficiency, or artifact remain plausible

both_sides_same_leaf required:
  only when single-side evidence cannot separate downy mildew from powdery
  mildew, deficiency, residue, or another lesion disease

wider_context useful:
  to assess whether lesions are localized oil spots, widespread deficiency-like
  chlorosis, late-season older foliage symptoms, or multi-leaf disease pressure
```

If one surface has high-signal downy mildew evidence, set:

```text
evidence_sufficiency: sufficient_single_surface
recommended_next_image: none
single_surface_decision: diagnostic
opposite_surface_role: optional_confirmation or not_needed
```

## Treatment Link

Treatment guidance is separate from visual diagnosis. Use
[Downy Mildew Treatment](../../treatment/downy_mildew.md); do not provide
management advice unless reviewed treatment resources are available.
