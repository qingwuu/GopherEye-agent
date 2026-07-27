---
title: Wiki Update System
page_type: workflow_page
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Wiki Update System

The wiki update system maintains curated project knowledge. The current default
is intentionally simple: edit or add markdown pages directly under `wiki/`.

## Separation

```text
wiki page edit
-> catalog rebuild
-> versioned commit
```

The raw-source and draft-proposal path is optional. Use it only when the source
needs provenance tracking, human review history, or later training data.

## Related Artifacts

- [Evidence Sufficiency](../../wiki/workflows/evidence_sufficiency.md)
- [Front/Back Image Request](../../wiki/workflows/front_back_request.md)
- [Raw Source Intake Rules](../source_requirements/raw_source_intake_rules.md)
- [Manual Source Backlog](../source_requirements/manual_source_backlog.md)
- [Schema Layer](../contracts/schema_layer.md)
- [Tool Layer](../tools/tool_layer.md)

## Agentic Behavior

Agentic behavior in this flow means the system can:

```text
identify related wiki pages
edit or create a wiki page
suggest hyperlinks
check links
rebuild the catalog
```

For now, the model may directly update `wiki/` pages when requested. Future
rules can reintroduce stricter review or raw-source intake for selected content
types.

