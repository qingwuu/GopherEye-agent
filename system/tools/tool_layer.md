---
title: Tool Layer
page_type: tool_explanation
review_status: draft
last_updated: 2026-07-12
sources: []
---

# Tool Layer

Tools are deterministic capabilities that the model can request but not replace.

## Examples

```text
read wiki page
search wiki pages
check markdown links
validate JSON
load image
save diagnosis output
create Git diff
create Git commit after approval
```

## Tool Principle

The model proposes actions. Tools perform actions under constraints.

For example:

```text
Model proposes a wiki update.
Tool writes to draft_updates/.
Human reviews.
Only reviewed changes are committed.
```

## Current Tool File

```text
tools/wiki_tools.py
```

See [Wiki Update System](../workflows/wiki_update_system.md).

