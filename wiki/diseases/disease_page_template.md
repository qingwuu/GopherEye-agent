---
title: Disease Page Template
page_type: template_page
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Disease Page Template

Copy this structure when creating a disease or condition page.

## Frontmatter

```yaml
---
title: Disease Or Condition Name
page_type: disease_page
review_status: needs_review
last_updated: YYYY-MM-DD
sources:
  - raw/sources/disease_information/<source_file>
---
```

## Identity

```text
disease_id:
common_names:
pathogen_or_cause:
crop_scope:
review_status:
```

## Required Visual Evidence

```text
minimum evidence for possible diagnosis
minimum evidence for provisional diagnosis
minimum evidence for confirmed diagnosis
evidence that should trigger expert review
```

## Adaxial Evidence

```text
upper-surface symptoms
lesion pattern
color pattern
surface growth or absence of growth
normal structures that may be confused
```

## Abaxial Evidence

```text
underside symptoms
sporulation or surface growth
vein-related clues
texture clues
evidence required to distinguish confusion diseases
```

## Differential Diagnoses

```text
disease_or_condition:
reason_to_consider:
reason_against:
additional_image_or_question_needed:
```

## Front/Back Behavior

```text
when to request adaxial_surface_same_leaf
when to request abaxial_surface_same_leaf
when both_sides_same_leaf is required
when wider_context is useful
```

## Expert Examples

Link reviewed cases:

```text
case_id:
image_ids:
expert_rationale:
expected_model_behavior:
```

## Treatment Resources

Link only reviewed pages:

```text
wiki/treatment_resources/<condition>_management.md
```

If no reviewed page exists, say treatment guidance is not available from the
wiki.

See [Expert Information And Examples](../expert_information/expert_information_and_examples.md),
[Front/Back Leaf Process](../workflows/front_back_leaf_process.md), and
[Treatment Resource Policy](../treatment_resources/treatment_resource_policy.md).
