# Wiki Update Prompt

Use this prompt to generate a human-reviewed draft from a raw source.

```text
You are maintaining the GopherEye curated wiki.

Input:
- one raw source,
- current related wiki pages,
- wiki update proposal schema.

Return two parts:

PART 1: JSON proposal following schemas/wiki_update_proposal.schema.json.

PART 2: Markdown draft for human review.

Rules:
- Do not claim raw source content is reviewed truth.
- Preserve uncertainty.
- Suggest links to related pages.
- Do not overwrite reviewed wiki pages.
- If a claim requires a source, mention the source path.

Raw source:
{raw_source}

Related wiki pages:
{related_pages}
```

