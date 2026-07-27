# Wiki Update Prompt

Use this prompt only for the optional raw/draft workflow. Simple updates can be
made directly in `wiki/` without generating a proposal first.

```text
You are maintaining the GopherEye wiki.

Input:
- one source or note,
- current related wiki pages,
- optional wiki update proposal schema.

Return two parts:

PART 1: JSON proposal following schemas/wiki_update_proposal.schema.json.

PART 2: Markdown draft for human review.

Rules:
- Write the JSON proposal free-text fields and markdown draft in English only.
- Do not claim source content is reviewed truth unless the source is actually
  reviewed.
- Preserve uncertainty.
- Suggest links to related pages.
- For the optional draft workflow, do not overwrite wiki pages.
- If a claim requires a source, mention the source path.

Source or note:
{raw_source}

Related wiki pages:
{related_pages}
```

