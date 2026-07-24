---
title: Case Example Structure
page_type: expert_page
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Case Example Structure

A case example is the unit that connects expert review, image evidence,
diagnosis behavior, and evaluation.

## Case Example Layers

```text
raw image files
image manifest rows
front/back relationship rows
reviewed visual labels
expert diagnosis rationale
diagnosis output target
follow-up dialog target
eval oracle
```

## Minimum Case Fields

```text
case_id
case_type
plant_id, if known
leaf_id, if known
observation_id, if known
image_ids
side_coverage
visible_symptoms
visible_structures
expert_label
expert_rationale
evidence_present
evidence_missing
differential_diagnoses
expected_next_step
review_status
source_refs
```

## Front/Back Case Pack

A strong front/back example should include:

```text
adaxial image of the symptomatic leaf
abaxial image of the same leaf
same-leaf pairing evidence
close-up image when texture is important
wider context image when plant position matters
expert explanation of what changed after the second side was provided
```

## Case Types

```text
single_image_insufficient_evidence
front_back_pair_sufficient_evidence
poor_quality_retry
normal_variation_not_disease
differential_confusion
treatment_question_requires_reviewed_resource
```

## Links To Dataset Examples

Dataset examples already use related structures:

```text
dataset/examples/system_records/image_manifest.example.jsonl
dataset/examples/system_records/image_relationships.example.jsonl
dataset/examples/system_records/reviewed_visual_labels.example.jsonl
dataset/examples/system_records/diagnosis_case_bank.example.jsonl
dataset/examples/system_records/eval_oracles.example.jsonl
```

See [Front/Back Leaf Process](../workflows/front_back_leaf_process.md),
[Diagnosis Scripts](../diagnosis/diagnosis_scripts.md), and
[Grape Leaf Diagnosis Dialog Tree](../dialogs/grape_leaf_diagnosis_dialog_tree.md).
