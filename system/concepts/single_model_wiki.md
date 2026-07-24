# Single-Model Wiki Concept

## Definition

A single-model wiki is an LLM Wiki where one instruction model handles the whole workflow:

```text
source ingestion reasoning
page selection
answer generation
update drafting
```

It does not require a separate embedding model.
The system may still keep a lightweight catalog of page titles, paths, headings, and previews, but that catalog is plain text, not a vector index.

