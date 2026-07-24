---
title: Raw Source Intake Rules
page_type: source_requirement
review_status: draft
last_updated: 2026-07-23
sources: []
---

# Raw Source Intake Rules

Raw source material is preserved evidence. It can include expert notes,
extension documents, papers, annotated examples, meeting notes, treatment
guides, diagnosis scripts, and dialog sketches.

Curated wiki pages should summarize reviewed source material. They should not
copy raw material directly into app-facing rules without review.

## Source Types

Use these source types when adding material with `add_source.py`:

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

Every source should record:

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

Use this progression:

```text
raw_collected
needs_expert_review
reviewed_for_wiki
reviewed_for_model_training
deprecated
```

Only `reviewed_for_wiki` or stronger material should become curated wiki
knowledge.

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
