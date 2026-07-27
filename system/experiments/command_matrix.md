# GopherEye Experiment Command Matrix

This file is a PowerShell-oriented command matrix for end-to-end experiments.
Run commands from the repository root.

## 0. Setup

```powershell
Set-Location "<repo_root>"

python -m pip install -U -r requirements.txt
python -m pip install -U -r Frontier_model\requirements.txt

python build_catalog.py
python build_catalog.py --wiki-dir system --catalog-dir Frontier_model\catalog\system

python tools\wiki_tools.py check-links
python -m compileall chat.py Frontier_model tools\data_agent.py
python tools\data_agent.py init

New-Item -ItemType Directory -Force experiment_logs
```

Optional API keys:

```powershell
$env:OPENAI_API_KEY = "..."
$env:ANTHROPIC_API_KEY = "..."
$env:MOONSHOT_API_KEY = "..."
```

Reusable external image paths:

```powershell
$LeafImage1 = "C:\path\to\your\grape_leaf_image_001.jpg"
$LeafImage2 = "C:\path\to\your\grape_leaf_image_002.jpg"
```

Use absolute local paths for images outside this repository. If a path contains
spaces, keep the quotes around the variable value.

If you only want to test one image, point both variables to the same file:

```powershell
$LeafImage2 = $LeafImage1
```

Verify that Python will receive existing local files:

```powershell
Test-Path $LeafImage1
Test-Path $LeafImage2
Resolve-Path $LeafImage1
Resolve-Path $LeafImage2
```

Create a benchmark case file from your external images:

```powershell
$CaseImage1 = (Resolve-Path $LeafImage1).Path
$CaseImage2 = (Resolve-Path $LeafImage2).Path

$Cases = @(
  @{
    case_id = "external_leaf_001"
    message = "Please inspect this grape leaf image. Is the evidence sufficient for diagnosis?"
    image_refs = @($CaseImage1)
    expected = @{ should_parse_json = $true; should_request_missing_evidence_when_needed = $true }
  },
  @{
    case_id = "external_leaf_002"
    message = "Inspect this grape leaf image and explain what next image would improve the diagnosis."
    image_refs = @($CaseImage2)
    expected = @{ should_parse_json = $true; should_request_missing_evidence_when_needed = $true }
  },
  @{
    case_id = "data_ingestion_question"
    message = "How should this app ingest user-uploaded grape leaf images and expert labels for future evaluation?"
    image_refs = @()
    expected = @{ task_type = "data_management" }
  }
)

$Cases | ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 10 } | Set-Content -Encoding utf8 experiment_logs\external_eval_cases.jsonl
Get-Content experiment_logs\external_eval_cases.jsonl
```

## 1. Inspect CLI And Knowledge State

```powershell
python ask.py --help
python chat.py --help
python -m Frontier_model.frontier_chat --help
python -m Frontier_model.benchmark --help
python tools\data_agent.py --help

python tools\wiki_tools.py list-pages
python tools\wiki_tools.py search "downy mildew"
python tools\wiki_tools.py read wiki\procedures\whole_diagnosis_process.md
python tools\wiki_tools.py read system\data\data_agent_workflow.md
```

## 2. Router Smoke Tests

These use `echo`, so they do not call an external model.

```powershell
python -m Frontier_model.frontier_chat "How should this app ingest user-uploaded grape leaf images into data collection and human review?" --profile echo --selection-mode keyword --json
python -m Frontier_model.frontier_chat "Design the data collection and human review workflow." --profile echo --selection-mode keyword --json

python -m Frontier_model.frontier_chat "Please inspect this grape leaf image and say whether evidence is sufficient." --profile echo --image-ref $LeafImage1 --selection-mode keyword --image-context current --json

python -m Frontier_model.frontier_chat "What evidence is required before diagnosing grape leaf disease?" --profile echo --selection-mode keyword --json
python -m Frontier_model.frontier_chat "Explain which paper or source content can enter the wiki." --profile echo --selection-mode keyword --json
python -m Frontier_model.frontier_chat "Summarize the current app architecture boundary." --profile echo --selection-mode keyword --json
```

Record from JSON output:

```text
session_path
session_id
route.task_type
route.selected_agent_path
context_label
selected_pages
envelope_valid
envelope_role_profile
```

## 3. Frontier Manual Runs

Data-management or system-design chat:

```powershell
python -m Frontier_model.frontier_chat "Design the Data Agent workflow for uploads, model labels, human review, and reviewed dataset indexing." --profile openai_frontier --selection-mode keyword --json
python -m Frontier_model.frontier_chat "Design the Data Agent workflow for uploads, model labels, human review, and reviewed dataset indexing." --profile anthropic_frontier --selection-mode keyword --json
python -m Frontier_model.frontier_chat "Design the Data Agent workflow for uploads, model labels, human review, and reviewed dataset indexing." --profile kimi --selection-mode keyword --json
python -m Frontier_model.frontier_chat "Design the Data Agent workflow for uploads, model labels, human review, and reviewed dataset indexing." --profile qwen_local --selection-mode keyword --json
```

Visual diagnosis:

```powershell
python -m Frontier_model.frontier_chat "Please inspect this grape leaf image. Give a provisional diagnosis only if evidence is sufficient, and say what image is missing." --profile openai_frontier --image-ref $LeafImage1 --selection-mode keyword --image-context current --json
python -m Frontier_model.frontier_chat "Please inspect this grape leaf image. Give a provisional diagnosis only if evidence is sufficient, and say what image is missing." --profile openai_balanced --image-ref $LeafImage1 --selection-mode keyword --image-context current --json
python -m Frontier_model.frontier_chat "Please inspect this grape leaf image. Give a provisional diagnosis only if evidence is sufficient, and say what image is missing." --profile anthropic_frontier --image-ref $LeafImage1 --selection-mode keyword --image-context current --json
python -m Frontier_model.frontier_chat "Please inspect this grape leaf image. Give a provisional diagnosis only if evidence is sufficient, and say what image is missing." --profile qwen_local --image-ref $LeafImage1 --selection-mode keyword --image-context current --json
```

Kimi in `models.example.json` is text-only, so use it for chat/data tests, not image-pixel tests.

## 4. Frontier Multi-Turn Image Runs

Use a fixed `--session-id` when you want a repeatable experiment folder name.

```powershell
python -m Frontier_model.frontier_chat "Turn 1: inspect this grape leaf image and list evidence present and missing." --session-id exp_frontier_leaf_001 --profile openai_frontier --image-ref $LeafImage1 --selection-mode keyword --image-context current --json

python -m Frontier_model.frontier_chat "Turn 2: why do you need the underside of the same leaf?" --session-id exp_frontier_leaf_001 --profile openai_frontier --selection-mode keyword --image-context session --json

python -m Frontier_model.frontier_chat "Turn 3: answer from memory only, without reattaching image pixels." --session-id exp_frontier_leaf_001 --profile openai_frontier --selection-mode keyword --image-context none --json
```

Image context combinations:

```powershell
python -m Frontier_model.frontier_chat "Current image only." --session-id exp_context_current --profile openai_frontier --image-ref $LeafImage1 --selection-mode keyword --image-context current --json
python -m Frontier_model.frontier_chat "Session images." --session-id exp_context_current --profile openai_frontier --selection-mode keyword --image-context session --json
python -m Frontier_model.frontier_chat "No image pixels." --session-id exp_context_current --profile openai_frontier --selection-mode keyword --image-context none --json
```

Multiple image refs:

```powershell
python -m Frontier_model.frontier_chat "Compare these two uploaded grape leaf images and separate evidence by image." --session-id exp_multi_image_001 --profile openai_frontier --image-ref $LeafImage1 --image-ref $LeafImage2 --selection-mode keyword --image-context current --max-attached-images 8 --json
python -m Frontier_model.frontier_chat "Repeat using only one attached image limit." --session-id exp_multi_image_001 --profile openai_frontier --selection-mode keyword --image-context session --max-attached-images 1 --json
```

## 5. Selection Mode Combinations

Meaning:

```text
keyword = Python keyword retrieval; no page-selection LLM call
model   = one extra page-selection LLM call, then main LLM call
full    = sends all context pages; no page-selection LLM call
none    = no wiki/system context pages
```

Text task across selection modes:

```powershell
$Modes = @("keyword", "model", "full", "none")
foreach ($m in $Modes) {
  python -m Frontier_model.frontier_chat "Explain the Data Agent boundary between model_label and human_reviewed_label." --profile openai_frontier --selection-mode $m --json | Tee-Object "experiment_logs\frontier_openai_data_$m.json"
}
```

Visual task across selection modes:

```powershell
$Modes = @("keyword", "model", "full", "none")
foreach ($m in $Modes) {
  python -m Frontier_model.frontier_chat "Inspect this grape leaf image and follow the wiki evidence sufficiency procedure." --profile openai_frontier --image-ref $LeafImage1 --selection-mode $m --image-context current --json | Tee-Object "experiment_logs\frontier_openai_visual_$m.json"
}
```

## 6. Provider Switching Combinations

Text-capable profiles:

```powershell
$TextProfiles = @("echo", "openai_frontier", "openai_balanced", "anthropic_frontier", "kimi", "qwen_local")
foreach ($p in $TextProfiles) {
  python -m Frontier_model.frontier_chat "Explain the system boundary between chat, diagnosis, and data collection." --profile $p --selection-mode keyword --json | Tee-Object "experiment_logs\frontier_text_$p.json"
}
```

Image-capable profiles in the example config:

```powershell
$VisionProfiles = @("openai_frontier", "openai_balanced", "anthropic_frontier", "qwen_local")
foreach ($p in $VisionProfiles) {
  python -m Frontier_model.frontier_chat "Inspect this grape leaf image. Return user-facing language plus structured memory." --profile $p --image-ref $LeafImage1 --selection-mode keyword --image-context current --json | Tee-Object "experiment_logs\frontier_vision_$p.json"
}
```

Full provider x selection matrix for text:

```powershell
$TextProfiles = @("echo", "openai_frontier", "openai_balanced", "anthropic_frontier", "kimi", "qwen_local")
$Modes = @("keyword", "model", "full", "none")
foreach ($p in $TextProfiles) {
  foreach ($m in $Modes) {
    python -m Frontier_model.frontier_chat "Explain how reviewed and unreviewed data should be separated." --profile $p --selection-mode $m --json | Tee-Object "experiment_logs\matrix_text_${p}_${m}.json"
  }
}
```

Full provider x selection matrix for vision:

```powershell
$VisionProfiles = @("openai_frontier", "openai_balanced", "anthropic_frontier", "qwen_local")
$Modes = @("keyword", "model", "full", "none")
foreach ($p in $VisionProfiles) {
  foreach ($m in $Modes) {
    python -m Frontier_model.frontier_chat "Inspect this grape leaf image and identify whether evidence is sufficient." --profile $p --image-ref $LeafImage1 --selection-mode $m --image-context current --json | Tee-Object "experiment_logs\matrix_vision_${p}_${m}.json"
  }
}
```

## 7. Frontier Benchmark Runs

Smoke benchmark:

```powershell
python -m Frontier_model.benchmark --cases experiment_logs\external_eval_cases.jsonl --profile echo --selection-mode keyword --json
```

Compare selected profiles:

```powershell
python -m Frontier_model.benchmark --cases experiment_logs\external_eval_cases.jsonl --profile openai_frontier --profile anthropic_frontier --profile qwen_local --selection-mode keyword --json
```

Benchmark across selection modes:

```powershell
$Modes = @("keyword", "model", "full", "none")
foreach ($m in $Modes) {
  python -m Frontier_model.benchmark --cases experiment_logs\external_eval_cases.jsonl --profile openai_frontier --profile anthropic_frontier --selection-mode $m --json | Tee-Object "experiment_logs\benchmark_${m}.json"
}
```

Benchmark outputs are also written under:

```powershell
Get-ChildItem Frontier_model\runs
```

## 8. Data Agent End-To-End Capture

First create a visual Frontier session:

```powershell
python -m Frontier_model.frontier_chat "Inspect this grape leaf image for data collection. Provide a provisional model label only, record missing evidence, and do not treat it as ground truth." --session-id exp_data_leaf_001 --profile openai_frontier --image-ref $LeafImage1 --selection-mode keyword --image-context current --json | Tee-Object experiment_logs\exp_data_leaf_001_frontier.json
```

Capture latest visual turn:

```powershell
python tools\data_agent.py capture-turn --session-path Frontier_model\sessions\exp_data_leaf_001.json
python tools\data_agent.py capture-turn --session-path Frontier_model\sessions\exp_data_leaf_001.json --copy-images
```

Equivalent capture by session id:

```powershell
python tools\data_agent.py capture-turn --session-id exp_data_leaf_001 --session-dir Frontier_model\sessions
```

Capture a specific user or assistant turn id:

```powershell
python tools\data_agent.py capture-turn --session-path Frontier_model\sessions\exp_data_leaf_001.json --turn-id 1
python tools\data_agent.py capture-turn --session-path Frontier_model\sessions\exp_data_leaf_001.json --turn-id 2
```

Inspect and validate:

```powershell
python tools\data_agent.py list-pending
python tools\data_agent.py show-instance <instance_id>
python tools\data_agent.py validate-instance <instance_id>
```

Data Agent capture makes zero LLM calls. It reads an existing session turn and writes `machine_generated / unreviewed` records.

## 9. Human Review Workflow

Create the submitted review file:

```powershell
$Instance = "<instance_id>"
Copy-Item data_agent\instances\$Instance\human_review.template.json data_agent\instances\$Instance\human_review.submitted.json
notepad data_agent\instances\$Instance\human_review.submitted.json
```

Inside `human_review.submitted.json`, set:

```json
{
  "review_status": "reviewed",
  "reviewer": "your_name",
  "reviewed_at": "2026-07-24T00:00:00Z",
  "decision": "accept_model_label"
}
```

Valid `decision` values:

```text
accept_model_label
correct_label
reject_not_leaf
reject_unusable_image
needs_more_evidence
```

Import review and rebuild indexes:

```powershell
python tools\data_agent.py import-review --instance-id $Instance
python tools\data_agent.py rebuild-indexes
python tools\data_agent.py build-reviewed-index
python tools\data_agent.py validate-instance $Instance
python tools\data_agent.py list-pending
```

Only `accept_model_label` and `correct_label` enter `data_agent\indexes\reviewed_dataset_index.jsonl` as ground truth.

## 10. Root Chat Flow

Root `chat.py` is the local/cloud wiki chat path. It is useful for comparing against the Frontier pipeline.

```powershell
python chat.py "What image evidence is required for grape leaf diagnosis?" --provider echo --selection-mode keyword --json
python chat.py "What image evidence is required for grape leaf diagnosis?" --provider openai --model gpt-4o-mini --selection-mode keyword --json
python chat.py "Please inspect this grape leaf image and tell me what evidence is missing." --provider qwen-vl --model Qwen/Qwen2.5-VL-7B-Instruct --image-ref $LeafImage1 --selection-mode keyword --image-context current --json
```

Continue a root chat session:

```powershell
python chat.py --list-sessions
python chat.py "Why do you need the underside image?" --session-id <session_id> --provider openai --model gpt-4o-mini --selection-mode keyword --image-context session --json
```

## 11. Single-Turn Wiki Ask Flow

No session memory, no image pixels:

```powershell
python ask.py "How should GopherEye ask for front and back grape leaf images?" --provider echo --selection-mode keyword --json
python ask.py "How should GopherEye ask for front and back grape leaf images?" --provider openai --model gpt-4o-mini --selection-mode model --json
python ask.py "How should GopherEye ask for front and back grape leaf images?" --provider transformers --model Qwen/Qwen2.5-7B-Instruct --selection-mode keyword --json
```

Selection options here are only:

```text
model
full
keyword
```

## 12. Cloud Model Legacy Comparison

OpenAI-only legacy cloud path:

```powershell
python Cloud_model\cloud_chat.py "Please explain why unreviewed model labels must not enter wiki." --model gpt-4o-mini --selection-mode keyword --json
python Cloud_model\cloud_chat.py "Inspect this grape leaf image and request missing evidence." --model gpt-4o-mini --image-ref $LeafImage1 --selection-mode keyword --image-context current --json
```

Compare one local/root session with one cloud session:

```powershell
python Cloud_model\compare_sessions.py --local-session sessions\<local_session>.json --cloud-session Cloud_model\sessions\<cloud_session>.json --json
```

## 13. Raw Source And Wiki-Draft Flow

This flow does not directly edit curated wiki pages.

```powershell
python add_source.py raw\sources\disease_information\README.md --source-type disease_information --title "Disease information note"
python suggest_updates.py raw\sources\disease_information\README.md --provider openai --model gpt-4o-mini
```

Draft outputs go to `draft_updates\` unless `--output-dir` is provided.

## 14. Recommended Experiment Record Fields

For each run, record:

```text
experiment_id
date
command
profile
provider
model
task_type
selection_mode
image_context
image_refs
session_id
session_path
selected_pages
attached_image_manifest
missing_image_refs
parsed_json
envelope_valid
envelope_role_profile
envelope_fallback_used
assistant_message_quality_notes
diagnosis_quality_notes
evidence_sufficiency_notes
data_agent_instance_id
human_review_decision
reviewed_dataset_index_included
```

## 15. Minimal End-To-End Runs

No API, route/schema smoke:

```powershell
python -m Frontier_model.benchmark --cases experiment_logs\external_eval_cases.jsonl --profile echo --selection-mode keyword --json
```

One real visual diagnosis, then Data Agent capture:

```powershell
python -m Frontier_model.frontier_chat "Inspect this grape leaf image for data collection. Record missing evidence and avoid over-confirming disease." --session-id exp_e2e_visual_001 --profile openai_frontier --image-ref $LeafImage1 --selection-mode keyword --image-context current --json
python tools\data_agent.py capture-turn --session-path Frontier_model\sessions\exp_e2e_visual_001.json --copy-images
python tools\data_agent.py list-pending
```

One real provider comparison:

```powershell
python -m Frontier_model.benchmark --cases experiment_logs\external_eval_cases.jsonl --profile openai_frontier --profile anthropic_frontier --selection-mode keyword --json
```
