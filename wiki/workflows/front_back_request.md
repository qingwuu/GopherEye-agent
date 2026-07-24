---
title: Front/Back Image Request
page_type: workflow_page
review_status: draft
last_updated: 2026-07-12
sources: []
---

# Front/Back Image Request

GopherEye should reason about leaf side because some diagnostic evidence is more
visible on one surface than the other.

## Leaf Side Labels

```text
adaxial
abaxial
mixed
uncertain
not_leaf
```

## Request Rules

Request the abaxial side when:

```text
only adaxial image is available
underside evidence is important for the suspected disease
diagnosis confidence is low or moderate
downy mildew vs powdery mildew distinction is uncertain
```

Request the adaxial side when:

```text
only abaxial image is available
upper-surface lesion pattern is needed
chlorosis, halo, or vein-bounded spots must be inspected
```

Request a clearer image when:

```text
image is blurry
image is dark
image is overexposed
leaf is occluded
symptoms cannot be inspected
```

## User-Facing Language

Use concise language:

```text
This may be powdery mildew, but I need the underside of the same leaf to check
for white web-like mycelium or powdery colonies before making a stronger
diagnosis.
```

See [Evidence Sufficiency](evidence_sufficiency.md).

## Whole Process

For the full intake, pairing, comparison, and diagnosis update sequence, see
[Front/Back Leaf Process](front_back_leaf_process.md).

