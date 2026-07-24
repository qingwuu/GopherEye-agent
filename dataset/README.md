# GopherEye VLM-Wiki Dataset Design

This folder documents the dataset structure for the VLM-first, wiki-grounded,
multi-turn GopherEye diagnostic workflow.

The important design rule is separation:

```text
model-facing examples
  prompt/label/eval-input records that can be converted into model calls

system records
  assets, IDs, joins, hidden labels, audit logs, and evaluation oracles
```

The model should learn diagnostic behavior and structured outputs. The
application should own paths, IDs, timestamps, joins, validation, storage, and
audit trails.

## Example Layout

```text
examples/
  README.md

  model_facing/
    visual_intake_sft.example.jsonl
    diagnosis_sft.example.jsonl
    chat_memory_sft.example.jsonl
    behavior_eval_inputs.example.jsonl

  system_records/
    image_manifest.example.jsonl
    image_relationships.example.jsonl
    reviewed_visual_labels.example.jsonl
    diagnosis_case_bank.example.jsonl
    eval_oracles.example.jsonl
    model_outputs_audit.example.jsonl
```

All `.jsonl` files are valid JSONL: one JSON object per line.

## Model-Facing Files

### `visual_intake_sft.example.jsonl`

Purpose:

```text
Train/evaluate the VLM's first structured look at an image.
```

Target task:

```text
image pixels + compact task context -> visual_intake JSON
```

The model learns:

```text
is_leaf_image
image quality
leaf side: adaxial, abaxial, mixed, uncertain, not_leaf
visible structures
visible symptoms
candidate diseases
short intake summary
```

### `diagnosis_sft.example.jsonl`

Purpose:

```text
Train/evaluate wiki-grounded diagnosis and evidence sufficiency.
```

Target task:

```text
visual_intakes + short_term_memory + selected wiki refs + user question
-> diagnosis_output JSON
```

This is the key app-facing training file.

### `chat_memory_sft.example.jsonl`

Purpose:

```text
Train/evaluate follow-up dialogue and structured rolling memory updates.
```

Target task:

```text
recent transcript + current short_term_memory + current message/images
-> assistant_message + memory_update
```

The model should use `image_order` for image-specific updates. It should not
generate image IDs, file paths, session IDs, timestamps, or filenames.

### `behavior_eval_inputs.example.jsonl`

Purpose:

```text
Input-only regression tests.
```

These records are safe to send to the model during evaluation. Hidden expected
fields and pass/fail criteria are stored in
`system_records/eval_oracles.example.jsonl`.

## System Record Files

### `image_manifest.example.jsonl`

Tracks stable image assets. This file is for loaders and dataset joins, not for
model prompts.

### `image_relationships.example.jsonl`

Tracks plant/leaf/observation/front-back relationships, such as whether two
images are the adaxial and abaxial views of the same leaf.

### `reviewed_visual_labels.example.jsonl`

Stores human-reviewed visual labels. Export scripts can convert these records
into `model_facing/visual_intake_sft.example.jsonl`.

### `diagnosis_case_bank.example.jsonl`

Stores hidden diagnosis case definitions and expected diagnosis outputs. Export
scripts can convert these records into `model_facing/diagnosis_sft.example.jsonl`.

### `eval_oracles.example.jsonl`

Stores hidden regression-test criteria:

```text
must_include
must_not_include
expected_fields
pass_criteria
```

These criteria should not be sent to the model during evaluation.

### `model_outputs_audit.example.jsonl`

Stores raw outputs from teacher models, legacy models, and future fine-tuned
models. These records are for auditing and mining future examples. They should
not overwrite ground truth labels.

## Recommended Build Order

```text
1. system_records/image_manifest
2. system_records/image_relationships
3. system_records/reviewed_visual_labels
4. model_facing/visual_intake_sft
5. system_records/diagnosis_case_bank
6. model_facing/diagnosis_sft
7. model_facing/behavior_eval_inputs + system_records/eval_oracles
8. model_facing/chat_memory_sft
9. system_records/model_outputs_audit
```

Start small. A small, reviewed dataset with consistent schema is more useful
than a large dataset that mixes IDs, labels, model outputs, and hidden answers.

## Runtime Responsibility Split

Code handles:

```text
session JSON creation
session/turn/image/visual_intake ID assignment
image path resolution
image re-attachment
schema validation
model output storage
database writes
joining system records into model-facing examples
```

The model handles:

```text
visual interpretation
wiki-grounded reasoning
evidence sufficiency judgment
schema-following output
content-bearing short_term_memory update proposal
professional user-facing answer
```

IDs and paths should not be part of the model learning target. Runtime code
assigns stable IDs, records them in `session.id_history`, and maps model
`image_order` updates back to the correct `image_id`.
