# Data Agent Runtime

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
