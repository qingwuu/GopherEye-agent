# GopherEye Data Agent

Independent CLI-first data automation for grape leaf image samples.

A sample can be:

- one standalone image, such as `images/1b.png`
- one folder with two related images, such as a front/back leaf pair
- one folder with more than two related images

The runtime is intentionally simple:

```text
images/
-> dataset_manifest.csv
-> dataset_manifest.jsonl
-> runs/<run_id>/artifacts/
```

It does not use the old chat/session archive pipeline.

## Main Commands

Import only:

```bash
python -m gophereye_data_agent import-samples images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test
```

OpenAI labeler:

```bash
export OPENAI_API_KEY="sk-..."

python -m gophereye_data_agent auto images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --label-provider openai
```

Claude labeler:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

python -m gophereye_data_agent auto images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --label-provider anthropic
```

The `auto` command:

```text
1. imports selected image samples
2. writes dataset_manifest.csv/jsonl
3. sends each sample's image(s) to OpenAI or Claude for grape disease label proposal
4. runs embedding
5. runs augmentation
6. exports Label Studio tasks
7. writes one run_summary.json
```

## Important Files

```text
gophereye_data_workspace/
  dataset_manifest.csv       human-readable dataset table
  dataset_manifest.jsonl     structured manifest for code
  runs/
    dagent_<id>/
      run_summary.json
      artifacts/
        labels/
        embeddings/
        augmented/
        label_studio_tasks.json
```

There are no `instances/`, `review_queue/`, or `indexes/` directories in the simple pipeline.

## Useful Commands

```bash
python -m gophereye_data_agent doctor
python -m gophereye_data_agent import-samples images --sample-ids 1,2,1b
python -m gophereye_data_agent auto images --sample-ids 1,2,1b --label-provider openai
python -m gophereye_data_agent label --provider openai
python -m gophereye_data_agent label --provider anthropic
python -m gophereye_data_agent embed
python -m gophereye_data_agent augment --count-per-image 1
python -m gophereye_data_agent export-label-studio
python -m gophereye_data_agent segment --backend yolo --model mode/yolo_grape.pt --max-items 1
python -m gophereye_data_agent modify /batch_id test_batch --apply
```

YOLO segmentation is local-only by default. Put your trained segmentation weights at:

```text
mode/yolo_grape.pt
```

or pass another local path with `--model`.

Ground-truth labels still require human review. Model labels are proposals only.
