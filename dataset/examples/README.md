# Dataset Examples

This directory is split by whether a record is model-facing.

```text
model_facing/
  Examples that can be converted directly into model prompts, labels, or
  input-only evaluation prompts.

system_records/
  Internal bookkeeping, reviewed labels, hidden expected outputs, audit logs,
  and asset relationship records. These records are used by loaders, validators,
  and evaluators, but should not be pasted into model prompts as-is.
```

Important rule:

```text
The model learns task behavior and structured outputs.
The application owns IDs, paths, timestamps, audit logs, joins, validation, and
dataset bookkeeping.
```

All `.jsonl` files in these subdirectories are valid JSONL: one JSON object per
line.
