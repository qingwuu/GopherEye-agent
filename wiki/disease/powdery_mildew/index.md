---
title: Powdery Mildew
page_type: disease_page
disease_id: powdery_mildew
review_status: draft
last_updated: 2026-07-29
sources:
  - https://ipm.ucanr.edu/agriculture/grape/powdery-mildew/
  - https://cals.cornell.edu/integrated-pest-management/outreach-education/fact-sheets/grapevine-powdery-mildew-erysiphe-necator-fruit-fact-sheet
  - https://agriculture.canada.ca/en/agricultural-production/crop-protection/agricultural-pest-management-resources/identification-guide-major-diseases-grapes
  - https://pmc.ncbi.nlm.nih.gov/articles/PMC6638670/
related:
  treatment: ../../treatment/powdery_mildew.md
  diagnosis_sop: ../../procedures/diagnosis_sop.md
  image_evidence_sop: ../../procedures/image_and_evidence_sop.md
  anatomy: ../../reference/grape_leaf_anatomy.md
  terminology: ../../reference/terminology.md
  differentials:
    - ../downy_mildew/index.md
    - ../healthy/index.md
    - ../others/index.md
---

# Powdery Mildew

Powdery mildew is a surface-growth diagnosis. Look for growth that sits on the
epidermis rather than color change alone.

## Identity

```text
disease_id: powdery_mildew
common_names: powdery mildew, grapevine powdery mildew, oidium
pathogen_or_cause: Erysiphe necator, historically Uncinula necator
crop_scope: grape leaves and other green grapevine tissues
review_status: draft
```

## Visual Evidence Thresholds

```text
possible:
  faint white-gray powder, dusty film, webby mycelium, or chlorotic spots that
  could correspond to powdery growth on either leaf surface

provisional:
  visible superficial white-gray powdery colonies, webby mycelium, or dusty
  conidia on a grape leaf surface, with location and surface recorded

strong single-surface:
  clearly visible white-gray powdery colonies or webby mycelium on one surface,
  especially when growth crosses veins, has a superficial dusty texture, or
  appears as multiple colonies rather than glare, dust, or residue

confirmed visual:
  high-signal powdery colonies or conidia on a clear leaf surface plus
  differential reasoning against downy mildew, dust/residue, normal gloss, and
  insect debris; lab confirmation is outside image-only diagnosis

expert review:
  only chlorosis without visible growth
  faint residue that could be dust, spray deposit, or glare
  severe necrosis where original powdery growth is no longer visible
  powdery and downy signs appearing together
```

Use [Image And Evidence SOP](../../procedures/image_and_evidence_sop.md) to
decide whether one visible surface is enough.

## Feature Checklist

Record visible fine features when present:

```text
white-gray powdery or dusty colonies
fine web-like mycelium
powdery film that sits on top of veins and interveinal tissue
colonies that start as small circular patches and may coalesce
young colonies with subtle whitish or metallic sheen
chlorotic spot on the opposite surface corresponding to a mildew colony
gray senescent colonies
tiny orange, brown, or black chasmothecia/cleistothecia on older colonies
localized epidermal browning or necrosis under old colonies
leaf curling, puckering, brittleness, or stunting in advanced cases
```

Do not require every feature. A clear single high-signal surface-growth feature
can be enough for diagnosis.

## Localization

Use [Grape Leaf Anatomy](../../reference/grape_leaf_anatomy.md) and
[Terminology](../../reference/terminology.md) for surface and leaf-part labels.

```text
adaxial evidence:
  upper-surface white or grayish-white powdery patches
  superficial dusty coating rather than tissue-internal yellowing alone
  colonies crossing vein boundaries
  chlorotic flecks or patches near colonies
  old colonies with gray tone or tiny dark chasmothecia
  curling or puckering when infection is advanced

abaxial evidence:
  fine white web-like mycelium
  white-gray powdery colonies or conidia
  gray spots on the underside
  small colonies corresponding to subtle upper-surface chlorotic spots
  late-season dark chasmothecia on either surface
```

## Differentials

```text
downy_mildew:
  consider when pale yellow spots, humid-period growth, or underside growth
  overlap in casual descriptions
  reason against powdery only: downy mildew more often has oily yellow upper
  lesions and cottony underside sporulation
  link: ../downy_mildew/index.md

dust_spray_or_soil_residue:
  consider when white-gray material sits on the surface
  reason against disease: residue often lacks colony edges, webby texture,
  lesion association, or repeated colony pattern
  link: ../others/index.md

normal_gloss_or_lighting_artifact:
  consider when glare looks pale or whitish
  reason against disease: glare follows light direction and does not form
  colonies, mycelium, powder, or chasmothecia
  link: ../healthy/index.md
```

Use [Diagnosis SOP](../../procedures/diagnosis_sop.md) before naming the final
candidate.

## Image Requests

```text
request adaxial_surface_same_leaf:
  only underside is visible and growth is faint, ambiguous, or lacks lesion
  context that would separate powdery mildew from downy mildew or residue

request abaxial_surface_same_leaf:
  only upper side is visible and evidence is limited to pale yellow spots, faint
  powder, or uncertain residue where downy mildew remains plausible

both_sides_same_leaf required:
  only when one-side evidence cannot separate powdery mildew from downy mildew,
  artifact, dust, spray residue, or another disease

wider_context useful:
  to assess distribution across leaves, canopy severity, or whether white
  material repeats as disease rather than localized contamination
```

If one clear surface shows high-signal powdery mildew structures, set:

```text
evidence_sufficiency: sufficient_single_surface
recommended_next_image: none
single_surface_decision: diagnostic
opposite_surface_role: optional_confirmation or not_needed
```

## Treatment Link

Treatment guidance is separate from visual diagnosis. Use
[Powdery Mildew Treatment](../../treatment/powdery_mildew.md); do not provide
management advice unless reviewed treatment resources are available.
