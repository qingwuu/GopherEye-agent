# GopherEye Data Agent 使用手册

这套 Data Agent 是独立 CLI pipeline，不走现在的 chat/frontier model，也不走旧 Session Archive。

当前数据单位叫 `sample`：

- `images/1/` 这种 folder 是一个 sample，里面可以有 1 张、2 张或更多相关图片
- `images/1b.png` 这种直接放在 `images/` 根目录的图片，也是一个独立 single-image sample
- 如果一个 sample 恰好有两张图，可以把它理解成 leaf front/back pair，但系统不会强制要求一定是 pair

## 1. 每次从头启动

Git Bash:

```bash
cd ~/OneDrive/文档/GitHub/GopherEye-agent
source .venv/Scripts/activate
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
```

检查依赖：

```bash
python -m gophereye_data_agent doctor
```

这一步只检查环境，不生成数据文件。

## 2. 最重要的数据文件

Data Agent 现在只维护一个大的 manifest：

```text
gophereye_data_workspace/<workspace>/
  dataset_manifest.csv
  dataset_manifest.jsonl
  runs/
    dagent_<run_id>/
      run_summary.json
      artifacts/
```

主要看 `dataset_manifest.csv`。它是人可以打开看的总表。

不会再生成这些旧复杂目录：

```text
instances/
review_queue/
indexes/
```

## 3. Manifest 每一行是什么

`dataset_manifest.csv` 每一行是一个 sample，不是一张图。

关键字段：

```text
instance_id                 代码内部使用的 sample id，例如 sample_1
sample_id                   原始 sample id，例如 1、2、1b
sample_type                 single / pair / multi_image
image_count                 这个 sample 里面有几张图
image_paths                 完整图片路径列表
side_1_path                 第一张图，方便 pair 场景查看
side_2_path                 第二张图，方便 pair 场景查看
label                       当前标签 proposal
label_confidence            标签置信度
label_source                标签来源，例如 openai / anthropic / heuristic
review_status               unreviewed / reviewed
is_ground_truth             是否人工确认过
latest_label_artifact       最新 label JSON artifact
latest_segmentation_artifact
latest_embedding_artifact
latest_augmentation_artifact
notes
created_at
updated_at
```

`pair_id` 这个字段暂时还在，是为了兼容旧生成文件。新的流程请看 `sample_id`。

## 4. 只导入图片

测试 `images/1/`、`images/2/` 两个 folder，再加一个单张图 `images/1b.png`：

```bash
python -m gophereye_data_agent import-samples images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test
```

这一步会生成或更新：

```text
gophereye_data_workspace/simple_test/dataset_manifest.csv
gophereye_data_workspace/simple_test/dataset_manifest.jsonl
```

输出里重点看：

```text
samples_seen
samples_imported
imported[].sample_id
imported[].sample_type
imported[].image_count
manifest_csv
manifest_jsonl
```

## 5. OpenAI 参与的一键流程

```bash
export OPENAI_API_KEY="sk-..."

python -m gophereye_data_agent auto images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --label-provider openai
```

它会自动做：

```text
1. 导入 sample
2. 更新 dataset_manifest.csv/jsonl
3. 把每个 sample 的图片发给 OpenAI
4. 生成 grape disease label proposal
5. 写回 manifest 里的 label / confidence / source
6. 生成 embedding
7. 生成 augmentation
8. 导出 Label Studio task JSON
9. 写 run_summary.json
```

生成文件位置：

```text
gophereye_data_workspace/simple_test/
  dataset_manifest.csv
  dataset_manifest.jsonl
  runs/
    dagent_<run_id>/
      run_summary.json
      artifacts/
        labels/
        embeddings/
        augmented/
        label_studio_tasks.json
```

## 6. Claude 参与的一键流程

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

python -m gophereye_data_agent auto images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --label-provider anthropic
```

输出结构和 OpenAI 一样，只是 label proposal 来源会是 Anthropic/Claude。

## 7. 只跑 labeling

先确保已经跑过 `import-samples`。

OpenAI:

```bash
export OPENAI_API_KEY="sk-..."

python -m gophereye_data_agent label \
  --provider openai \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3
```

Claude:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

python -m gophereye_data_agent label \
  --provider anthropic \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3
```

没有 API key 时，可以用本地 heuristic 跑通流程：

```bash
python -m gophereye_data_agent label \
  --provider heuristic \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3
```

labeling 生成：

```text
runs/dagent_<run_id>/artifacts/labels/*.grape_label_proposal.json
```

并会更新：

```text
dataset_manifest.csv
dataset_manifest.jsonl
```

注意：这些 label 是 proposal，不是 ground truth。

## 8. YOLO segmentation

你之后训练好的 YOLO segmentation model 放这里：

```text
mode/yolo_grape.pt
```

然后跑：

```bash
python -m gophereye_data_agent segment \
  --backend yolo \
  --model mode/yolo_grape.pt \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 1
```

如果 `mode/yolo_grape.pt` 不存在，命令会直接返回 `not_available`，不会下载默认 YOLO 模型。

segmentation 生成：

```text
runs/dagent_<run_id>/artifacts/segmentation/
  segmentation_manifest.json
  masks/
  overlays/
```

## 9. SAM2 segmentation

如果 SAM2 环境可用，可以跑：

```bash
python -m gophereye_data_agent segment \
  --backend sam2 \
  --pretrained facebook/sam2-hiera-large \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 1
```

或者用本地 checkpoint：

```bash
python -m gophereye_data_agent segment \
  --backend sam2 \
  --model-cfg configs/sam2.1/sam2.1_hiera_l.yaml \
  --checkpoint /path/to/sam2.1_hiera_large.pt \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 1
```

SAM2 输出：

```text
runs/dagent_<run_id>/artifacts/segmentation_sam2/
  segmentation_manifest.json
  masks/
```

## 10. Embedding

```bash
python -m gophereye_data_agent embed \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --persist-vector-index
```

生成：

```text
runs/dagent_<run_id>/artifacts/embeddings/embeddings.json
runs/dagent_<run_id>/artifacts/lancedb/
```

当前 MVP 的 embedding 是本地 color histogram。它主要用于：

- 找相似叶片图
- 找重复或近重复图片
- 后续做自动分组
- 后续 active learning 选样

如果你现在觉得 embedding 暂时不需要，一键流程可以关掉：

```bash
python -m gophereye_data_agent auto images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --label-provider openai \
  --no-embed
```

## 11. Augmentation

```bash
python -m gophereye_data_agent augment \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --count-per-image 1
```

生成：

```text
runs/dagent_<run_id>/artifacts/augmented/
  augmentation_manifest.json
  *_aug_0.jpg
```

如果 Albumentations 可用，会用 Albumentations；否则用 PIL fallback。

## 12. Label Studio export

```bash
python -m gophereye_data_agent export-label-studio \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3
```

生成：

```text
runs/dagent_<run_id>/artifacts/label_studio_tasks.json
```

当前是导出 task JSON，不是自动启动 Label Studio UI。

## 13. 修改 manifest 字段

dry-run，不真正写：

```bash
python -m gophereye_data_agent modify /batch_id simple_test \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3
```

真正写：

```bash
python -m gophereye_data_agent modify /batch_id simple_test \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --apply
```

Git Bash 如果把 `/batch_id` 当路径转换，就用：

```bash
MSYS_NO_PATHCONV=1 python -m gophereye_data_agent modify /batch_id simple_test \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --apply
```

这会更新：

```text
dataset_manifest.csv
dataset_manifest.jsonl
```

并生成一次 run summary。

## 14. 查看结果

查看总表：

```bash
head -5 gophereye_data_workspace/simple_test/dataset_manifest.csv
```

查看最新 run：

```bash
ls -lt gophereye_data_workspace/simple_test/runs | head
```

查看 artifacts：

```bash
find gophereye_data_workspace/simple_test/runs -path '*artifacts*' -type f | head -80
```

查看某次 run summary：

```bash
cat gophereye_data_workspace/simple_test/runs/<dagent_run_id>/run_summary.json
```

## 15. 推荐测试命令组合

本地无 API key，只测试系统能跑通：

```bash
python -m gophereye_data_agent import-samples images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test

python -m gophereye_data_agent auto images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --label-provider heuristic \
  --no-embed \
  --no-augment \
  --no-export-label-studio
```

OpenAI 真正参与：

```bash
export OPENAI_API_KEY="sk-..."

python -m gophereye_data_agent auto images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --label-provider openai
```

Claude 真正参与：

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

python -m gophereye_data_agent auto images \
  --sample-ids 1,2,1b \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 3 \
  --label-provider anthropic
```

YOLO 本地模型测试：

```bash
python -m gophereye_data_agent segment \
  --backend yolo \
  --model mode/yolo_grape.pt \
  --workspace-root gophereye_data_workspace/simple_test \
  --job-root gophereye_data_workspace/simple_test/runs \
  --max-items 1
```
