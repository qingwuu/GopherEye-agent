---
title: Powdery Mildew - Image Requests
page_type: detailed_section_page
source_wiki_path: wiki/disease/powdery_mildew/index.md
source_section: Image Requests
parent_page: index.md
review_status: draft
last_updated: 2026-07-29
disease_id: powdery_mildew
sources:
  - https://ipm.ucanr.edu/agriculture/grape/powdery-mildew/
  - https://cals.cornell.edu/integrated-pest-management/outreach-education/fact-sheets/grapevine-powdery-mildew-erysiphe-necator-fruit-fact-sheet
  - https://agriculture.canada.ca/en/agricultural-production/crop-protection/agricultural-pest-management-resources/identification-guide-major-diseases-grapes
  - https://pmc.ncbi.nlm.nih.gov/articles/PMC6638670/
---

# Powdery Mildew - Image Requests

Parent: [Powdery Mildew](index.md)

```text
source_wiki_path: wiki/disease/powdery_mildew/index.md
source_section: Image Requests
retrieval_unit: detailed section page
search_cues: Powdery Mildew Image Requests text request adaxial_surface_same_leaf only underside is visible and growth is faint ambiguous or lacks lesion context that would separate powdery mildew from downy mildew
```

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
