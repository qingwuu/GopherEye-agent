# System Records

Files in this folder are not meant to be sent to the model as prompt context.
They support joins, provenance, hidden labels, evaluation, and model-output
auditing.

Use these records to build the files in `../model_facing/`.

```text
image_manifest.example.jsonl
  Stable image asset records.

image_relationships.example.jsonl
  Plant/leaf/front-back pairing records.

reviewed_visual_labels.example.jsonl
  Human-reviewed labels that can export visual_intake SFT targets.

diagnosis_case_bank.example.jsonl
  Hidden case definitions and expected diagnosis outputs.

eval_oracles.example.jsonl
  Hidden pass/fail criteria for behavior tests.

model_outputs_audit.example.jsonl
  Raw and parsed model outputs. These are audit records, not ground truth.
```
