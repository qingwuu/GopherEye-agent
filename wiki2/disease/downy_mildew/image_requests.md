---
title: Downy Mildew - Image Requests
page_type: detailed_section_page
source_wiki_path: wiki/disease/downy_mildew/index.md
source_section: Image Requests
parent_page: index.md
review_status: draft
last_updated: 2026-07-29
disease_id: downy_mildew
sources:
  - https://cals.cornell.edu/integrated-pest-management/grapevine-downy-mildew-plasmopara-viticola-fruit-fact-sheet
  - https://agriculture.canada.ca/en/agricultural-production/crop-protection/agricultural-pest-management-resources/identification-guide-major-diseases-grapes
  - https://apsjournals.apsnet.org/doi/10.1094/PHP-01-17-0009-DG
  - https://www.apsnet.org/edcenter/pdlessons/Pages/DownyMildewGrape.aspx
---

# Downy Mildew - Image Requests

Parent: [Downy Mildew](index.md)

```text
source_wiki_path: wiki/disease/downy_mildew/index.md
source_section: Image Requests
retrieval_unit: detailed section page
search_cues: Downy Mildew Image Requests text request adaxial_surface_same_leaf only underside is visible and sporulation is faint patchy or not clearly associated with lesion pattern request abaxial_surface_same_leaf upper surface shows
```

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
