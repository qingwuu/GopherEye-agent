from __future__ import annotations

import json
import os
import re
from typing import Any

from src.gophereye_runtime.utils import now_utc, parse_json_object, stable_id

from .schemas import DataOperation, JsonPatchAction, OperationPlan, OperationType, TargetSelector


PLANNER_SYSTEM_PROMPT = """You are GopherEye Data Agent's operation planner.

Return only a JSON object that matches the provided operation plan schema.
The executor, not the model, performs file writes and model inference.

Safety rules:
- Machine labels are proposals only; never mark ground_truth true.
- Use dry-run by default.
- For metadata edits, update the dataset manifest unless the user names a specific artifact file.
- Do not invent image paths or instance IDs.
"""


def default_plan(prompt: str, *, planner: str = "rule") -> OperationPlan:
    return OperationPlan(
        plan_id=stable_id("plan", prompt, now_utc()),
        user_prompt=prompt,
        created_at=now_utc(),
        planner=planner,  # type: ignore[arg-type]
        target_selector=TargetSelector(),
        operations=[],
        notes=[],
    )


def rule_based_plan(prompt: str) -> OperationPlan:
    plan = default_plan(prompt, planner="rule")
    text = prompt.lower()
    operation_text = text.replace("label studio", "ls_platform").replace("labelstudio", "ls_platform")

    selector = TargetSelector(source="dataset", max_items=50)
    max_match = re.search(r"(?:first|limit|max)\s+(\d+)", text)
    if max_match:
        selector.max_items = int(max_match.group(1))
    if "reviewed" in text:
        selector.source = "reviewed_dataset"
    if "completed" in text:
        selector.source = "completed_reviews"
    if "all" in text:
        selector.source = "dataset"

    plan.target_selector = selector

    patch_actions = parse_simple_set_actions(prompt)
    if patch_actions or "modify" in text or "set " in text or "change " in text:
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.MODIFY_MANIFEST,
                description="Modify the dataset manifest through validated patch actions.",
                patch_actions=patch_actions,
                params={"requires_explicit_actions": not bool(patch_actions)},
            )
        )

    if any(token in operation_text for token in ["segment", "segmentation", "mask", "yolo"]):
        params = {"backend": "yolo", "target": "generic_leaf_or_symptom"}
        params["model"] = "official" if any(token in operation_text for token in ["official", "default"]) else "local"
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.SEGMENTATION,
                description="Generate segmentation artifacts.",
                params=params,
            )
        )

    if any(token in operation_text for token in ["label", "labeling", "diagnose", "diagnosis", "diagnostic", "disease", "powdery", "downy"]):
        if "heuristic" in operation_text or "local rule" in operation_text:
            provider = "heuristic"
        elif "claude" in operation_text or "anthropic" in operation_text:
            provider = "anthropic"
        else:
            provider = "openai"
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.GRAPE_DISEASE_LABELING,
                description="Create grape disease label proposals.",
                params={
                    "allowed_labels": ["powdery_mildew", "downy_mildew", "healthy", "unknown", "not_leaf"],
                    "provider": provider,
                    "write_artifacts": False,
                    "write_back": False,
                },
            )
        )

    if any(token in text for token in ["embed", "embedding", "similar", "duplicate", "cluster"]):
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.EMBEDDING,
                description="Compute image embeddings for similarity, grouping, or duplicate discovery.",
                params={"backend": "color_histogram", "persist_vector_index": False},
            )
        )

    if any(token in text for token in ["augment", "augmentation", "synthetic"]):
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.AUGMENTATION,
                description="Create derived augmented images.",
                params={"backend": "auto", "count_per_image": 3, "preserve_masks": True},
            )
        )

    wants_push = any(token in text for token in ["push", "upload", "send to", "open in", "view in", "export", "推送", "上传", "查看", "打开"])
    if "label studio" in text or "labelstudio" in text:
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.EXPORT_LABEL_STUDIO,
                description="Export or upload selected targets as Label Studio tasks.",
                params={"output_name": "label_studio_tasks.json", "embed_images": True, "upload": wants_push},
            )
        )

    if "fiftyone" in text:
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.OPEN_FIFTYONE,
                description="Create a persistent FiftyOne dataset view.",
                params={"dataset_name": "gophereye_data_agent", "overwrite": True},
            )
        )

    if "roboflow" in text or "robotflow" in text:
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.PUSH_ROBOFLOW,
                description="Push selected images to a configured Roboflow project.",
                params={},
            )
        )

    if "hugging face" in text or "hf hub" in text:
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.SYNC_HF_HUB,
                description="Upload selected artifacts to Hugging Face Hub.",
                params={},
            )
        )

    if "mlflow" in text:
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.LOG_MLFLOW,
                description="Log this job and artifacts to MLflow.",
                params={},
            )
        )

    if "dvc" in text:
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.VERSION_DVC,
                description="Prepare or run DVC data versioning commands.",
                params={},
            )
        )

    if "lakefs" in text:
        plan.operations.append(
            DataOperation(
                operation_type=OperationType.VERSION_LAKEFS,
                description="Prepare or run lakeFS versioning commands.",
                params={},
            )
        )

    if not plan.operations:
        plan.notes.append("No operation keyword was detected. Add modify, segment, label, embed, augment, or export.")
    return plan


def parse_simple_set_actions(prompt: str) -> list[JsonPatchAction]:
    actions: list[JsonPatchAction] = []
    pattern = r"\bset\s+([A-Za-z0-9_.-]+)\s*=\s*(\"[^\"]+\"|'[^']+'|.+?)(?=\s+(?:for|and|then)\b|[,.;\n]|$)"
    for match in re.finditer(pattern, prompt, flags=re.IGNORECASE):
        field = match.group(1).strip().replace(".", "_")
        value = match.group(2).strip().strip("\"'")
        actions.append(
            JsonPatchAction(
                op="set",
                file="manifest",
                json_pointer=f"/corrections/{escape_json_pointer(field)}",
                value=value,
                reason="Parsed from natural-language set expression.",
            )
        )
    return actions


def escape_json_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def plan_with_openai(prompt: str, *, model: str = "gpt-5-mini") -> OperationPlan:
    from openai import OpenAI

    schema = OperationPlan.model_json_schema()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or None)
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "User request:\n" + prompt + "\n\nReturn a strict operation plan JSON.",
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "gophereye_data_agent_operation_plan",
                "schema": schema,
                "strict": True,
            }
        },
    )
    raw = getattr(response, "output_text", "") or ""
    parsed = parse_json_object(raw) or json.loads(raw)
    return OperationPlan.model_validate(parsed)


def plan_with_anthropic(prompt: str, *, model: str = "claude-sonnet-4-5") -> OperationPlan:
    try:
        from anthropic import Anthropic
    except Exception as exc:
        raise RuntimeError("anthropic is not installed. Install anthropic to use the Anthropic planner.") from exc

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY") or None)
    schema = OperationPlan.model_json_schema()
    message = client.messages.create(
        model=model,
        max_tokens=2400,
        tools=[
            {
                "name": "submit_operation_plan",
                "description": "Submit the validated Data Agent operation plan.",
                "input_schema": schema,
            }
        ],
        tool_choice={"type": "tool", "name": "submit_operation_plan"},
        messages=[
            {
                "role": "user",
                "content": PLANNER_SYSTEM_PROMPT + "\n\nUser request:\n" + prompt,
            }
        ],
    )
    for block in message.content:
        if getattr(block, "type", None) == "tool_use":
            return OperationPlan.model_validate(getattr(block, "input"))
    raise RuntimeError("Anthropic planner did not return a tool call.")


def make_plan(prompt: str, *, planner: str = "rule", model: str | None = None) -> OperationPlan:
    if planner == "rule":
        return rule_based_plan(prompt)
    if planner == "openai":
        return plan_with_openai(prompt, model=model or "gpt-5-mini")
    if planner == "anthropic":
        return plan_with_anthropic(prompt, model=model or "claude-sonnet-4-5")
    raise ValueError(f"Unsupported planner: {planner}")
