---
title: Powdery Mildew
page_type: disease_page
review_status: needs_review
last_updated: 2026-07-27
review_status: draft
sources:
  - https://ipm.ucanr.edu/agriculture/grape/powdery-mildew/
  - https://cals.cornell.edu/integrated-pest-management/outreach-education/fact-sheets/grapevine-powdery-mildew-erysiphe-necator-fruit-fact-sheet
  - https://agriculture.canada.ca/en/agricultural-production/crop-protection/agricultural-pest-management-resources/identification-guide-major-diseases-grapes
  - https://pmc.ncbi.nlm.nih.gov/articles/PMC6638670/
---

# Powdery Mildew

## Identity

```text
disease_id: powdery_mildew
common_names: powdery mildew, grapevine powdery mildew, oidium
pathogen_or_cause: Erysiphe necator, also historically Uncinula necator
crop_scope: grape leaves and other green grapevine tissues
review_status: needs_review
```

## Required Visual Evidence

Powdery mildew is primarily a surface-growth diagnosis. The model should look
for growth that sits on the epidermis rather than color change alone.

```text
minimum evidence for possible diagnosis:
  faint white-gray powder, dusty film, webby mycelium, or chlorotic spots that
  could correspond to powdery growth on either leaf surface

minimum evidence for provisional diagnosis:
  visible superficial white-gray powdery colonies, webby mycelium, or dusty
  conidia on a grape leaf surface, with location and surface recorded

minimum evidence for strong single-surface diagnosis:
  clearly visible white-gray powdery colonies or webby mycelium on one surface,
  especially when the growth crosses veins, has a superficial dusty texture, or
  appears as multiple colonies rather than glare, dust, or residue

minimum evidence for confirmed visual diagnosis:
  high-signal powdery colonies or conidia on a clear leaf surface plus
  differential reasoning against downy mildew, dust/residue, normal gloss, and
  insect debris; lab confirmation is outside image-only diagnosis

evidence that should trigger expert review:
  only chlorosis without visible growth
  faint residue that could be dust, spray deposit, or glare
  severe necrosis where original powdery growth is no longer visible
  powdery and downy signs appearing together
```

## Fine Visual Features

Record these small features when visible:

```text
white-gray powdery or dusty colonies
fine web-like mycelium
powdery film that sits on top of veins and interveinal tissue
colonies that start as small circular patches and may coalesce
young colonies with a subtle whitish or metallic sheen
chlorotic spot on the opposite surface corresponding to a mildew colony
gray senescent colonies
tiny orange, brown, or black chasmothecia/cleistothecia on older colonies
localized epidermal browning or necrosis under old colonies
leaf curling, puckering, brittleness, or stunting in more advanced cases
```

Do not require all of these features. A clear single high-signal surface-growth
feature can be enough for diagnosis.

## Adaxial Evidence

The upper surface can be diagnostic by itself when powdery colonies are clear.

```text
upper-surface white or grayish-white powdery patches
superficial dusty coating rather than tissue-internal yellowing alone
colonies crossing vein boundaries
chlorotic flecks or patches near colonies
old colonies with gray tone or tiny dark chasmothecia
curling or puckering when infection is advanced
```

## Abaxial Evidence

The underside can also show powdery mildew.

```text
fine white web-like mycelium
white-gray powdery colonies or conidia
gray spots on the underside
small colonies corresponding to subtle upper-surface chlorotic spots
late-season dark chasmothecia on either surface
```

## Differential Diagnoses

```text
disease_or_condition: downy_mildew
reason_to_consider: pale yellow spots, humid-period growth, or underside
  growth may overlap in casual descriptions
reason_against: powdery mildew growth is superficial, white-gray, powdery or
  dusty, often visible on the upper surface; downy mildew more often has oily
  yellow upper lesions and cottony underside sporulation
additional_image_or_question_needed: request underside only if surface growth is
  faint or if powdery vs downy remains unresolved

disease_or_condition: dust, spray residue, or soil residue
reason_to_consider: white-gray material can sit on the surface
reason_against: residue often lacks colony edges, webby texture, lesion
  association, or repeated colony pattern
additional_image_or_question_needed: close-up or user note about whether the
  material wipes off may help when ambiguous

disease_or_condition: normal leaf gloss or lighting artifact
reason_to_consider: glare can look pale or whitish
reason_against: glare follows light direction and does not form colonies,
  mycelium, powder, or chasmothecia
additional_image_or_question_needed: clearer same view only if glare blocks the
  suspected colony
```

## Front/Back Behavior

```text
when to request adaxial_surface_same_leaf:
  only underside is visible and growth is faint, ambiguous, or lacks lesion
  context that would separate powdery mildew from downy mildew or residue

when to request abaxial_surface_same_leaf:
  only upper side is visible and the evidence is limited to pale yellow spots,
  faint powder, or uncertain residue where downy mildew remains plausible

when both_sides_same_leaf is required:
  not automatic; require both sides only when one-side evidence cannot separate
  powdery mildew from downy mildew, artifact, dust, spray residue, or another
  disease

when wider_context is useful:
  to assess distribution across multiple leaves, canopy severity, or whether
  the white material repeats as disease rather than localized contamination
```

## Single-Surface Decision Rule

If one clear surface shows high-signal powdery mildew structures, set:

```text
evidence_sufficiency: sufficient_single_surface
recommended_next_image: none
single_surface_decision: diagnostic
opposite_surface_role: optional_confirmation or not_needed
```

Ask for the other surface only when the visible evidence is not diagnostic
enough, not simply because only one side was uploaded.

## Treatment Resources

No reviewed powdery mildew treatment page is currently linked here. Keep
treatment guidance out of diagnosis responses unless a reviewed management page
is included in context.

See [Evidence Sufficiency](../workflows/evidence_sufficiency.md),
[Front/Back Image Request](../workflows/front_back_request.md), and
[Differential Diagnosis Procedure](../procedures/differential_diagnosis_procedure.md).
