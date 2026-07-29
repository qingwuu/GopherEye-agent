---
title: Source Policy
page_type: reference_page
review_status: draft
last_updated: 2026-07-29
sources: []
related:
  diagnosis_sop: ../procedures/diagnosis_sop.md
  treatment_powdery: ../treatment/powdery_mildew.md
  treatment_downy: ../treatment/downy_mildew.md
  treatment_healthy: ../treatment/healthy_or_normal_variation.md
  treatment_others: ../treatment/others.md
---

# Source Policy

This page defines how reviewed knowledge, treatment resources, and case
examples enter the wiki.

## Treatment Hard Rules

```text
do not recommend chemical treatment from unsupported memory
do not infer treatment from a disease name alone
do not give rate, timing, product, or legal-use advice unless the exact reviewed
  resource supports it
mention diagnosis uncertainty when the diagnosis is provisional
prefer source-backed management categories over product-specific advice
record missing treatment sources in the manual source backlog
```

Treatment pages:

```text
../treatment/powdery_mildew.md
../treatment/downy_mildew.md
../treatment/healthy_or_normal_variation.md
../treatment/others.md
```

## Resource Review Requirements

A treatment resource can be used in app-facing answers only when it has:

```text
authoritative source
publication or access date
crop and region context
disease or condition scope
review status
reviewer notes
known limitations
```

## Answer Tiers

```text
no reviewed treatment page selected:
  do not recommend treatment
  say reviewed management resources are missing

reviewed general management page selected:
  summarize supported non-product management steps and cite the page

reviewed chemical-management page selected:
  keep wording conservative, cite the page, and tell the user to follow current
  label and local regulations
```

## Treatment Resource Record

```text
resource_id:
title:
organization:
publication_date:
access_date:
crop_context:
region:
disease_scope:
management_categories:
chemical_content_present:
label_or_regulatory_caveat:
reviewer:
review_status:
source_refs:
```

## Expert Information Rules

Expert information is the reviewed layer between raw human expertise and
assistant behavior. It should explain the evidence boundary that led to a label.

Useful expert information includes:

```text
visual diagnostic rules
front/back evidence requirements
single-surface sufficiency rules
common confusion pairs
confidence boundaries
diagnostic visibility thresholds
normal-variation cautions
treatment or management caveats
reviewed example annotations
```

Do not use unsupported expert memory as settled truth. Mark uncertainty clearly
until a claim is reviewed.

## Expert Claim Shape

```text
expert_claim_id:
disease_or_condition:
visual_context:
leaf_side:
claim:
fine_visual_features:
supporting_visual_evidence:
evidence_missing:
single_surface_decision:
confidence_boundary:
common_confusions:
example_case_ids:
source_refs:
review_status:
```

## Case Example Shape

```text
case_id:
case_type:
plant_id, if known:
leaf_id, if known:
observation_id, if known:
image_ids:
side_coverage:
visible_symptoms:
fine_visual_features:
visible_structures:
expert_label:
expert_rationale:
evidence_present:
evidence_missing:
single_surface_decision:
differential_diagnoses:
expected_next_step:
review_status:
source_refs:
```

Dataset examples use related records:

```text
dataset/examples/system_records/image_manifest.example.jsonl
dataset/examples/system_records/image_relationships.example.jsonl
dataset/examples/system_records/reviewed_visual_labels.example.jsonl
dataset/examples/system_records/diagnosis_case_bank.example.jsonl
dataset/examples/system_records/eval_oracles.example.jsonl
```

Missing reviewed sources should be tracked in
[Manual Source Backlog](../../system/source_requirements/manual_source_backlog.md).
