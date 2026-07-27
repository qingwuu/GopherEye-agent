# Wiki Update Flow

## Purpose

Update wiki knowledge with the simplest useful path. For now, new or revised
knowledge can be placed directly under `wiki/` without first copying material
through `raw/` or generating a draft proposal.

## Inputs

```text
wiki target path
new or revised page content
current wiki catalog
optional source links or notes
```

## Outputs

```text
updated wiki/*.md page
rebuilt catalog
optional notes in the page frontmatter sources field
```

## Steps

```text
1. Choose or create the target page under wiki/.
2. Edit the page directly.
3. Add source links in frontmatter when useful.
4. Run link checks when links changed.
5. Rebuild catalog.
6. Commit wiki changes when ready.
```

## Optional Raw/Draft Path

Use `raw/`, `add_source.py`, `suggest_updates.py`, or
`schemas/wiki_update_proposal.schema.json` only when the source needs audit
history, lengthy review, or later training provenance.

## Guardrails

```text
Keep the edit scoped to the target wiki page.
Preserve uncertainty when the evidence is not settled.
Mention source provenance for important factual claims when available.
Do not add treatment recommendations unless a reviewed treatment resource is
available.
```

## Minimal Demo

```bash
python tools/wiki_tools.py check-links
python build_catalog.py
```

