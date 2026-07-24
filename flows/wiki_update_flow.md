# Wiki Update Flow

## Purpose

Convert raw source material into curated, reviewed, linkable wiki knowledge.

## Inputs

```text
raw source path
source type
optional title
current wiki catalog
related wiki pages
wiki update proposal schema
```

## Outputs

```text
draft_updates/*.md
optional wiki_update_proposal JSON
update report
human review decision
```

## Steps

```text
1. Add raw source using add_source.py.
2. Build or load catalog.
3. Select related wiki pages.
4. Generate draft update using prompts/wiki_update_prompt.md.
5. Suggest new pages, updated sections, and hyperlinks.
6. Validate proposed JSON against schemas/wiki_update_proposal.schema.json.
7. Run link checks using tools/wiki_tools.py check-links.
8. Human reviews and edits curated wiki pages.
9. Rebuild catalog.
10. Commit reviewed wiki changes to GitHub.
```

## Guardrails

```text
The model can write draft updates.
The model must not directly overwrite reviewed wiki pages.
Raw source text should not be treated as final truth.
Every important factual update should mention source provenance.
```

## Minimal Demo

```bash
python add_source.py raw/powdery_mildew.md --source-type disease --title "Powdery mildew"
python suggest_updates.py raw/sources/disease/<file>.md --provider openai --model gpt-4o-mini
python tools/wiki_tools.py check-links
python build_catalog.py
```

