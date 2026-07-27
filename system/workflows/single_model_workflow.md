# Single-Model Workflow

## Ask Flow

```text
user question
-> build or load catalog
-> same model selects relevant page IDs
-> code reads selected markdown files
-> same model answers from selected files
```

The model does not see embeddings. It sees a plain-text catalog.

## Full Context Mode

Full context mode sends all curated wiki pages to the same model:

```bash
python ask.py "question" --selection-mode full
```

Use this only while the wiki is small.

## Model Selection Mode

Model selection mode first asks the same model to choose page IDs:

```bash
python ask.py "question" --selection-mode model
```

This is the default mode.

## Keyword Mode

Keyword mode does not use a model for selection:

```bash
python ask.py "question" --selection-mode keyword
```

This is only a fallback or debugging mode.

## Update Flow

```text
new or revised wiki knowledge
-> target wiki page is edited directly
-> catalog is rebuilt
```

The older raw-source and draft-update path remains available for updates that
need provenance tracking or formal review, but it is not required for simple
wiki edits.

