# GopherEye Data Agent 启动与测试手册

## 1. 每次从零启动

在 Git Bash 中进入 repo：

```bash
cd ~/OneDrive/文档/GitHub/GopherEye-agent
```

启用虚拟环境：

```bash
source .venv/Scripts/activate
```

建议设置 UTF-8，避免中文路径和表格显示乱码：

```bash
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
```

确认依赖：

```bash
python -m gophereye_data_agent doctor
```

如果全部是 `yes`，说明外部工具已经被当前 `.venv` 识别。

## 2. 可选服务启动

### MLflow

如果要把 Data Agent job 记录到 MLflow，先开一个单独 terminal：

```bash
source .venv/Scripts/activate

mlflow server \
  --host 127.0.0.1 \
  --port 5000 \
  --workers 1 \
  --backend-store-uri sqlite:///gophereye_data_workspace/agent_artifacts/mlflow.db \
  --default-artifact-root gophereye_data_workspace/agent_artifacts/mlartifacts
```

然后在 Data Agent terminal 里设置：

```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
```

浏览器打开：

```text
http://127.0.0.1:5000
```

### lakeFS

lakeFS 当前在 Data Agent 中是可检测/占位 adapter。真实 commit/upload 还需要后续补 repository、branch、path 的写入逻辑。

如果你启动了 lakeFS quickstart，设置：

```bash
export LAKECTL_SERVER_ENDPOINT_URL=http://127.0.0.1:8000
export LAKECTL_CREDENTIALS_ACCESS_KEY_ID="你的 access key"
export LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY="你的 secret key"
```

## 3. 从原始 pair 图片导入测试 workspace

为了只测试 `images/1` 和 `images/2`，建议用独立 workspace root，不污染默认 `gophereye_data_workspace/`：

```bash
python -m gophereye_data_agent import-pairs images \
  --pair-ids 1,2 \
  --workspace-root gophereye_data_workspace/pair_test
```

这一步做的事：

- 扫描 `images/1/` 和 `images/2/`
- 每个文件夹生成一个 instance
- 写入 `manifest.json`
- 写入 `upload_record.json`
- 写入 `model_label.json`
- 写入 `human_review.template.json`
- 生成 `review_queue/pending.jsonl`
- 生成 `indexes/*.jsonl`

输出应类似：

```text
pairs_imported: 2
inst_pair_1 -> images/1/*.jpeg
inst_pair_2 -> images/2/*.jpeg
```

后续测试统一使用：

```bash
WORKSPACE=gophereye_data_workspace/pair_test
JOBS=gophereye_data_workspace/pair_test/jobs
```

## 4. 查看和规划

查看 operation plan schema：

```bash
python -m gophereye_data_agent schema
```

用自然语言生成计划，不执行：

```bash
python -m gophereye_data_agent plan \
  "set batch_id=pair_test and label grape disease and embed similar images and augment"
```

保存计划到文件：

```bash
python -m gophereye_data_agent plan \
  "set batch_id=pair_test and label grape disease and embed similar images and augment" \
  --out gophereye_data_workspace/pair_test/operation_plan.json
```

执行已保存计划：

```bash
python -m gophereye_data_agent apply \
  gophereye_data_workspace/pair_test/operation_plan.json \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS"
```

注意：`modify_instance_json` 默认 dry-run。真正写 JSON 必须加 `--apply`，或者使用 `apply` 命令。

## 5. Modify Instance JSON

dry-run，只规划不写：

```bash
python -m gophereye_data_agent modify /corrections/batch_id pair_test \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS"
```

真正写入：

```bash
python -m gophereye_data_agent modify /corrections/batch_id pair_test \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --apply
```

这会修改：

```text
human_review.template.json
  corrections.batch_id = "pair_test"
```

并在 job 里保存 backup 和 audit log。

## 6. Grape Disease Labeling

启发式 labeling：

```bash
python -m gophereye_data_agent label \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 2
```

OpenAI planner 生成计划：

```bash
export OPENAI_API_KEY="你的 OpenAI key"

python -m gophereye_data_agent plan \
  "label pending grape disease" \
  --planner openai \
  --model gpt-5-mini
```

当前 `label` 是 proposal，不是 ground truth。人审之前不要把它当最终标签。

## 7. Segmentation

### YOLO segmentation

首次运行可能下载 `yolo11n-seg.pt`，建议先用一两个样本测试：

```bash
python -m gophereye_data_agent segment \
  --backend yolo \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 1
```

如果你已经有本地 YOLO segmentation 模型：

```bash
python -m gophereye_data_agent segment \
  --backend yolo \
  --model /path/to/yolo11n-seg.pt \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 1
```

输出会在 job artifact 里生成 mask、overlay 和 `segmentation_manifest.json`。

### SAM2 segmentation

使用 Hugging Face pretrained，首次运行可能下载较大模型：

```bash
python -m gophereye_data_agent segment \
  --backend sam2 \
  --pretrained facebook/sam2-hiera-large \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 1
```

使用本地 checkpoint：

```bash
python -m gophereye_data_agent segment \
  --backend sam2 \
  --model-cfg configs/sam2.1/sam2.1_hiera_l.yaml \
  --checkpoint /path/to/sam2.1_hiera_large.pt \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 1
```

## 8. Embedding

默认使用本地 color histogram embedding：

```bash
python -m gophereye_data_agent embed \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 2
```

同时写入 LanceDB vector index：

```bash
python -m gophereye_data_agent embed \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 2 \
  --persist-vector-index
```

Embedding 的用途：

- 查找相似叶片图片
- 查找重复图片
- 自动分组
- 做 active learning 选样
- 后续接 FiftyOne / LanceDB 相似检索

## 9. Augmentation

```bash
python -m gophereye_data_agent augment \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 2 \
  --count-per-image 3
```

如果 Albumentations 可用，会使用 Albumentations；否则 fallback 到 PIL 简单增强。

## 10. Label Studio Export

导出 Label Studio task JSON：

```bash
python -m gophereye_data_agent export-label-studio \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 2
```

输出文件在：

```text
gophereye_data_workspace/pair_test/jobs/<job_id>/artifacts/label_studio_tasks.json
```

当前实现是导出 task JSON。自动创建 Label Studio project、上传 task、同步 annotation 需要下一步继续补 adapter。

## 11. MLflow

确认 MLflow server 已启动，并设置：

```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
```

执行并记录 artifacts：

```bash
python -m gophereye_data_agent run \
  "label pending grape disease and mlflow" \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS"
```

这一步会：

- 生成 grape disease label proposals
- 把整个 job folder 记录到 MLflow experiment `gophereye_data_agent`

## 12. DVC

dry-run：

```bash
python -m gophereye_data_agent run \
  "dvc" \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS"
```

真正执行 `dvc add`：

```bash
python -m gophereye_data_agent run \
  "dvc" \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --apply
```

注意：`--apply` 会调用 DVC 写 `.dvc` 文件。

## 13. lakeFS

当前命令：

```bash
python -m gophereye_data_agent run \
  "lakefs" \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS"
```

当前状态：

- 如果 `lakefs` Python client 可 import，会返回 `skipped`
- 它会提示需要 `repo`、`branch`、`path`
- 真正写入 lakeFS repository 的逻辑还需要下一步补充

## 14. FiftyOne

创建 FiftyOne dataset，不启动 UI：

```bash
python -m gophereye_data_agent run \
  "open fiftyone all limit 2" \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS"
```

如果要打开 FiftyOne UI，需要根据 job result 里的 `dataset_name` 启动：

```bash
python - <<'PY'
import fiftyone as fo
dataset_name = "把 job_result.json 里的 dataset_name 填到这里"
ds = fo.load_dataset(dataset_name)
session = fo.launch_app(ds)
session.wait()
PY
```

## 15. Hugging Face Hub

当前自然语言命令会因为缺少 `repo_id` 而跳过：

```bash
python -m gophereye_data_agent run \
  "hugging face" \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS"
```

真正上传需要下一步给 CLI 增加 `--repo-id`，或者手动创建 operation plan 并填入：

```json
{
  "operation_type": "sync_hf_hub",
  "params": {
    "repo_id": "your-name/your-dataset",
    "repo_type": "dataset"
  }
}
```

## 16. MCP Server

启动 MCP server：

```bash
python -m gophereye_data_agent mcp-server
```

这是长运行进程。当前暴露：

- `create_operation_plan`
- `gophereye-data-agent://schema/operation-plan`

停止用 `Ctrl+C`。

## 17. OpenAI Agents SDK

当前 adapter 可创建一个 Agent manager：

```bash
python - <<'PY'
from gophereye_data_agent.agents_runtime import build_agents_sdk_manager
agent = build_agents_sdk_manager()
print(agent.name)
PY
```

目前主 CLI 仍以 `plan/run/apply` 为主；Agents SDK 的多工具 orchestrator 是下一步可以继续扩展的部分。

## 18. 查看结果

查看最近 job：

```bash
ls -lt "$JOBS" | head
```

查看某个 job：

```bash
JOB="$JOBS/<job_id>"
cat "$JOB/job_result.json"
cat "$JOB/operation_plan.json"
cat "$JOB/resolved_targets.json"
```

查看 artifacts：

```bash
find "$JOBS" -path '*artifacts*' -type f | head -50
```

## 19. 用 images/1 和 images/2 一次性测试命令

从零测试：

```bash
cd ~/OneDrive/文档/GitHub/GopherEye-agent
source .venv/Scripts/activate
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

WORKSPACE=gophereye_data_workspace/pair_test
JOBS=gophereye_data_workspace/pair_test/jobs

python -m gophereye_data_agent doctor

python -m gophereye_data_agent import-pairs images \
  --pair-ids 1,2 \
  --workspace-root "$WORKSPACE"

python -m gophereye_data_agent modify /corrections/batch_id pair_test \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --apply

python -m gophereye_data_agent label \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 2

python -m gophereye_data_agent embed \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 2 \
  --persist-vector-index

python -m gophereye_data_agent augment \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 2 \
  --count-per-image 1

python -m gophereye_data_agent export-label-studio \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 2
```

可选重模型测试：

```bash
python -m gophereye_data_agent segment \
  --backend yolo \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 1

python -m gophereye_data_agent segment \
  --backend sam2 \
  --pretrained facebook/sam2-hiera-large \
  --source pending_reviews \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS" \
  --max-items 1
```

可选 MLflow 测试：

```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000

python -m gophereye_data_agent run \
  "label pending grape disease and mlflow" \
  --workspace-root "$WORKSPACE" \
  --job-root "$JOBS"
```

## 20. 本次 images/1,2 已验证结果

我已经用 `images/1` 和 `images/2` 跑过这些功能：

```text
import-pairs: imported 2 pairs
modify: 2 patch actions applied
label: Created 2 label proposals
embed: Created 4 embeddings
augment: Created 4 augmented images
export-label-studio: Exported 4 Label Studio tasks
MLflow: Logged job to experiment gophereye_data_agent
DVC dry-run: would run dvc add ...
lakeFS: adapter available, requires repo/branch/path before real commit
```

YOLO 和 SAM2 本地没有检测到已下载的模型/checkpoint，所以没有在本文档生成时强行跑重模型下载。建议你先用 `--max-items 1` 测试。
