from __future__ import annotations

from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import local_path_from_ref, read_json, read_jsonl

from .paths import DEFAULT_WORKSPACE_ROOT, REPO_ROOT, normalize_path, root_relative
from .schemas import InstanceTarget, TargetSelector


INSTANCE_FILES = {
    "manifest": "manifest.json",
    "upload_record": "upload_record.json",
    "model_label": "model_label.json",
    "human_review_template": "human_review.template.json",
    "human_review_submitted": "human_review.submitted.json",
}


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = read_json(path)
    return value if isinstance(value, dict) else {}


def iter_instance_dirs(workspace_root: Path = DEFAULT_WORKSPACE_ROOT) -> list[Path]:
    root = workspace_root / "instances"
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def target_from_instance_dir(instance_dir: Path) -> InstanceTarget:
    manifest = read_json_if_exists(instance_dir / "manifest.json")
    model_label = read_json_if_exists(instance_dir / "model_label.json")
    upload_record = read_json_if_exists(instance_dir / "upload_record.json")
    review = read_json_if_exists(instance_dir / "human_review.submitted.json")
    instance_id = str(
        manifest.get("instance_id")
        or model_label.get("instance_id")
        or upload_record.get("instance_id")
        or instance_dir.name
    )
    image_links = []
    if isinstance(upload_record.get("uploads"), list):
        image_links.extend(row for row in upload_record["uploads"] if isinstance(row, dict))
    if isinstance(manifest.get("linked_files"), dict):
        image_links.extend(row for row in manifest["linked_files"].get("uploads", []) if isinstance(row, dict))
    return InstanceTarget(
        instance_id=instance_id,
        instance_dir=root_relative(instance_dir),
        source={"kind": "instance_dir"},
        manifest=manifest,
        model_label=model_label,
        upload_record=upload_record,
        review=review,
        image_links=dedupe_image_links(image_links),
    )


def dedupe_image_links(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("image_id") or row.get("source_ref") or len(out))
        old = out.get(key, {})
        out[key] = {**old, **row}
    return list(out.values())


def index_rows(workspace_root: Path, name: str) -> list[dict[str, Any]]:
    return read_jsonl(workspace_root / "indexes" / name)


def resolve_workspace_ref(ref: str, workspace_root: Path) -> Path | None:
    repo_candidate = local_path_from_ref(REPO_ROOT, ref)
    workspace_candidate = local_path_from_ref(workspace_root, ref)
    for candidate in [repo_candidate, workspace_candidate]:
        if candidate is not None and candidate.exists():
            return candidate
    return repo_candidate or workspace_candidate


def targets_from_index(selector: TargetSelector, workspace_root: Path) -> list[InstanceTarget]:
    if selector.source == "pending_reviews":
        queue_rows = read_jsonl(workspace_root / "review_queue" / "pending.jsonl")
    elif selector.source == "completed_reviews":
        queue_rows = read_jsonl(workspace_root / "review_queue" / "completed.jsonl")
    elif selector.source == "reviewed_dataset":
        queue_rows = index_rows(workspace_root, "reviewed_dataset_index.jsonl")
    else:
        queue_rows = []

    targets: list[InstanceTarget] = []
    labels_by_instance = {
        str(row.get("instance_id")): row
        for row in index_rows(workspace_root, "model_labels.jsonl")
        if row.get("instance_id")
    }
    uploads_by_instance: dict[str, list[dict[str, Any]]] = {}
    for row in index_rows(workspace_root, "uploads.jsonl"):
        if row.get("instance_id"):
            uploads_by_instance.setdefault(str(row["instance_id"]), []).append(row)

    for row in queue_rows:
        instance_id = str(row.get("instance_id") or "")
        if not instance_id:
            continue
        instance_dir_text = row.get("instance_dir")
        instance_dir = (
            resolve_workspace_ref(str(instance_dir_text), workspace_root)
            if instance_dir_text
            else workspace_root / "instances" / instance_id
        )
        if instance_dir is None:
            instance_dir = workspace_root / "instances" / instance_id
        if instance_dir.exists():
            target = target_from_instance_dir(instance_dir)
        else:
            target = InstanceTarget(
                instance_id=instance_id,
                instance_dir=root_relative(instance_dir),
                source={"kind": selector.source, "row": row},
                model_label=labels_by_instance.get(instance_id, {}),
                image_links=uploads_by_instance.get(instance_id, []),
            )
        targets.append(target)
    return targets


def target_from_explicit_path(path_text: str) -> InstanceTarget:
    path = normalize_path(path_text)
    if path.is_dir():
        return target_from_instance_dir(path)
    value = read_json_if_exists(path)
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
    evidence_status = str(target.model_label.get("evidence_status") or "")
    if selector.evidence_status and evidence_status not in selector.evidence_status:
        return False
    label = str((target.model_label.get("model_diagnosis") or {}).get("label") or "")
    if selector.model_labels and label not in selector.model_labels:
        return False
    if not selector.include_without_images and not target.image_links:
        return False
    return True


def resolve_targets(selector: TargetSelector, workspace_root: Path = DEFAULT_WORKSPACE_ROOT) -> list[InstanceTarget]:
    if selector.source == "workspace_instances":
        targets = [target_from_instance_dir(path) for path in iter_instance_dirs(workspace_root)]
    elif selector.source == "explicit_paths":
        targets = [target_from_explicit_path(path) for path in selector.paths]
    else:
        targets = targets_from_index(selector, workspace_root)

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
