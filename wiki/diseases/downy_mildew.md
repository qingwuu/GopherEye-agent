---
title: Downy Mildew
page_type: disease_page
review_status: needs_review
last_updated: 2026-07-27
review_status: draft
sources:
  - https://cals.cornell.edu/integrated-pest-management/grapevine-downy-mildew-plasmopara-viticola-fruit-fact-sheet
  - https://agriculture.canada.ca/en/agricultural-production/crop-protection/agricultural-pest-management-resources/identification-guide-major-diseases-grapes
  - https://apsjournals.apsnet.org/doi/10.1094/PHP-01-17-0009-DG
  - https://www.apsnet.org/edcenter/pdlessons/Pages/DownyMildewGrape.aspx
---

# Downy Mildew

## Identity

```text
disease_id: downy_mildew
common_names: downy mildew, grapevine downy mildew
pathogen_or_cause: Plasmopara viticola
crop_scope: grape leaves and other green grapevine tissues
review_status: needs_review
```

## Required Visual Evidence

Downy mildew is often a lesion-pattern plus surface-specific sporulation
diagnosis. The underside is highly useful, but it is not mandatory in every
single image case.

```text
minimum evidence for possible diagnosis:
  yellow-green, oily-looking, angular, or vein-bounded lesions on the upper
  surface, or white cottony/downy growth on the lower surface

minimum evidence for provisional diagnosis:
  clear oil spots or vein-limited angular yellow-to-brown lesions on the upper
  surface, or visible underside white cottony sporulation associated with leaf
  lesions

minimum evidence for strong single-surface diagnosis:
  high-signal adaxial oil spots or angular vein-limited lesions with lesion
  geometry and differential reasoning, or high-signal abaxial cottony
  sporulation on a grape leaf underside

minimum evidence for confirmed visual diagnosis:
  typical oil spots and/or underside downy sporulation with alternatives
  addressed; lab confirmation is outside image-only diagnosis

evidence that should trigger expert review:
  only generic yellowing, marginal scorch, or brown spots
  suspected downy mildew on cold-climate cultivars with sparse or absent
  sporulation
  mixed powdery and downy signs
  severe necrosis without enough lesion history or geometry
```

## Fine Visual Features

Record these small features when visible:

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
mildew, especially when humidity, timing, cultivar, or lesion age may reduce
sporulation visibility.

## Adaxial Evidence

The upper surface can support diagnosis when lesion pattern is specific.

```text
shiny or oily-looking yellow spots
yellow-green mottled spots that are localized rather than uniform deficiency
spots that become brown or reddish-brown with age
angular or vein-limited lesions
oil spots near older foliage or fruiting-zone leaves
dark, dry, or black-brown atypical lesions in some cold-climate cultivars
vein tracking in cultivars where this pattern is reported
```

Generic chlorosis alone is not enough. The model should describe lesion shape,
edge, vein relationship, and distribution before calling downy mildew.

## Abaxial Evidence

The underside often provides the most specific sign.

```text
white cottony/downy sporulation on the lower leaf surface
sporulation directly under an upper lesion when both sides are available
patchy or sparse sporulation on older lesions
darkened tissue under upper oil spots
raised veins that help identify the underside but are not disease by themselves
```

## Differential Diagnoses

```text
disease_or_condition: powdery_mildew
reason_to_consider: white growth and leaf chlorosis can overlap in casual
  descriptions
reason_against: downy mildew usually has oily upper lesions and cottony
  underside sporulation; powdery mildew is superficial white-gray powdery or
  webby growth on the epidermis
additional_image_or_question_needed: request the opposite surface only if the
  visible signs do not separate oil-spot/downy growth from powdery colonies

disease_or_condition: nutrient deficiency or physiological chlorosis
reason_to_consider: yellowing may be interveinal or patchy
reason_against: deficiencies usually lack oil-spot sheen, lesion edges, cottony
  sporulation, and localized vein-bounded lesion geometry
additional_image_or_question_needed: wider context or underside if lesion
  geometry is unclear

disease_or_condition: black rot, anthracnose, or other necrotic leaf spot
reason_to_consider: brown spots and necrosis can overlap
reason_against: downy mildew lesions often begin as oil spots and may be
  angular or vein-delimited; black rot often has different spot margins and
  fruiting bodies
additional_image_or_question_needed: close-up lesion geometry and underside
  view when necrosis is advanced
```

## Front/Back Behavior

```text
when to request adaxial_surface_same_leaf:
  only underside is visible and sporulation is faint, patchy, or not clearly
  associated with lesion pattern

when to request abaxial_surface_same_leaf:
  upper surface shows generic yellowing, faint oil spots, or lesions where
  powdery mildew, deficiency, or artifact remain plausible

when both_sides_same_leaf is required:
  not automatic; require both sides only when single-side evidence cannot
  separate downy mildew from powdery mildew, deficiency, residue, or another
  lesion disease

when wider_context is useful:
  to assess whether lesions are localized oil spots, widespread deficiency-like
  chlorosis, late-season older foliage symptoms, or multi-leaf disease pressure
```

## Single-Surface Decision Rule

If one surface has high-signal downy mildew evidence, set:

```text
evidence_sufficiency: sufficient_single_surface
recommended_next_image: none
single_surface_decision: diagnostic
opposite_surface_role: optional_confirmation or not_needed
```

If only the adaxial surface is visible, do not automatically request the
abaxial surface. Request it only when the visible oil-spot or lesion evidence is
too weak, generic, or confusable.

## Treatment Resources

No reviewed downy mildew treatment page is currently linked here. Keep treatment
guidance out of diagnosis responses unless a reviewed management page is
included in context.

See [Evidence Sufficiency](../workflows/evidence_sufficiency.md),
[Front/Back Image Request](../workflows/front_back_request.md), and
[Differential Diagnosis Procedure](../procedures/differential_diagnosis_procedure.md).
