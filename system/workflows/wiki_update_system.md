---
title: Wiki Update System
page_type: workflow_page
review_status: draft
last_updated: 2026-07-12
sources: []
---

# Wiki Update System

The wiki update system converts raw sources into curated project knowledge.

## Separation

```text
raw source
-> draft update
-> human review
-> curated wiki page
-> catalog rebuild
-> versioned commit
```

Raw sources should not directly overwrite curated wiki pages.

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
read a raw source
identify related wiki pages
draft page updates
suggest hyperlinks
check links
prepare a review report
```

The model proposes updates. The workflow and tools enforce review and safety.

