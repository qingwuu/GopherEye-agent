---
title: Diagnosis Scripts
page_type: procedure_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Diagnosis Scripts

Diagnosis scripts are reusable botanical response patterns. They describe what
an expert-style assistant should check and how it should communicate
uncertainty.

## First Image Script

Use when the user provides an image:

```text
First I will check whether this is a grape leaf, whether the image is clear enough, which leaf surface is visible, and what symptoms are actually visible.
```

The observation should include:

```text
leaf or non-leaf status
grape leaf plausibility
image quality
leaf surface
visible structures
visible abnormal signs
evidence still missing
```

## Missing Surface Script

Use when the opposite surface is diagnostically important:

```text
This image shows only one side of the leaf. Please upload the other side of the same leaf so I can compare surface symptoms before making a stronger diagnosis.
```

If the missing side is known:

```text
Please upload the underside of the same leaf.
Please upload the upper side of the same leaf.
```

## Single-Surface Diagnosis Script

Use when one visible side has high-signal disease-specific evidence:

```text
This side of the leaf shows enough specific evidence for a diagnosis. The opposite side could help confirm the pattern, but it is not required for this assessment.
```

## Differential Diagnosis Script

Use when symptoms overlap:

```text
This evidence could fit more than one condition. I will keep the diagnosis provisional and compare the visible symptoms against the most likely differentials.
```

The response should state:

```text
reason to consider each differential
reason against each differential
evidence still missing
next image or observation needed
```

## Not Enough Evidence Script

Use when the image does not support reliable diagnosis:

```text
I cannot make a reliable disease diagnosis from this evidence alone. The main missing evidence is: [specific missing evidence]. The most useful next image is:
[specific next image].
```

## Treatment Question Script

Use when the user asks what to do:

See [Visual Observation Sequence](../procedures/visual_observation_sequence.md),
[Evidence Sufficiency](../workflows/evidence_sufficiency.md),
[Front/Back Leaf Process](../workflows/front_back_leaf_process.md),
[Grape Leaf Diagnosis Dialog Tree](../dialogs/grape_leaf_diagnosis_dialog_tree.md), and
[Treatment Resource Policy](../treatment_resources/treatment_resource_policy.md).
