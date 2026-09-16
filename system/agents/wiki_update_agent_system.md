---
title: Wiki Update Agent System
page_type: system_page
review_status: draft
last_updated: 2026-07-31
sources: []
---

# Wiki Update Agent System

The Wiki Update Agent is an isolated source-backed maintenance agent for
`wiki/`. It does not share runtime state with the frontier chat agent or the
data agent.

Implementation entry point:

```text
gophereye_wiki_update_agent/
wiki_update.py
```

## Boundary

```text
owns:
  web-search-backed wiki update runs
  selected wiki page reads
  minimal append-only wiki edit operations
  automatic catalog rebuild after applied updates
  run artifacts under wiki_update_agent_workspace/

does not own:
  frontier chat sessions
  visual diagnosis session memory
  data agent manifests, labels, embeddings, or augmentations
  human ground-truth labels
```

## Flow

```text
user update request
-> priority-source web search using manually maintained source file
-> broad web search beyond priority sources
-> compact research facts and sources
-> build/read wiki catalog
-> select candidate wiki pages
-> read current page content before final target decision
-> emit restricted wiki operations
-> apply minimal updates
-> rebuild catalog/wiki
-> save research, proposal, and run summary
```

## Edit Constraints

The model may not rewrite whole pages. The runtime accepts only restricted
operations:

```text
append_under_heading
append_to_file
create_page, only when explicitly enabled
```

The preferred operation is `append_under_heading` on a page the model has read.
Content should stay concise, source-backed, and non-duplicative.

Treatment guidance remains conservative. Do not add product rates, legal-use
instructions, or chemical label advice unless an authoritative current source
supports the exact wording and the selected target is a treatment page.

## Priority Sources

Manual priority websites live in:

```text
gophereye_wiki_update_agent/priority_sources.json
```

They are searched first so preferred extension, university, government, or
reviewed sources get early attention. They are not an exclusive allowlist. The
agent must still run broad web search afterward when web search is enabled.
