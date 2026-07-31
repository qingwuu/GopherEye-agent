from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import now_utc, read_jsonl, safe_component, stable_id, write_jsonl

from .paths import root_relative
from .schemas import InstanceTarget


MANIFEST_JSONL = "dataset_manifest.jsonl"
MANIFEST_CSV = "dataset_manifest.csv"

BASE_COLUMNS = [
    "record_type",
    "schema_version",
    "instance_id",
    "sample_id",
    "pair_id",
    "sample_type",
    "image_count",
    "source_dir",
    "image_paths",
    "side_1_path",
    "side_2_path",
    "side_1_image_id",
    "side_2_image_id",
    "label",
    "label_confidence",
    "label_source",
    "review_status",
    "is_ground_truth",
    "latest_label_artifact",
    "latest_segmentation_artifact",
    "latest_embedding_artifact",
    "latest_augmentation_artifact",
    "notes",
    "created_at",
    "updated_at",
]


def manifest_jsonl_path(workspace_root: Path) -> Path:
    return workspace_root / MANIFEST_JSONL


def manifest_csv_path(workspace_root: Path) -> Path:
    return workspace_root / MANIFEST_CSV


def read_manifest(workspace_root: Path) -> list[dict[str, Any]]:
    return read_jsonl(manifest_jsonl_path(workspace_root))


def write_manifest(workspace_root: Path, rows: list[dict[str, Any]]) -> dict[str, str | int]:
    workspace_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(manifest_jsonl_path(workspace_root), rows)
    write_manifest_csv(manifest_csv_path(workspace_root), rows)
    return {
        "rows": len(rows),
        "manifest_jsonl": root_relative(manifest_jsonl_path(workspace_root)) or str(manifest_jsonl_path(workspace_root)),
        "manifest_csv": root_relative(manifest_csv_path(workspace_root)) or str(manifest_csv_path(workspace_root)),
    }


def write_manifest_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(BASE_COLUMNS)
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in columns})


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def upsert_manifest_rows(workspace_root: Path, new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = read_manifest(workspace_root)
    by_id = {str(row.get("instance_id")): row for row in existing if row.get("instance_id")}
    for row in new_rows:
        instance_id = str(row["instance_id"])
        old = by_id.get(instance_id, {})
        created_at = old.get("created_at") or row.get("created_at") or now_utc()
        by_id[instance_id] = {**old, **row, "created_at": created_at, "updated_at": now_utc()}
    rows = sorted(by_id.values(), key=lambda item: natural_sample_sort_key(str(item.get("sample_id") or item.get("pair_id") or item.get("instance_id") or "")))
    write_manifest(workspace_root, rows)
    return rows


def natural_sample_sort_key(value: str) -> tuple[int, str]:
    return (int(value), value) if value.isdigit() else (10**9, value)


def make_sample_manifest_row(sample_id: str, files: list[Path]) -> dict[str, Any]:
    clean_sample_id = safe_component(sample_id)
    instance_id = f"sample_{clean_sample_id}"
    created_at = now_utc()
    image_paths = [root_relative(path) or str(path) for path in files]
    side_1_path = image_paths[0] if len(image_paths) >= 1 else ""
    side_2_path = image_paths[1] if len(image_paths) >= 2 else ""
    sample_type = "single" if len(image_paths) == 1 else "pair" if len(image_paths) == 2 else "multi_image"
    return {
        "record_type": "gophereye_data_agent_dataset_row",
        "schema_version": "gophereye.data_agent.dataset_manifest.v1",
        "instance_id": instance_id,
        "sample_id": sample_id,
        # Kept only so older generated manifests and commands remain readable.
        "pair_id": sample_id,
        "sample_type": sample_type,
        "image_count": len(image_paths),
        "source_dir": root_relative(files[0].parent) or str(files[0].parent),
        "image_paths": image_paths,
        "side_1_path": side_1_path,
        "side_2_path": side_2_path,
        "side_1_image_id": f"img_sample_{clean_sample_id}_1" if len(image_paths) >= 1 else "",
        "side_2_image_id": f"img_sample_{clean_sample_id}_2" if len(image_paths) >= 2 else "",
        "label": "unknown",
        "label_confidence": "unknown",
        "label_source": "unlabeled",
        "review_status": "unreviewed",
        "is_ground_truth": False,
        "latest_label_artifact": "",
        "latest_segmentation_artifact": "",
        "latest_embedding_artifact": "",
        "latest_augmentation_artifact": "",
        "notes": "",
        "created_at": created_at,
        "updated_at": created_at,
        "source_fingerprint": stable_id("sample", sample_id, image_paths),
    }


def manifest_row_to_target(row: dict[str, Any]) -> InstanceTarget:
    image_links = []
    sample_id = row.get("sample_id") or row.get("pair_id")
    raw_paths = row.get("image_paths")
    image_paths = raw_paths if isinstance(raw_paths, list) else []
    if not image_paths:
        image_paths = [row.get("side_1_path"), row.get("side_2_path")]
    for image_index, path in enumerate([item for item in image_paths if item], start=1):
        if not path:
            continue
        image_links.append(
            {
                "image_id": row.get(f"side_{image_index}_image_id") or f"{row.get('instance_id')}_{image_index}",
                "sample_id": sample_id,
                "sample_image_index": image_index,
                "pair_id": row.get("pair_id"),
                "pair_side_index": image_index if len(image_paths) > 1 else None,
                "image_role": f"leaf_sample_image_{image_index}" if len(image_paths) > 1 else "leaf_single_image",
                "stored_path": path,
                "source_ref": path,
            }
        )
    label = str(row.get("label") or "unknown")
    confidence = str(row.get("label_confidence") or "unknown")
    return InstanceTarget(
        instance_id=str(row.get("instance_id") or sample_id),
        instance_dir=None,
        source={"kind": "manifest_row", "manifest": root_relative(manifest_jsonl_path_from_row(row))},
        manifest=row,
        model_label={
            "instance_id": row.get("instance_id"),
            "model_diagnosis": {"label": label, "confidence": confidence},
            "evidence_present": [],
            "evidence_status": "not_evaluated",
            "review_status": row.get("review_status") or "unreviewed",
        },
        upload_record={"uploads": image_links},
        review={},
        image_links=image_links,
    )


def manifest_jsonl_path_from_row(row: dict[str, Any]) -> Path:
    manifest_path = row.get("_manifest_path")
    return Path(str(manifest_path)) if manifest_path else Path(MANIFEST_JSONL)


def attach_manifest_path(rows: list[dict[str, Any]], workspace_root: Path) -> list[dict[str, Any]]:
    path = manifest_jsonl_path(workspace_root)
    return [{**row, "_manifest_path": str(path)} for row in rows]
