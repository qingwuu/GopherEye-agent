# GopherEye Frontier Model Agent System

This folder is an isolated prototype for a provider-switchable frontier-model
agent system. It reuses root-level wiki knowledge, system documentation,
schemas, session memory, image bookkeeping, and selected-page workflow, but
routes model calls through a provider registry.

It reuses the root-level wiki knowledge, schemas, and shared runtime helpers.

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

frontier_agents/
  Provider adapters and the staged agent pipeline.

models.example.json
  Example model registry. Copy to a private config if you need local changes.
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
  --image-ref C:/path/to/your/grape_leaf_image_001.jpg \
  --selection-mode keyword \
  --image-context current \
  --json
```

## Run With Claude

```bash
export ANTHROPIC_API_KEY="..."

python -m Frontier_model.frontier_chat "Please inspect this grape leaf image." \
  --profile anthropic_frontier \
  --image-ref C:/path/to/your/grape_leaf_image_001.jpg \
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

Frontier session JSON outputs are saved outside this code folder under:

```text
sessions/frontier/
```

By default the chat agent auto-sizes its selected-page budget from the current
question complexity. Use `--max-selected-files N` only when you want to force a
manual context limit for a specific run.

## Agent Flow

```text
user message / image
-> router
-> vision agent if images are attached
-> retrieval agent over wiki or system pages
-> diagnosis/chat response agent
-> thin assistant envelope JSON response
-> session memory update
-> saved session output
```

The first version uses a deterministic router plus frontier model calls for the
semantic work. This keeps the flow inspectable and cheap while preserving the
multi-agent architecture.

The runtime now uses one assistant envelope schema for all roles:

```text
schemas/envelopes/assistant_envelope.schema.json
```

Role profiles decide which payload constraints apply. For example, visual
diagnosis requires visual memory fields and validates `visual_intakes` against
`schemas/visual_intake.schema.json`; data-management turns use the same
envelope but do not receive write permission to wiki or ground-truth data.

For visual diagnosis, the pipeline prefers core botanical procedure pages from
`wiki/`, such as:

```text
wiki/procedures/diagnosis_sop.md
wiki/procedures/image_and_evidence_sop.md
wiki/disease/powdery_mildew/index.md
wiki/disease/downy_mildew/index.md
wiki/disease/healthy/index.md
wiki/disease/others/index.md
```

The detailed plant diagnostic procedure should stay in `wiki/`. Frontier code
should reference those pages as context, not duplicate their botanical content
inside Python rules.
