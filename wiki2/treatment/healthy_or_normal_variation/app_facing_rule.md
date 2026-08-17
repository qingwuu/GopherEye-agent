---
title: Healthy Or Normal Variation Treatment - App-Facing Rule
page_type: detailed_section_page
source_wiki_path: wiki/treatment/healthy_or_normal_variation.md
source_section: App-Facing Rule
parent_page: index.md
review_status: draft
last_updated: 2026-07-29
disease_id: healthy
---

# Healthy Or Normal Variation Treatment - App-Facing Rule

Parent: [Healthy Or Normal Variation Treatment](index.md)

```text
source_wiki_path: wiki/treatment/healthy_or_normal_variation.md
source_section: App-Facing Rule
retrieval_unit: detailed section page
search_cues: Healthy Or Normal Variation Treatment App-Facing Rule text if image_shows_no_visible_disease_evidence say that no disease evidence is visible in the provided image do not claim the plant is disease-free do not recommend
```

```text
if image_shows_no_visible_disease_evidence:
  say that no disease evidence is visible in the provided image
  do not claim the plant is disease-free
  do not recommend chemical treatment

if image_quality_blocks_inspection:
  ask for the most useful next image before making a healthy/normal judgment
```
