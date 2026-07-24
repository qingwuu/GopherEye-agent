# GopherEye VLM-Wiki 数据集设计

这个目录用于说明 GopherEye 的 VLM + Wiki 诊断工作流数据结构。

核心原则是分层：

```text
model_facing/
  可以转换成模型 prompt、训练 label、评估输入的样本。

system_records/
  图片资产、ID、路径、人工标签、隐藏答案、评估 oracle、审计日志。
```

模型应该学习诊断行为和结构化输出。程序应该负责路径、ID、时间戳、表之间的 join、schema 校验、保存和审计。

## 示例目录

```text
examples/
  README.md

  model_facing/
    visual_intake_sft.example.jsonl
    diagnosis_sft.example.jsonl
    chat_memory_sft.example.jsonl
    behavior_eval_inputs.example.jsonl

  system_records/
    image_manifest.example.jsonl
    image_relationships.example.jsonl
    reviewed_visual_labels.example.jsonl
    diagnosis_case_bank.example.jsonl
    eval_oracles.example.jsonl
    model_outputs_audit.example.jsonl
```

所有 `.jsonl` 文件都是真正的 JSONL：一行一个 JSON 对象。

## 需要喂给模型或可导出给模型的文件

### `model_facing/visual_intake_sft.example.jsonl`

用途：

```text
训练/评估 VLM 对图片的第一轮结构化观察。
```

目标任务：

```text
image pixels + compact task context -> visual_intake JSON
```

模型学习：

```text
是否是叶片图片
图片质量
叶片正反面
可见结构
可见症状
候选病害
简短观察总结
```

### `model_facing/diagnosis_sft.example.jsonl`

用途：

```text
训练/评估基于 wiki 的证据充分性判断和诊断决策。
```

目标任务：

```text
visual_intakes + short_term_memory + selected wiki refs + user question
-> diagnosis_output JSON
```

这是最关键的 app-facing 训练文件。

### `model_facing/chat_memory_sft.example.jsonl`

用途：

```text
训练/评估多轮追问回答和 short_term_memory 更新。
```

目标任务：

```text
recent transcript + current short_term_memory + current message/images
-> assistant_message + memory_update
```

模型只应该用 `image_order` 表示当前图像顺序，不应该生成 `image_id`、路径、session ID、时间戳或文件名。

### `model_facing/behavior_eval_inputs.example.jsonl`

用途：

```text
只包含评估时可以喂给模型的输入。
```

隐藏答案和 pass/fail 规则放在：

```text
system_records/eval_oracles.example.jsonl
```

## 不应该直接喂给模型的系统记录

### `system_records/image_manifest.example.jsonl`

记录稳定图片资产。用于 loader 和 join，不应直接作为 prompt 内容。

### `system_records/image_relationships.example.jsonl`

记录同一叶片、正反面配对、observation 等关系。

### `system_records/reviewed_visual_labels.example.jsonl`

记录人工审核后的视觉标签。导出脚本可以把它转换成 `model_facing/visual_intake_sft.example.jsonl`。

### `system_records/diagnosis_case_bank.example.jsonl`

记录诊断 case 和隐藏 expected output。导出脚本可以把它转换成 `model_facing/diagnosis_sft.example.jsonl`。

### `system_records/eval_oracles.example.jsonl`

记录评估 oracle：

```text
must_include
must_not_include
expected_fields
pass_criteria
```

这些内容评估时不能喂给模型。

### `system_records/model_outputs_audit.example.jsonl`

记录 teacher model、旧模型、未来微调模型的原始输出。它用于审计和挖掘训练样本，不是 ground truth。

## 推荐构建顺序

```text
1. system_records/image_manifest
2. system_records/image_relationships
3. system_records/reviewed_visual_labels
4. model_facing/visual_intake_sft
5. system_records/diagnosis_case_bank
6. model_facing/diagnosis_sft
7. model_facing/behavior_eval_inputs + system_records/eval_oracles
8. model_facing/chat_memory_sft
9. system_records/model_outputs_audit
```

先做小而准确的人工审核数据集，再逐步扩大规模。
