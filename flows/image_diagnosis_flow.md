# Image Diagnosis Flow

## Purpose

Use one VLM and the curated wiki to produce an evidence-grounded, app-ready
diagnosis result.

## Inputs

```text
user image
user question
current session state
selected wiki disease pages
selected workflow pages
visual intake schema
diagnosis output schema
```

## Outputs

```text
visual intake JSON
diagnosis output JSON
user-facing answer
recommended next image if evidence is insufficient
```

## Steps

```text
1. Load user image.
2. VLM performs visual intake using prompts/visual_intake_prompt.md.
3. Validate visual intake JSON against schemas/visual_intake.schema.json.
4. Select relevant wiki pages, including grape leaf foundation pages when
   anatomy, side, normal variation, or image quality matters.
5. VLM combines visual evidence and wiki rules using prompts/diagnosis_decision_prompt.md.
6. Validate diagnosis JSON against schemas/diagnosis_output.schema.json.
7. Apply hard business rules.
8. Save diagnosis state for follow-up chat.
9. Return user-facing message and allowed follow-up questions.
```

## Hard Business Rules

```text
If image_quality.overall is unusable:
  diagnosis_status should be poor_quality.
  recommended_next_image should be clearer_same_view.

If evidence_sufficiency starts with insufficient:
  diagnosis_status must not be confirmed.

If side_label is adaxial and the disease page says abaxial evidence is needed
for this specific case:
  recommended_next_image should be abaxial_surface_same_leaf.

If one visible surface has sufficient disease-specific evidence:
  evidence_sufficiency should be sufficient_single_surface.
  recommended_next_image should be none.
  do not request the opposite surface automatically.

If image_quality issues are nonblocking:
  do not set diagnosis_status to poor_quality.
  keep the answer focused on visible leaf evidence.
```

## Minimal Demo Goal

```text
User uploads only adaxial image with clear superficial white-gray powdery
colonies.
System outputs powdery mildew diagnosis from the single surface and does not
request the abaxial image as a requirement.

User uploads only adaxial image with generic pale spots and uncertain faint
residue.
System keeps the diagnosis provisional and requests the abaxial image of the
same leaf only if it would separate powdery mildew, downy mildew, or artifact.
```

## Grape Leaf Foundation Pages

The diagnosis flow should use these pages when visual localization matters:

```text
wiki/grape_leaf/anatomy.md
wiki/grape_leaf/leaf_surfaces.md
wiki/grape_leaf/normal_variation.md
wiki/grape_leaf/image_guidance.md
```
