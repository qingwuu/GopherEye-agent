# GopherEye Cloud Model Comparison

This folder is a parallel OpenAI API version of the root-level multi-turn VLM
chat. It reuses the same wiki app files without modifying them.

The goal is to compare:

```text
chat.py
  local Qwen2.5-VL

Cloud_model/cloud_chat.py
  OpenAI cloud vision model
```

Both flows reuse the same `wiki/` knowledge, prompt structure, session-memory
normalization, image re-attachment logic, and selected-page workflow. The main
difference is the model backend.

## Files

```text
cloud_chat.py
  OpenAI API multi-turn chat runner.

compare_sessions.py
  Utility to compare a local wiki session JSON with a cloud session JSON.

README.md
  This runbook.
```

Cloud sessions are saved under:

```text
Cloud_model/sessions/
```

Local sessions remain under:

```text
sessions/
```

## Environment

From the existing MSI environment:

```bash
conda activate gophereye-wiki-vlm
export PYTHONNOUSERSITE=1
cd ~/image-cli-bot
```

Install the OpenAI package if needed:

```bash
pip install openai python-dotenv
```

Set your OpenAI key:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Choose a cloud model:

```bash
export OPENAI_MODEL="gpt-4o-mini"
```

You can override the model with `--model` in every command.

## Build Wiki Catalog

Because this cloud flow reuses root-level `wiki/` knowledge files, build the existing
catalog first:

```bash
python build_catalog.py
```

## Run A Parallel Comparison

Use the same `SESSION_ID` for local and cloud. The sessions are stored in
different folders, so the IDs can match safely.

```bash
SESSION_ID=compare_leaf_001
```

### Turn 1: Adaxial Image Only

Local:

```bash
python chat.py "Please inspect this grape leaf image. Is the evidence sufficient for diagnosis?" \
  --session-id $SESSION_ID \
  --provider qwen-vl \
  --model Qwen/Qwen2.5-VL-7B-Instruct \
  --image-ref raw/images/leaf_001_adaxial.jpg \
  --selection-mode keyword \
  --image-context session \
  --max-new-tokens 900 \
  --json
```

Cloud:

```bash
python Cloud_model/cloud_chat.py "Please inspect this grape leaf image. Is the evidence sufficient for diagnosis?" \
  --session-id $SESSION_ID \
  --model $OPENAI_MODEL \
  --image-ref raw/images/leaf_001_adaxial.jpg \
  --selection-mode keyword \
  --image-context session \
  --max-new-tokens 900 \
  --json
```

### Turn 2: Follow-Up Without New Image

Local:

```bash
python chat.py "Look at the same image again. What additional image should the user provide?" \
  --session-id $SESSION_ID \
  --provider qwen-vl \
  --model Qwen/Qwen2.5-VL-7B-Instruct \
  --selection-mode keyword \
  --image-context session \
  --max-new-tokens 900 \
  --json
```

Cloud:

```bash
python Cloud_model/cloud_chat.py "Look at the same image again. What additional image should the user provide?" \
  --session-id $SESSION_ID \
  --model $OPENAI_MODEL \
  --selection-mode keyword \
  --image-context session \
  --max-new-tokens 900 \
  --json
```

### Turn 3: Add Abaxial Image

Local:

```bash
python chat.py "Here is the underside of the same leaf. Compare it with the previous image and update the diagnosis." \
  --session-id $SESSION_ID \
  --provider qwen-vl \
  --model Qwen/Qwen2.5-VL-7B-Instruct \
  --image-ref raw/images/leaf_001_abaxial.jpg \
  --selection-mode keyword \
  --image-context session \
  --max-new-tokens 1100 \
  --json
```

Cloud:

```bash
python Cloud_model/cloud_chat.py "Here is the underside of the same leaf. Compare it with the previous image and update the diagnosis." \
  --session-id $SESSION_ID \
  --model $OPENAI_MODEL \
  --image-ref raw/images/leaf_001_abaxial.jpg \
  --selection-mode keyword \
  --image-context session \
  --max-new-tokens 1100 \
  --json
```

## Compare Session Outputs

From the repository root:

```bash
python Cloud_model/compare_sessions.py \
  --local-session sessions/$SESSION_ID.json \
  --cloud-session Cloud_model/sessions/$SESSION_ID.json
```

Look for:

```text
attached_image_refs
missing_image_refs
assistant_message
current_diagnosis
evidence_present
evidence_missing
recommended_next_image
visual_intakes
selected_pages
```

## Important Notes

The cloud model cannot read a local file path by itself. `cloud_chat.py` resolves
local image paths and converts local files into base64 data URLs before sending
them to the OpenAI API.

For fair comparison, the cloud script reuses the same session-memory structure
as `chat.py`.
