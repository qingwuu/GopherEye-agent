from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import safe_component

from .planner import make_plan
from .sample_import import import_image_samples
from .paths import normalize_path
from .schemas import DataOperation, OperationPlan, OperationType, TargetSelector


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "tif", "tiff", "bmp"}


@dataclass
class PromptImport:
    image_root: Path
    sample_ids: list[str]


def extract_image_paths(prompt: str) -> list[Path]:
    pattern = r"(?P<path>(?:[A-Za-z]:)?[^\s\"'，,;]+?\.(?:jpg|jpeg|png|webp|tif|tiff|bmp))"
    paths: list[Path] = []
    seen: set[str] = set()
    for match in re.finditer(pattern, prompt, flags=re.IGNORECASE):
        raw = match.group("path").strip().strip("`")
        path = normalize_path(raw)
        key = str(path.resolve(strict=False)).lower()
        if key not in seen:
            paths.append(path)
            seen.add(key)
    return paths


def sample_id_from_prompt(prompt: str) -> str | None:
    patterns = [
        r"\bsample(?:\s+id)?\s*[:=]?\s*([A-Za-z0-9_.-]+)",
        r"导入为\s*([A-Za-z0-9_.-]+)",
        r"作为\s*([A-Za-z0-9_.-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            value = safe_component(match.group(1))
            if value and value.lower() not in {"sample", "a", "an"}:
                return value
    return None


def imports_from_prompt(prompt: str) -> list[PromptImport]:
    explicit_paths = extract_image_paths(prompt)
    forced_sample_id = sample_id_from_prompt(prompt)
    imports: list[PromptImport] = []
    for path in explicit_paths:
        if path.suffix.lower().lstrip(".") in IMAGE_EXTENSIONS:
            sample_id = forced_sample_id or path.stem
            imports.append(PromptImport(image_root=path.parent, sample_ids=[sample_id]))
    return imports


def platforms_from_prompt(prompt: str, requested: str = "auto") -> list[str]:
    value = requested.strip().lower().replace("_", "-")
    if value and value not in {"auto", "none"}:
        return [value]
    if value == "none":
        return []

    text = prompt.lower()
    platforms: list[str] = []
    if "label studio" in text or "labelstudio" in text:
        platforms.append("label-studio")
    if "fiftyone" in text:
        platforms.append("fiftyone")
    if "roboflow" in text or "robotflow" in text:
        platforms.append("roboflow")
    if not platforms and any(token in text for token in ["push", "upload", "view", "open", "推送", "上传", "查看", "打开"]):
        platforms.append("fiftyone")
    return platforms


def ensure_platform_operations(plan: OperationPlan, platforms: list[str]) -> None:
    for platform in platforms:
        normalized = platform.lower().replace("_", "-")
        if normalized in {"label-studio", "labelstudio"}:
            existing = next((op for op in plan.operations if op.operation_type == OperationType.EXPORT_LABEL_STUDIO), None)
            params = {"output_name": "label_studio_tasks.json", "embed_images": True, "upload": True}
            if existing:
                existing.params = {**existing.params, **params}
            else:
                plan.operations.append(
                    DataOperation(
                        operation_type=OperationType.EXPORT_LABEL_STUDIO,
                        description="Export and optionally upload selected targets as Label Studio tasks.",
                        params=params,
                    )
                )
        elif normalized == "fiftyone":
            if not any(op.operation_type == OperationType.OPEN_FIFTYONE for op in plan.operations):
                plan.operations.append(
                    DataOperation(
                        operation_type=OperationType.OPEN_FIFTYONE,
                        description="Create a persistent FiftyOne dataset view.",
                        params={"dataset_name": "gophereye_data_agent", "overwrite": True},
                    )
                )
        elif normalized in {"roboflow", "robotflow"}:
            if not any(op.operation_type == OperationType.PUSH_ROBOFLOW for op in plan.operations):
                plan.operations.append(
                    DataOperation(
                        operation_type=OperationType.PUSH_ROBOFLOW,
                        description="Push selected images to a configured Roboflow project.",
                    )
                )


def build_language_prompt_plan(
    prompt: str,
    *,
    planner: str,
    model: str | None,
    workspace_root: Path,
    push_to: str,
) -> tuple[OperationPlan, list[dict[str, Any]]]:
    import_results: list[dict[str, Any]] = []
    imported_instance_ids: list[str] = []
    for import_spec in imports_from_prompt(prompt):
        result = import_image_samples(
            import_spec.image_root,
            workspace_root=workspace_root,
            sample_ids=import_spec.sample_ids,
        )
        import_results.append(result)
        imported_instance_ids.extend(str(row.get("instance_id")) for row in result.get("imported", []) if row.get("instance_id"))

    plan = make_plan(prompt, planner=planner, model=model)
    if imported_instance_ids:
        plan.target_selector = TargetSelector(
            source="dataset",
            instance_ids=imported_instance_ids,
            max_items=len(imported_instance_ids),
        )
    ensure_platform_operations(plan, platforms_from_prompt(prompt, requested=push_to))
    return plan, import_results
