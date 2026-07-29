# Session Archive Runtime

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

Archive all capture-worthy Frontier session turns, generate review templates,
copy local images when available, rebuild queue indexes, and rebuild the
reviewed dataset index:

```bash
python tools/session_archiver.py
```

The explicit form is:

```bash
python tools/session_archiver.py archive-all
```

By default this scans:

```text
sessions/frontier/*.json
```

It archives visual/image turns only. Pure chat turns are skipped unless the
debug option `--include-all-turns` is used.

List records waiting for human review:

```bash
python tools/session_archiver.py list-pending
```

Human review first version:

```text
1. Copy human_review.template.json to human_review.submitted.json.
2. Edit reviewer, reviewed_at, review_status, decision, and human_reviewed_label.
3. Run the archivist again to refresh queues and reviewed_dataset_index.jsonl.
```

```bash
python tools/session_archiver.py
```

Single-turn capture and manual index commands still exist for debugging:

```bash
python tools/session_archiver.py capture-turn --session-path sessions/frontier/<session>.json
python tools/session_archiver.py rebuild-indexes
python tools/session_archiver.py build-reviewed-index
```

Validate one instance:

```bash
python tools/session_archiver.py validate-instance <instance_id>
```
