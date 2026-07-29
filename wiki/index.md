---
title: GopherEye Wiki Index
page_type: index_page
review_status: draft
last_updated: 2026-07-29
---

# GopherEye Wiki

This wiki is organized around diagnosis decisions. Disease pages hold the
disease-specific details; procedures hold reusable reasoning steps; treatment
pages hold only reviewed management boundaries and links.

## Disease Knowledge

- [Powdery Mildew](disease/powdery_mildew/index.md)
- [Downy Mildew](disease/downy_mildew/index.md)
- [Healthy Or Normal Variation](disease/healthy/index.md)
- [Other Or Unresolved Conditions](disease/others/index.md)

## Treatment Boundaries

- [Powdery Mildew Treatment](treatment/powdery_mildew.md)
- [Downy Mildew Treatment](treatment/downy_mildew.md)
- [Healthy Or Normal Variation Treatment](treatment/healthy_or_normal_variation.md)
- [Other Or Unresolved Conditions Treatment](treatment/others.md)

## Procedures

- [Diagnosis SOP](procedures/diagnosis_sop.md)
- [Image And Evidence SOP](procedures/image_and_evidence_sop.md)

## Reference

- [Grape Leaf Anatomy](reference/grape_leaf_anatomy.md)
- [Terminology](reference/terminology.md)
- [Source Policy](reference/source_policy.md)

## Navigation Rules

```text
diagnosis question:
  start with procedures/diagnosis_sop.md
  then open the relevant disease page

image quality or missing surface question:
  start with procedures/image_and_evidence_sop.md
  then open the disease page only if a candidate is visible

treatment question:
  open the disease page for diagnosis confidence
  then open the matching treatment page
  do not answer from unsupported memory

uncertain or noncanonical symptoms:
  compare against disease/healthy/index.md and disease/others/index.md
```
