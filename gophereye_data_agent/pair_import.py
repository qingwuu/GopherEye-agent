from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import now_utc, safe_component, stable_id, write_json, write_jsonl

from .paths import REPO_ROOT, root_relative
from .targets import iter_instance_dirs, read_json_if_exists


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def discover_pair_dirs(image_root: Path, pair_ids: list[str] | None = None) -> list[Path]:
    if not image_root.exists():
        raise FileNotFoundError(f"Image root does not exist: {image_root}")
    wanted = {str(pair_id) for pair_id in pair_ids or []}
    dirs = [path for path in image_root.iterdir() if path.is_dir() and path.name.isdigit()]
    if wanted:
        dirs = [path for path in dirs if path.name in wanted]
    return sorted(dirs, key=lambda path: int(path.name))


def image_files(pair_dir: Path) -> list[Path]:
    return sorted(path for path in pair_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def import_image_pairs(
    image_root: Path,
    *,
    workspace_root: Path,
    pair_ids: list[str] | None = None,
    copy_images: bool = False,
    overwrite: bool = True,
) -> dict[str, Any]:
    pair_dirs = discover_pair_dirs(image_root, pair_ids=pair_ids)
    imported: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for pair_dir in pair_dirs:
        files = image_files(pair_dir)
        if len(files) < 2:
            skipped.append({"pair_id": pair_dir.name, "reason": "fewer than 2 image files"})
            continue
        if len(files) > 2:
            files = files[:2]
        imported.append(
            import_one_pair(
                pair_dir.name,
                files,
                workspace_root=workspace_root,
                copy_images=copy_images,
                overwrite=overwrite,
            )
        )
    rebuild_pair_indexes(workspace_root)
    return {
        "workspace_root": root_relative(workspace_root) or str(workspace_root),
        "image_root": root_relative(image_root) or str(image_root),
        "copy_images": copy_images,
        "pairs_seen": len(pair_dirs),
        "pairs_imported": len(imported),
        "imported": imported,
        "skipped": skipped,
    }


def import_one_pair(
    pair_id: str,
    files: list[Path],
    *,
    workspace_root: Path,
    copy_images: bool,
    overwrite: bool,
) -> dict[str, Any]:
    instance_id = f"inst_pair_{safe_component(pair_id)}"
    instance_dir = workspace_root / "instances" / instance_id
    if instance_dir.exists() and not overwrite:
        return {
            "pair_id": pair_id,
            "instance_id": instance_id,
            "instance_dir": root_relative(instance_dir),
            "status": "exists",
        }
    instance_dir.mkdir(parents=True, exist_ok=True)
    created_at = now_utc()
    uploads = []
    for index, source_path in enumerate(files, start=1):
        image_id = f"img_pair_{safe_component(pair_id)}_{index}"
        stored_path = source_path
        copy_status = "referenced"
        if copy_images:
            dest = workspace_root / "uploads" / "images" / image_id / source_path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest)
            stored_path = dest
            copy_status = "copied"
        uploads.append(
            {
                "record_type": "upload_record",
                "schema_version": "gophereye.data_agent.upload_record.v1",
                "upload_record_id": stable_id("upload", instance_id, source_path.name),
                "instance_id": instance_id,
                "image_id": image_id,
                "pair_id": pair_id,
                "pair_side_index": index,
                "image_role": f"leaf_pair_side_{index}",
                "side_hint": "front_or_back_unknown",
                "source_ref": root_relative(source_path) or str(source_path),
                "image_uri": source_path.resolve(strict=False).as_uri(),
                "stored_path": root_relative(stored_path) or str(stored_path),
                "copy_status": copy_status,
                "created_at": created_at,
                "review_status": "unreviewed",
                "is_ground_truth": False,
            }
        )

    upload_record = {
        "record_type": "upload_record_collection",
        "schema_version": "gophereye.data_agent.upload_record_collection.v1",
        "instance_id": instance_id,
        "created_at": created_at,
        "uploads": uploads,
    }
    model_label = {
        "record_type": "model_label",
        "schema_version": "gophereye.data_agent.model_label.v1",
        "model_label_id": stable_id("ml", instance_id),
        "instance_id": instance_id,
        "created_at": created_at,
        "label_source": "raw_image_pair_import",
        "generation_status": "unlabeled",
        "review_status": "unreviewed",
        "is_ground_truth": False,
        "evidence_status": "not_evaluated",
        "source": {
            "kind": "image_pair_folder",
            "pair_id": pair_id,
            "pair_dir": root_relative(files[0].parent) or str(files[0].parent),
        },
        "model_diagnosis": {
            "label": "unknown",
            "confidence": "unknown",
            "raw_current_diagnosis": "Imported leaf front/back image pair; no disease label generated yet.",
        },
        "image_ids": [row["image_id"] for row in uploads],
        "evidence_present": [],
        "evidence_missing": [],
        "recommended_next_image": "human_review_or_model_labeling",
    }
    review_template = {
        "record_type": "human_review_template",
        "schema_version": "gophereye.data_agent.human_review_template.v1",
        "review_id": stable_id("review", instance_id),
        "instance_id": instance_id,
        "created_at": created_at,
        "review_status": "unreviewed",
        "is_ground_truth": False,
        "pair_id": pair_id,
        "image_pair": [
            {
                "image_id": row["image_id"],
                "pair_side_index": row["pair_side_index"],
                "image_role": row["image_role"],
                "path": row["stored_path"],
            }
            for row in uploads
        ],
        "corrections": {},
        "human_notes": "",
    }
    manifest = {
        "record_type": "gophereye_data_agent_instance_manifest",
        "schema_version": "gophereye.data_agent.instance_manifest.v1",
        "instance_id": instance_id,
        "created_at": created_at,
        "updated_at": created_at,
        "review_status": "unreviewed",
        "is_ground_truth": False,
        "source": {
            "kind": "image_pair_folder",
            "pair_id": pair_id,
            "pair_dir": root_relative(files[0].parent) or str(files[0].parent),
        },
        "instance_dir": root_relative(instance_dir),
        "image_ids": [row["image_id"] for row in uploads],
        "model_label_id": model_label["model_label_id"],
        "review_id": review_template["review_id"],
        "files": {
            "manifest": "manifest.json",
            "upload_record": "upload_record.json",
            "model_label": "model_label.json",
            "human_review_template": "human_review.template.json",
            "audit_events": "audit_events.jsonl",
        },
        "linked_files": {"uploads": uploads},
        "boundary": {
            "llm_calls_created_by_gophereye_data_agent": 0,
            "label_source": "raw_unreviewed_import",
            "wiki_write_allowed": False,
            "human_review_required_for_ground_truth": True,
        },
    }

    write_json(instance_dir / "upload_record.json", upload_record)
    write_json(instance_dir / "model_label.json", model_label)
    write_json(instance_dir / "human_review.template.json", review_template)
    write_json(instance_dir / "manifest.json", manifest)
    write_jsonl(
        instance_dir / "audit_events.jsonl",
        [
            {
                "created_at": created_at,
                "event_id": stable_id("event", "import_image_pair", instance_id),
                "event_type": "import_image_pair",
                "instance_id": instance_id,
                "pair_id": pair_id,
                "source_files": [root_relative(path) or str(path) for path in files],
            }
        ],
    )
    return {
        "pair_id": pair_id,
        "instance_id": instance_id,
        "instance_dir": root_relative(instance_dir),
        "image_ids": [row["image_id"] for row in uploads],
        "image_paths": [row["stored_path"] for row in uploads],
        "status": "imported",
    }


def rebuild_pair_indexes(workspace_root: Path) -> dict[str, int]:
    uploads = []
    labels = []
    pending = []
    completed = []
    reviews = []
    for instance_dir in iter_instance_dirs(workspace_root):
        manifest = read_json_if_exists(instance_dir / "manifest.json")
        model_label = read_json_if_exists(instance_dir / "model_label.json")
        upload_record = read_json_if_exists(instance_dir / "upload_record.json")
        review = read_json_if_exists(instance_dir / "human_review.submitted.json")
        if not manifest or not model_label or not upload_record:
            continue
        uploads.extend(row for row in upload_record.get("uploads", []) if isinstance(row, dict))
        labels.append(model_label)
        if review:
            reviews.append(review)
            completed.append(
                {
                    "record_type": "review_queue_item",
                    "schema_version": "gophereye.data_agent.review_queue_item.v1",
                    "queue_status": "completed",
                    "instance_id": manifest.get("instance_id"),
                    "model_label_id": manifest.get("model_label_id"),
                    "instance_dir": root_relative(instance_dir),
                }
            )
        else:
            pending.append(
                {
                    "record_type": "review_queue_item",
                    "schema_version": "gophereye.data_agent.review_queue_item.v1",
                    "queue_status": "pending",
                    "instance_id": manifest.get("instance_id"),
                    "model_label_id": manifest.get("model_label_id"),
                    "created_at": now_utc(),
                    "instance_dir": root_relative(instance_dir),
                    "human_review_template": root_relative(instance_dir / "human_review.template.json"),
                    "evidence_status": model_label.get("evidence_status"),
                    "image_ids": model_label.get("image_ids") or [],
                    "model_diagnosis": model_label.get("model_diagnosis"),
                }
            )

    write_jsonl(workspace_root / "indexes" / "uploads.jsonl", uploads)
    write_jsonl(workspace_root / "indexes" / "model_labels.jsonl", labels)
    write_jsonl(workspace_root / "indexes" / "human_reviews.jsonl", reviews)
    write_jsonl(workspace_root / "indexes" / "reviewed_dataset_index.jsonl", [])
    write_jsonl(workspace_root / "review_queue" / "pending.jsonl", pending)
    write_jsonl(workspace_root / "review_queue" / "completed.jsonl", completed)
    return {
        "uploads": len(uploads),
        "model_labels": len(labels),
        "human_reviews": len(reviews),
        "pending_reviews": len(pending),
        "completed_reviews": len(completed),
    }
