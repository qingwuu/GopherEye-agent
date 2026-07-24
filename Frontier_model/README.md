# GopherEye Frontier Model Agent System

This folder is an isolated prototype for a provider-switchable frontier-model
agent system. It reuses root-level wiki knowledge, system documentation,
schemas, session memory, image bookkeeping, and selected-page workflow, but
routes model calls through a provider registry.

It reuses the root-level wiki app (`chat.py`, `wiki/`, `schemas/`, and
`src/single_model_wiki/`) and does not replace `Cloud_model/cloud_chat.py`.

## Goal

```text
same app flow
-> switch OpenAI / Claude / Kimi / local Qwen by config
-> compare output quality, JSON reliability, cost metadata, and latency
-> preserve data for later evaluation and training
```

## Files

```text
frontier_chat.py
  CLI for one multi-turn agent session.

benchmark.py
  Runs the same cases against one or more model profiles.

frontier_agents/
  Provider adapters and the staged agent pipeline.

models.example.json
  Example model registry. Copy to a private config if you need local changes.

examples/eval_cases.example.jsonl
  Small benchmark cases using existing demo images.

sessions/
  Frontier session JSON outputs.

runs/
  Benchmark result JSON outputs.
```

## Model Profiles

The pipeline supports these provider types:

```text
openai_responses
  OpenAI Responses API with text and image inputs.

anthropic_messages
  Anthropic Messages API with text and image inputs.

openai_chat_compatible
  Kimi/Moonshot or another OpenAI-compatible Chat Completions endpoint.

local_wiki
  Existing local wiki/Qwen path.

echo
  No-credential smoke-test backend.
```

`models.example.json` defaults to `echo` so the CLI can run without API keys.

## Quick Smoke Test

From the repo root:

```bash
python -m Frontier_model.frontier_chat "How should the app handle data ingestion?" \
  --profile echo \
  --json
```

## Run With OpenAI

```bash
export OPENAI_API_KEY="..."

python -m Frontier_model.frontier_chat "Please inspect this grape leaf image." \
  --profile openai_frontier \
  --image-ref BLIP-Qwen/GopherEye/demo/healthy1/77f95a602b13b086a18cd789_teacher__77f95a602b13b086a18cd789.jpg \
  --selection-mode keyword \
  --image-context current \
  --json
```

## Run With Claude

```bash
export ANTHROPIC_API_KEY="..."

python -m Frontier_model.frontier_chat "Please inspect this grape leaf image." \
  --profile anthropic_frontier \
  --image-ref BLIP-Qwen/GopherEye/demo/downy1/b908ce7166e6989e301cf494_teacher__b908ce7166e6989e301cf494.jpg \
  --selection-mode keyword \
  --image-context current \
  --json
```

## Run With Kimi / Moonshot

Kimi is configured through the OpenAI-compatible Chat Completions adapter.
Update the model name and `supports_images` value in a private config after
verifying which Kimi model and modality you have access to.

```bash
export MOONSHOT_API_KEY="..."

python -m Frontier_model.frontier_chat "Explain the data ingestion plan for this app." \
  --profile kimi \
  --json
```

## Benchmark Multiple Profiles

```bash
python -m Frontier_model.benchmark \
  --cases Frontier_model/examples/eval_cases.example.jsonl \
  --profile openai_frontier \
  --profile anthropic_frontier \
  --profile qwen_local
```

Benchmark outputs are saved under:

```text
Frontier_model/runs/
```

## Agent Flow

```text
user message / image
-> router
-> vision agent if images are attached
-> retrieval agent over wiki or system pages
-> diagnosis/chat/data agent
-> schema-shaped JSON response
-> session memory update
-> saved session and benchmark outputs
```

The first version uses a deterministic router plus frontier model calls for the
semantic work. This keeps the flow inspectable and cheap while preserving the
multi-agent architecture.

For visual diagnosis, the pipeline prefers core botanical procedure pages from
`wiki/`, such as:

```text
wiki/procedures/whole_diagnosis_process.md
wiki/procedures/visual_observation_sequence.md
wiki/procedures/symptom_localization_procedure.md
wiki/workflows/evidence_sufficiency.md
wiki/workflows/front_back_leaf_process.md
```

The detailed plant diagnostic procedure should stay in `wiki/`. Frontier code
should reference those pages as context, not duplicate their botanical content
inside Python rules.
