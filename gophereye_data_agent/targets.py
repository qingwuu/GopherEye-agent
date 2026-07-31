from __future__ import annotations

from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import local_path_from_ref, read_json

from .manifest_store import attach_manifest_path, manifest_row_to_target, read_manifest
from .paths import DEFAULT_WORKSPACE_ROOT, REPO_ROOT, normalize_path, root_relative
from .schemas import InstanceTarget, TargetSelector


INSTANCE_FILES = {
    "manifest": "dataset_manifest.jsonl",
    "upload_record": "dataset_manifest.jsonl",
    "model_label": "dataset_manifest.jsonl",
    "human_review_template": "dataset_manifest.jsonl",
    "human_review_submitted": "dataset_manifest.jsonl",
}


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = read_json(path)
    return value if isinstance(value, dict) else {}


def resolve_workspace_ref(ref: str, workspace_root: Path) -> Path | None:
    repo_candidate = local_path_from_ref(REPO_ROOT, ref)
    workspace_candidate = local_path_from_ref(workspace_root, ref)
    for candidate in [repo_candidate, workspace_candidate]:
        if candidate is not None and candidate.exists():
            return candidate
    return repo_candidate or workspace_candidate


def target_from_explicit_path(path_text: str) -> InstanceTarget:
    path = normalize_path(path_text)
    if path.is_dir():
        row = {
            "instance_id": path.name,
            "sample_id": path.name,
            "pair_id": path.name,
            "source_dir": root_relative(path),
            "sample_type": "directory",
            "image_count": 0,
            "image_paths": [],
            "side_1_path": "",
            "side_2_path": "",
            "label": "unknown",
            "label_confidence": "unknown",
            "review_status": "unreviewed",
        }
        return manifest_row_to_target(row)
    value = read_json_if_exists(path)
    if "side_1_path" in value or "side_2_path" in value:
        return manifest_row_to_target(value)
    instance_id = str(value.get("instance_id") or path.stem)
    return InstanceTarget(
        instance_id=instance_id,
        instance_dir=root_relative(path.parent),
        source={"kind": "explicit_path", "path": root_relative(path)},
        manifest=value if path.name == "manifest.json" else {},
        model_label=value if path.name == "model_label.json" else {},
    )


def passes_filters(target: InstanceTarget, selector: TargetSelector) -> bool:
    if selector.instance_ids and target.instance_id not in selector.instance_ids:
        return False
    image_ids = {str(row.get("image_id")) for row in target.image_links if row.get("image_id")}
    if selector.image_ids and not image_ids.intersection(selector.image_ids):
        return False
    review_status = str(target.manifest.get("review_status") or target.model_label.get("review_status") or "")
    if selector.review_status and review_status not in selector.review_status:
        return False
    label = str(target.manifest.get("label") or (target.model_label.get("model_diagnosis") or {}).get("label") or "")
    if selector.model_labels and label not in selector.model_labels:
        return False
    if not selector.include_without_images and not target.image_links:
        return False
    return True


def resolve_targets(selector: TargetSelector, workspace_root: Path = DEFAULT_WORKSPACE_ROOT) -> list[InstanceTarget]:
    if selector.source == "explicit_paths":
        targets = [target_from_explicit_path(path) for path in selector.paths]
    else:
        rows = attach_manifest_path(read_manifest(workspace_root), workspace_root)
        if selector.source == "completed_reviews":
            rows = [row for row in rows if str(row.get("review_status")) == "reviewed"]
        elif selector.source == "reviewed_dataset":
            rows = [row for row in rows if bool(row.get("is_ground_truth"))]
        elif selector.source == "pending_reviews":
            rows = [row for row in rows if str(row.get("review_status") or "unreviewed") != "reviewed"]
        targets = [manifest_row_to_target(row) for row in rows]

    filtered = [target for target in targets if passes_filters(target, selector)]
    if selector.max_items:
        filtered = filtered[: selector.max_items]
    return filtered


def local_image_paths(target: InstanceTarget, workspace_root: Path = DEFAULT_WORKSPACE_ROOT) -> list[Path]:
    paths: list[Path] = []
    for row in target.image_links:
        for key in ["stored_path", "source_ref", "image_uri"]:
            ref = row.get(key)
            if not ref or not isinstance(ref, str):
                continue
            if ref.startswith(("http://", "https://", "data:")):
                continue
            path = resolve_workspace_ref(ref, workspace_root)
            if path is None:
                continue
            if path.exists() and path.is_file():
                paths.append(path)
                break
    return paths
