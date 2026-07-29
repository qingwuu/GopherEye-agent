# GopherEye Data Agent

This is the independent GopherEye Data Agent runtime. It is separate from
`Frontier_model/` and does not use the old session-archive data pipeline.

## Purpose

```text
natural-language data request
-> operation plan schema
-> deterministic executor
-> optional vision / annotation / dataset tools
-> artifacts + audit logs
```

The LLM plans. Python executes. Ground-truth labels still require human review.

## Quick Commands

```bash
python -m gophereye_data_agent doctor
python -m gophereye_data_agent plan "segment pending images and label grape disease"
python -m gophereye_data_agent run "segment pending images and label grape disease"
python -m gophereye_data_agent modify /corrections/group_id plot_a --apply
python -m gophereye_data_agent segment --backend yolo
python -m gophereye_data_agent segment --backend sam2
python -m gophereye_data_agent label --provider heuristic
python -m gophereye_data_agent embed
python -m gophereye_data_agent augment --count-per-image 3
python -m gophereye_data_agent export-label-studio
```

`run` is dry-run for JSON modification by default. Use `--apply` only when you
intend to write instance JSON.

Most commands accept `--workspace-root` and `--job-root`. The default workspace
is `gophereye_data_workspace/`, which is reserved for GopherEye Data Agent
instances, jobs, and artifacts.

## Optional Integrations

The core CLI uses Typer and Pydantic. External tools are optional:

```text
OpenAI Agents SDK
MCP
Ultralytics YOLO
SAM2
Albumentations
FiftyOne
Label Studio
Hugging Face Hub
MLflow
DVC
lakeFS
LanceDB
DuckDB
```

Missing integrations return `not_available` instead of crashing the job.

SAM2 needs an importable `sam2` package plus either:

```bash
python -m gophereye_data_agent segment --backend sam2 --model-cfg <cfg> --checkpoint <checkpoint>
```

or environment variables:

```bash
GOPHEREYE_SAM2_PRETRAINED=facebook/sam2-hiera-large
GOPHEREYE_SAM2_MODEL_CFG=configs/sam2.1/sam2.1_hiera_l.yaml
GOPHEREYE_SAM2_CHECKPOINT=checkpoints/sam2.1_hiera_large.pt
```

## Runtime Outputs

```text
gophereye_data_workspace/jobs/
  dagent_<id>/
    operation_plan.json
    resolved_targets.json
    job_result.json
    audit_events.jsonl
    backups/
    artifacts/
```

## MVP Operation Order

```text
LLM planner schema
-> modify instance JSON
-> generic segmentation
-> grape disease label proposal
-> embedding
-> augmentation
```

Disease-specific segmentation refinement can be added after labeling when the
first generic masks and disease proposal are available.
