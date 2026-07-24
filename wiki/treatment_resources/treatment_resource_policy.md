---
title: Treatment Resource Policy
page_type: treatment_page
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Treatment Resource Policy

Treatment and management guidance must be handled more cautiously than visual
diagnosis. GopherEye should not recommend chemical treatment unless a reviewed
management page is selected in context.

## Hard Rules

```text
Do not recommend chemical treatment from unsupported memory.
Do not infer treatment from a disease name alone.
Do not give rate, timing, product, or legal-use advice unless the exact reviewed
resource supports it.
Mention diagnosis uncertainty when the diagnosis is provisional.
Prefer source-backed management categories over product-specific advice.
Record missing treatment sources in the manual source backlog.
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
No reviewed treatment page selected:
  Do not recommend treatment. Say reviewed management resources are missing.

Reviewed general management page selected:
  Summarize supported non-product management steps and cite the page.

Reviewed chemical-management page selected:
  Keep wording conservative, cite the page, and tell the user to follow current
  label and local regulations.
```

## Treatment Resource Record

Use this structure when creating a reviewed treatment page:

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

See [Treatment Resource Index](resource_index.md),
[Diagnosis Scripts](../diagnosis/diagnosis_scripts.md), and
[Manual Source Backlog](../../system/source_requirements/manual_source_backlog.md).
