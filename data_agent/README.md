# Data Agent Runtime

This folder is the runtime sidecar for collecting, reviewing, and indexing
GopherEye data instances.

It is separate from `wiki/`. Unreviewed model labels and raw model outputs do
not become wiki knowledge.

## Boundary

```text
existing router / prompt builder / vision-diagnosis agent
  produce normal session output

tools/data_agent.py
  reads existing session output
  creates upload records
  writes machine_generated / unreviewed model labels
  creates human review JSON templates
  imports reviewed JSON
  builds reviewed dataset indexes
```

The Data Agent does not make new LLM calls in this first version.

## Runtime Layout

```text
data_agent/
  instances/
    inst_<id>/
      manifest.json
      upload_record.json
      model_label.json
      human_review.template.json
      human_review.submitted.json
      selected_pages.json
      raw_model_output.json
      final_model_output.json
      session_excerpt.json
      audit_events.jsonl

  uploads/images/
    <image_id>/
      optional copied image files

  indexes/
    uploads.jsonl
    model_labels.jsonl
    human_reviews.jsonl
    reviewed_dataset_index.jsonl

  review_queue/
    pending.jsonl
    completed.jsonl
```

Each instance folder is the durable unit. It links the images, model output,
selected context pages, review file, and audit log for one captured session
turn.

## Commands

Create the runtime folders:

```bash
python tools/data_agent.py init
```

Capture the latest visual diagnosis turn from an existing Frontier session:

```bash
python tools/data_agent.py capture-turn --session-path Frontier_model/sessions/<session>.json
```

Optionally copy local image files into `data_agent/uploads/images/`:

```bash
python tools/data_agent.py capture-turn --session-path Frontier_model/sessions/<session>.json --copy-images
```

List records waiting for human review:

```bash
python tools/data_agent.py list-pending
```

Human review first version:

```text
1. Copy human_review.template.json to human_review.submitted.json.
2. Edit reviewer, reviewed_at, review_status, decision, and human_reviewed_label.
3. Import the submitted JSON with the CLI.
```

```bash
python tools/data_agent.py import-review --instance-id <instance_id>
```

Build the ground-truth dataset index from imported human reviews:

```bash
python tools/data_agent.py build-reviewed-index
```

Validate one instance:

```bash
python tools/data_agent.py validate-instance <instance_id>
```

## Status Rules

```text
model_label
  generation_status = machine_generated
  review_status = unreviewed
  is_ground_truth = false

human_review.submitted.json
  review_status = reviewed
  decision = accept_model_label | correct_label | reject_not_leaf |
             reject_unusable_image | needs_more_evidence

reviewed_dataset_index.jsonl
  includes only accept_model_label and correct_label
  is_ground_truth = true
  wiki_ingestion_allowed = false
```

Insufficient evidence is still recorded. It remains useful for review queues,
next-image policy, active learning, and future data collection, but it is not
treated as a reviewed disease label unless a human reviewer explicitly confirms
an ingestible label.
