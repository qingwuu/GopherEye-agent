# GopherEye App Workspace

This root folder is the GopherEye app workspace.
The previous nested wiki prototype folders have been moved to the repository root.
Model training and historical GopherEye code live under `BLIP-Qwen/`.

## Wiki/System Boundary

```text
wiki/
  Plant, grape, grape leaf, disease evidence, diagnosis procedure, routine,
  expert case, and reviewed treatment-resource knowledge.

system/
  Model, provider, agent, schema/tool, source-ingestion, data-memory, and
  implementation documentation.
```

The `wiki/` catalog should not contain model/provider/system architecture pages.
Those belong in `system/` or in executable folders such as `Frontier_model/`.

The goal of this version is to test a simpler LLM Wiki design:

```text
one language model
-> reads the wiki catalog
-> selects relevant wiki pages
-> reads selected markdown files
-> answers the question
-> optionally drafts wiki updates from raw sources
```

There is no embedding model in the default flow. This makes the wiki app useful for
comparing against the existing `Wiki` implementation, where retrieval and answer
generation are separated.

## Current Development Scope

The workspace separates the app into strict functional layers:

```text
raw/
  preserved source material

wiki/
  curated grape leaf domain knowledge and app-facing routines

system/
  implementation and model/provider documentation

schemas/
  machine-readable JSON contracts

prompts/
  reusable model instructions

tools/
  deterministic file/search/validation actions

flows/
  ordered agentic workflows

eval/
  behavior tests and regression cases

dataset/
  proposed dataset structures and example JSONL rows for VLM-Wiki training,
  evaluation, and model-output auditing
```

Read these first:

```text
DEVELOPMENT_GUIDE.md
system/README.md
dataset/README.md
wiki/index.md
Frontier_model/README.md
```

## Main Difference From `Wiki`

```text
Wiki:
  embedding/search model finds relevant chunks
  answer model writes the final response

This wiki app:
  the same model selects relevant files and writes the final response
```

This means the single-model path is easier to understand, but it may be slower, less stable on
large wikis, and more dependent on the reasoning ability of the chosen model.

## Recommended Model

Use one instruction model for the whole process:

```text
Local:
  Qwen/Qwen2.5-7B-Instruct
  Qwen/Qwen2.5-3B-Instruct

API:
  gpt-4o-mini
  gpt-4o
```

## Quick Start From This Folder

You said your server prompt is:

```bash
(gophereye-wiki) shen0574@agc08 [~/Wiki]
```

Enter the repo root first:

```bash
cd ~/image-cli-bot
```

Then install dependencies:

```bash
pip install -U -r requirements.txt
```

Build the lightweight catalog:

```bash
python build_catalog.py
```

Ask with a local Qwen model:

```bash
python ask.py "How should GopherEye use past, current, and future leaf observations?" \
  --provider transformers \
  --model Qwen/Qwen2.5-7B-Instruct
```

Ask with OpenAI:

```bash
export OPENAI_API_KEY="..."
python ask.py "How should GopherEye use past, current, and future leaf observations?" \
  --provider openai \
  --model gpt-4o-mini
```

## Selection Modes

Default mode:

```bash
python ask.py "question" --selection-mode model
```

The same model first chooses relevant wiki files from the catalog, then answers
using only those files.

Full context mode:

```bash
python ask.py "question" --selection-mode full
```

This sends every curated wiki page to the same model. It is simplest, but only
works while the wiki is small enough to fit into the model context.

## Add A Source

```bash
python add_source.py path/to/pi_meeting.md \
  --source-type meeting \
  --title "PI meeting"
```

This copies the source into `raw/sources/` and records it in
`raw/source_manifest.jsonl`.

## Draft Wiki Updates

```bash
python suggest_updates.py raw/sources/meeting/file.md \
  --provider transformers \
  --model Qwen/Qwen2.5-7B-Instruct
```

The output is written to `draft_updates/`. It does not edit curated wiki pages.

## Tool Examples

```bash
python tools/wiki_tools.py list-pages
python tools/wiki_tools.py search "powdery mildew"
python tools/wiki_tools.py check-links
python tools/wiki_tools.py validate-json schemas/diagnosis_output.schema.json result.json
```

## Multi-Turn Chat

Start a new chat session:

```bash
python chat.py "A user uploaded an upper-side grape leaf image with pale yellow spots. What should we ask next?" \
  --provider transformers \
  --model Qwen/Qwen2.5-7B-Instruct \
  --selection-mode model
```

Continue the same session by reusing the printed `session_id`:

```bash
python chat.py "Why do you need the underside?" \
  --session-id session_YYYYMMDD_HHMMSS \
  --provider transformers \
  --model Qwen/Qwen2.5-7B-Instruct
```

Session files are stored under:

```text
sessions/*.json
```

Each session keeps a complete transcript plus a compact `short_term_memory`
object that is inserted into the next turn prompt.

Code owns all bookkeeping IDs. `chat.py` assigns and records `image_id`,
`visual_intake_id`, turn IDs, paths, and timestamps in the session JSON. The VLM
is asked only for content-bearing updates such as side label, image quality,
visible symptoms, evidence sufficiency, and the user-facing answer. The session
also stores `id_history` so generated names can be reused and collision-checked
across later turns.

Run a multi-turn VLM session with image pixels:

```bash
python chat.py "Please inspect this grape leaf image and tell me what evidence is missing." \
  --provider qwen-vl \
  --model Qwen/Qwen2.5-VL-7B-Instruct \
  --image-ref raw/images/user_leaf_001.jpg \
  --selection-mode keyword \
  --image-context session
```

Continue the same session and re-send the saved image pixels to the VLM:

```bash
python chat.py "Please look at the same image again. Why do you need the underside?" \
  --session-id session_YYYYMMDD_HHMMSS \
  --provider qwen-vl \
  --model Qwen/Qwen2.5-VL-7B-Instruct \
  --selection-mode keyword \
  --image-context session
```

Add a new image on any later turn:

```bash
python chat.py "Here is the underside of the same leaf. Compare it with the previous image." \
  --session-id session_YYYYMMDD_HHMMSS \
  --provider qwen-vl \
  --model Qwen/Qwen2.5-VL-7B-Instruct \
  --image-ref raw/images/user_leaf_001_abaxial.jpg \
  --selection-mode keyword \
  --image-context session
```

Attach multiple new images in one turn:

```bash
python chat.py "Compare these two new images with the earlier one." \
  --session-id session_YYYYMMDD_HHMMSS \
  --provider qwen-vl \
  --model Qwen/Qwen2.5-VL-7B-Instruct \
  --image-ref raw/images/leaf_closeup.jpg \
  --image-ref raw/images/leaf_context.jpg \
  --image-context session \
  --max-attached-images 8
```

`--image-context session` means the code reads image paths stored in
`short_term_memory.known_images`, converts local files to `file://...` URIs, and
attaches the image pixels to the Qwen2.5-VL model call. The model itself does not
open paths; Python does.

Image context options:

```text
session
  Attach current-turn images plus saved session images, up to --max-attached-images.

current
  Attach only images passed in this turn with --image-ref.

none
  Do not attach image pixels; use only stored visual_intakes and text memory.
```

## Flow Documents

```text
flows/wiki_update_flow.md
flows/image_diagnosis_flow.md
flows/followup_chat_flow.md
```

These describe the practical meaning of agentic behavior in this project.
