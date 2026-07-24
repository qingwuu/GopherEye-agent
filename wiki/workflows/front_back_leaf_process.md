---
title: Front/Back Leaf Process
page_type: workflow_page
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Front/Back Leaf Process

This page defines the whole process for handling adaxial and abaxial grape leaf
images from intake through diagnosis.

## Process

```text
1. Receive current user image.
2. Assign code-owned image IDs and image_order values.
3. Run visual intake.
4. Determine side_label: adaxial, abaxial, mixed, uncertain, or not_leaf.
5. Check image quality.
6. Check whether the current disease candidates require the missing side.
7. If the other side is needed, ask for the same leaf from the other side.
8. When a second side arrives, compare it with prior session images.
9. Record the front/back relationship.
10. Re-run diagnosis decision with both visual intakes.
11. Save evidence_present, evidence_missing, diagnosis_status, and allowed
    follow-up questions.
```

## State Transitions

```text
no_image
-> current_image_received
-> side_identified
-> evidence_sufficiency_checked
-> missing_side_requested
-> front_back_pair_received
-> pair_compared
-> diagnosis_updated
```

## Same-Leaf Pair Requirement

When asking for the other side, request the same leaf whenever possible. The
system should not silently treat two unrelated leaves as a front/back pair.

Same-leaf evidence can include:

```text
user confirmation
similar leaf shape
similar lesion position
matching context photo
plant_id or leaf_id from the app
manual reviewer confirmation
```

## User Instructions

Use direct wording:

```text
Please upload the underside of the same leaf. Keep the spotted area in frame and
use even lighting.
```

If the first image is the underside:

```text
Please upload the upper side of the same leaf so I can compare the surface
pattern with the underside evidence.
```

If same-leaf pairing is uncertain:

```text
I can compare these images, but I cannot confirm they are the same leaf. If
possible, upload both sides of one leaf in the same session.
```

## App Records

The app should connect this process to:

```text
image_manifest rows
image_relationship rows
visual_intake rows
diagnosis output rows
chat session memory
```

See [Front/Back Image Request](front_back_request.md),
[Evidence Sufficiency](evidence_sufficiency.md),
[Grape Leaf Surfaces](../grape_leaf/leaf_surfaces.md), and
[Case Example Structure](../expert_information/case_example_structure.md).
