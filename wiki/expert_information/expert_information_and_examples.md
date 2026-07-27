---
title: Expert Information And Examples
page_type: expert_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Expert Information And Examples

Expert information is the reviewed layer between raw human expertise and
assistant behavior. It should explain not only the final label, but also the
evidence boundary that led to that label.

## What Counts As Expert Information

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

Do not use unsupported expert memory as settled truth. For now, simple updates
may be written directly in `wiki/`; mark uncertainty clearly. Store original
notes in `raw/` only when provenance or later review matters.

## Expert Claim Shape

Use this structure when turning expert notes into wiki content:

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

## Example Case Shape

Each expert example should connect image evidence to an app behavior:

```text
case_id:
disease_or_condition:
image_ids:
side_coverage:
expert_label:
expert_rationale:
fine_visual_features:
evidence_present:
evidence_missing:
expected_diagnosis_status:
recommended_next_image:
allowed_follow_up_questions:
linked_treatment_resources:
```

## App-Facing Use

Expert examples can support:

```text
visual intake examples
diagnosis decision examples
follow-up dialog examples
behavior eval oracles
wiki Q&A examples
assistant-output audit cases
single-surface diagnostic cases
```

Reviewed examples should use stable case IDs when possible. See
[Case Example Structure](case_example_structure.md).

## Required Links

Expert pages should link to:

```text
disease page
front/back process
diagnosis script
dialog tree branch
treatment resource index, if treatment is discussed
raw source record, if one exists
```

See [Manual Source Backlog](../../system/source_requirements/manual_source_backlog.md) and
[Disease Page Template](../diseases/disease_page_template.md).
