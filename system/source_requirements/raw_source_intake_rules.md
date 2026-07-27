---
title: Raw Source Intake Rules
page_type: source_requirement
review_status: draft
last_updated: 2026-07-27
sources: []
---

# Raw Source Intake Rules

Raw source material is optional preserved evidence. It can include expert notes,
extension documents, papers, annotated examples, meeting notes, treatment
guides, diagnosis scripts, and dialog sketches.

For now, wiki updates can be written directly under `wiki/` without first
copying the material into `raw/`. Use `raw/` only when provenance, audit trail,
or later training reuse matters.

Curated wiki pages should still avoid unsupported overclaiming. If a claim is
uncertain, mark it as uncertain in the wiki page.

## Source Types

Use these source types only when adding optional material with `add_source.py`:

```text
expert_information
expert_examples
treatment_resources
diagnosis_scripts
procedure_notes
dialog_trees
disease_information
meeting
paper
note
```

Examples:

```bash
python add_source.py path/to/expert_notes.md --source-type expert_information --title "Expert meeting notes"
python add_source.py path/to/powdery_case.md --source-type expert_examples --title "Powdery mildew front-back example"
python add_source.py path/to/treatment_guide.pdf --source-type treatment_resources --title "Reviewed treatment guide"
```

## Required Metadata

When using the optional raw-source path, record:

```text
source title
source type
author or organization
date published or date received
who collected it
review status
related disease or workflow
whether it can be used for model-facing answers
```

## Review States

If a source needs formal review, use this progression:

```text
raw_collected
needs_expert_review
reviewed_for_wiki
reviewed_for_model_training
deprecated
```

Simple wiki edits do not need to pass through this state machine. Formal review
states are for sources or claims that need auditability.

## Manual Source Folders

Manual collection folders:

- [Expert information raw folder](../../raw/sources/expert_information/README.md)
- [Expert examples raw folder](../../raw/sources/expert_examples/README.md)
- [Treatment resources raw folder](../../raw/sources/treatment_resources/README.md)
- [Diagnosis scripts raw folder](../../raw/sources/diagnosis_scripts/README.md)
- [Procedure notes raw folder](../../raw/sources/procedure_notes/README.md)
- [Dialog trees raw folder](../../raw/sources/dialog_trees/README.md)
- [Disease information raw folder](../../raw/sources/disease_information/README.md)

See [Wiki Update System](../workflows/wiki_update_system.md) and
[Manual Source Backlog](manual_source_backlog.md).
