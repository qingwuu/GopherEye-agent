---
title: Healthy Or Normal Variation Treatment
page_type: treatment_page
disease_id: healthy
review_status: draft
last_updated: 2026-07-29
sources: []
related:
  disease: ../disease/healthy/index.md
  diagnosis_sop: ../procedures/diagnosis_sop.md
  source_policy: ../reference/source_policy.md
---

# Healthy Or Normal Variation Treatment

This page supports the boundary between visual reassurance and management
advice. It does not provide treatment recommendations.

## App-Facing Rule

```text
if image_shows_no_visible_disease_evidence:
  say that no disease evidence is visible in the provided image
  do not claim the plant is disease-free
  do not recommend chemical treatment

if image_quality_blocks_inspection:
  ask for the most useful next image before making a healthy/normal judgment
```

## Required Links

- Diagnosis page: [Healthy Or Normal Variation](../disease/healthy/index.md)
- Review rules: [Source Policy](../reference/source_policy.md)
