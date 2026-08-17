---
title: Downy Mildew Treatment - App-Facing Rule
page_type: detailed_section_page
source_wiki_path: wiki/treatment/downy_mildew.md
source_section: App-Facing Rule
parent_page: index.md
review_status: draft
last_updated: 2026-07-29
disease_id: downy_mildew
---

# Downy Mildew Treatment - App-Facing Rule

Parent: [Downy Mildew Treatment](index.md)

```text
source_wiki_path: wiki/treatment/downy_mildew.md
source_section: App-Facing Rule
retrieval_unit: detailed section page
search_cues: Downy Mildew Treatment App-Facing Rule text if reviewed_management_resource_selected answer only from that reviewed resource if no reviewed_management_resource_selected do not recommend chemical treatment do not infer treatment from the disease
```

```text
if reviewed_management_resource_selected:
  answer only from that reviewed resource

if no reviewed_management_resource_selected:
  do not recommend chemical treatment
  do not infer treatment from the disease name alone
  state that reviewed management resources are missing
```
