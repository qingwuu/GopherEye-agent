from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance

from src.gophereye_runtime.utils import stable_id, write_json

from .paths import DEFAULT_WORKSPACE_ROOT, DEFAULT_YOLO_SEG_MODEL, normalize_path, root_relative
from .schemas import InstanceTarget, OperationResult
from .storage import artifact_ref
from .targets import local_image_paths


OFFICIAL_YOLO_SEG_MODEL = "yolo11n-seg.pt"
LOCAL_YOLO_ALIASES = {"", "local", "grape", "grape-local", "yolo_grape"}
OFFICIAL_YOLO_ALIASES = {"official", "default", "ultralytics", "official-default", "yolo-default"}


def run_segmentation(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
) -> OperationResult:
    backend = params.get("backend") or "auto"
    if backend not in {"auto", "yolo"}:
        return OperationResult(
            operation_type="segmentation",
            status="not_available",
            message=f"Segmentation backend {backend!r} is not enabled. This MVP currently supports YOLO only.",
            targets_seen=len(targets),
        )
    return run_yolo_segmentation(targets, job_dir=job_dir, params=params, workspace_root=workspace_root)


def resolve_yolo_model(model_value: object | None) -> tuple[str, str, bool]:
    raw = str(model_value or os.getenv("GOPHEREYE_YOLO_MODEL") or "local").strip()
    raw_lower = raw.lower()
    if raw_lower in LOCAL_YOLO_ALIASES:
        model_path = normalize_path(DEFAULT_YOLO_SEG_MODEL)
        return str(model_path), root_relative(model_path) or str(model_path), True
    if raw_lower in OFFICIAL_YOLO_ALIASES:
        return OFFICIAL_YOLO_SEG_MODEL, OFFICIAL_YOLO_SEG_MODEL, False

    model_path = normalize_path(raw)
    if model_path.exists():
        return str(model_path), root_relative(model_path) or str(model_path), True

    looks_like_path = model_path.is_absolute() or any(separator in raw for separator in ["/", "\\"])
    if looks_like_path:
        return str(model_path), root_relative(model_path) or str(model_path), True

    return raw, raw, False


def run_yolo_segmentation(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
) -> OperationResult:
    image_jobs = [
        (target, image_path)
        for target in targets
        for image_path in local_image_paths(target, workspace_root=workspace_root)
    ]
    if not image_jobs:
        return OperationResult(
            operation_type="segmentation",
            status="skipped",
            message="No local images were resolved for segmentation.",
            targets_seen=len(targets),
        )

    model_arg, model_ref, require_local_file = resolve_yolo_model(params.get("model"))
    if require_local_file and not Path(model_arg).exists():
        return OperationResult(
            operation_type="segmentation",
            status="not_available",
            message=(
                "Local YOLO segmentation model not found. "
                f"Expected {model_ref}. "
                "Train your YOLO seg model and place it there, pass --model <path>, or use --model official."
            ),
            targets_seen=len(targets),
            details={"expected_model": model_ref, "official_default": OFFICIAL_YOLO_SEG_MODEL},
        )

    try:
        from ultralytics import YOLO
    except Exception as exc:
        return OperationResult(
            operation_type="segmentation",
            status="not_available",
            message=f"ultralytics is not installed: {exc}",
            targets_seen=len(targets),
        )
    out_dir = job_dir / "artifacts" / "segmentation"
    mask_dir = out_dir / "masks"
    overlay_dir = out_dir / "overlays"
    mask_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[str] = []
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    try:
        model = YOLO(model_arg)
    except Exception as exc:
        return OperationResult(
            operation_type="segmentation",
            status="not_available",
            message=f"Could not load YOLO model {model_ref!r}: {exc}",
            targets_seen=len(targets),
        )

    for target, image_path in image_jobs:
        try:
            results = model(str(image_path), verbose=False)
            for result_idx, result in enumerate(results):
                overlay_path = overlay_dir / f"{target.instance_id}_{image_path.stem}_{result_idx}.jpg"
                try:
                    overlay = result.plot()
                    Image.fromarray(overlay[..., ::-1]).save(overlay_path)
                    artifacts.append(artifact_ref(overlay_path))
                except Exception:
                    overlay_path = None
                masks = getattr(result, "masks", None)
                boxes = getattr(result, "boxes", None)
                names = getattr(result, "names", {}) or {}
                if masks is None:
                    records.append(
                        {
                            "instance_id": target.instance_id,
                            "image_path": str(image_path),
                            "backend": "yolo",
                            "model": model_ref,
                            "masks": [],
                            "overlay_path": artifact_ref(overlay_path) if overlay_path else None,
                        }
                    )
                    continue
                mask_data = masks.data.cpu().numpy() if hasattr(masks.data, "cpu") else np.asarray(masks.data)
                mask_records = []
                cls_values = []
                conf_values = []
                if boxes is not None:
                    cls_values = boxes.cls.cpu().numpy().tolist() if hasattr(boxes.cls, "cpu") else list(boxes.cls)
                    conf_values = boxes.conf.cpu().numpy().tolist() if hasattr(boxes.conf, "cpu") else list(boxes.conf)
                for mask_idx, mask in enumerate(mask_data):
                    mask_path = mask_dir / f"{target.instance_id}_{image_path.stem}_{result_idx}_{mask_idx}.png"
                    Image.fromarray((mask.astype(np.uint8) * 255)).save(mask_path)
                    artifacts.append(artifact_ref(mask_path))
                    class_id = int(cls_values[mask_idx]) if mask_idx < len(cls_values) else None
                    mask_records.append(
                        {
                            "mask_path": artifact_ref(mask_path),
                            "class_id": class_id,
                            "class_name": names.get(class_id) if class_id is not None else None,
                            "confidence": float(conf_values[mask_idx]) if mask_idx < len(conf_values) else None,
                        }
                    )
                records.append(
                    {
                        "instance_id": target.instance_id,
                        "image_path": str(image_path),
                        "backend": "yolo",
                        "model": model_ref,
                        "masks": mask_records,
                        "overlay_path": artifact_ref(overlay_path) if overlay_path else None,
                    }
                )
        except Exception as exc:
            errors.append({"instance_id": target.instance_id, "image_path": str(image_path), "error": str(exc)})

    manifest_path = out_dir / "segmentation_manifest.json"
    write_json(
        manifest_path,
        {
            "record_type": "segmentation_manifest",
            "schema_version": "gophereye.data_agent.segmentation_manifest.v1",
            "backend": "yolo",
            "model": model_ref,
            "records": records,
            "errors": errors,
        },
    )
    artifacts.append(artifact_ref(manifest_path))
    return OperationResult(
        operation_type="segmentation",
        status="ok" if not errors else "failed" if not records else "ok",
        message=f"Created segmentation records for {len(records)} images; {len(errors)} errors.",
        targets_seen=len(targets),
        artifacts=artifacts,
        details={"records": records, "errors": errors},
    )


def compute_color_histogram(path: Path, bins: int = 16) -> list[float]:
    image = Image.open(path).convert("RGB").resize((224, 224))
    arr = np.asarray(image, dtype=np.float32) / 255.0
    features: list[float] = []
    for channel in range(3):
        hist, _ = np.histogram(arr[:, :, channel], bins=bins, range=(0.0, 1.0), density=True)
        features.extend(hist.astype(float).tolist())
    norm = math.sqrt(sum(x * x for x in features)) or 1.0
    return [x / norm for x in features]


def run_embeddings(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
) -> OperationResult:
    backend = params.get("backend") or "color_histogram"
    if backend not in {"color_histogram", "lancedb"}:
        return OperationResult(
            operation_type="embedding",
            status="not_available",
            message=f"Embedding backend {backend!r} is not implemented in this local MVP.",
            targets_seen=len(targets),
        )

    out_dir = job_dir / "artifacts" / "embeddings"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for target in targets:
        for image_path in local_image_paths(target, workspace_root=workspace_root):
            try:
                vector = compute_color_histogram(image_path, bins=int(params.get("bins", 16)))
                rows.append(
                    {
                        "embedding_id": stable_id("emb", target.instance_id, str(image_path)),
                        "instance_id": target.instance_id,
                        "image_path": str(image_path),
                        "backend": "color_histogram",
                        "dimension": len(vector),
                        "vector": vector,
                    }
                )
            except Exception as exc:
                errors.append({"instance_id": target.instance_id, "image_path": str(image_path), "error": str(exc)})

    path = out_dir / "embeddings.json"
    write_json(path, {"record_type": "embedding_manifest", "rows": rows, "errors": errors})
    artifacts = [artifact_ref(path)]

    if params.get("persist_vector_index"):
        lance_result = maybe_write_lancedb(rows, job_dir=job_dir)
        artifacts.extend(lance_result.get("artifacts", []))

    return OperationResult(
        operation_type="embedding",
        status="ok" if not errors else "failed" if not rows else "ok",
        message=f"Created {len(rows)} embeddings; {len(errors)} errors.",
        targets_seen=len(targets),
        artifacts=artifacts,
        details={"rows": len(rows), "errors": errors},
    )


def maybe_write_lancedb(rows: list[dict[str, Any]], *, job_dir: Path) -> dict[str, Any]:
    try:
        import lancedb
        import pyarrow as pa
    except Exception as exc:
        return {"status": "not_available", "message": str(exc), "artifacts": []}
    db_path = job_dir / "artifacts" / "lancedb"
    db = lancedb.connect(str(db_path))
    table_rows = [
        {
            "embedding_id": row["embedding_id"],
            "instance_id": row["instance_id"],
            "image_path": row["image_path"],
            "vector": row["vector"],
        }
        for row in rows
    ]
    if table_rows:
        db.create_table("image_embeddings", table_rows, mode="overwrite")
    return {"status": "ok", "artifacts": [artifact_ref(db_path)]}


def run_augmentation(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
) -> OperationResult:
    out_dir = job_dir / "artifacts" / "augmented"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = int(params.get("count_per_image", 3))
    artifacts: list[str] = []
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    albumentations_available = False
    try:
        import albumentations as A

        albumentations_available = True
        try:
            rotate = A.Rotate(angle_range=(-20, 20), p=0.5)
        except TypeError:
            rotate = A.Rotate(limit=20, p=0.5)
        transform = A.Compose(
            [
                A.HorizontalFlip(p=0.5),
                A.RandomBrightnessContrast(p=0.5),
                rotate,
            ]
        )
    except Exception:
        transform = None

    for target in targets:
        for image_path in local_image_paths(target, workspace_root=workspace_root):
            try:
                image = Image.open(image_path).convert("RGB")
                for idx in range(count):
                    if albumentations_available and transform is not None:
                        arr = np.asarray(image)
                        aug = transform(image=arr)["image"]
                        out_img = Image.fromarray(aug)
                        method = "albumentations"
                    else:
                        out_img = fallback_augment(image, idx)
                        method = "pil_fallback"
                    out_path = out_dir / f"{target.instance_id}_{image_path.stem}_aug_{idx}.jpg"
                    out_img.save(out_path, quality=92)
                    artifacts.append(artifact_ref(out_path))
                    records.append(
                        {
                            "instance_id": target.instance_id,
                            "source_image": str(image_path),
                            "augmented_image": artifact_ref(out_path),
                            "method": method,
                        }
                    )
            except Exception as exc:
                errors.append({"instance_id": target.instance_id, "image_path": str(image_path), "error": str(exc)})

    manifest_path = out_dir / "augmentation_manifest.json"
    write_json(
        manifest_path,
        {
            "record_type": "augmentation_manifest",
            "schema_version": "gophereye.data_agent.augmentation_manifest.v1",
            "records": records,
            "errors": errors,
        },
    )
    artifacts.append(artifact_ref(manifest_path))
    return OperationResult(
        operation_type="augmentation",
        status="ok" if not errors else "failed" if not records else "ok",
        message=f"Created {len(records)} augmented images; {len(errors)} errors.",
        targets_seen=len(targets),
        artifacts=artifacts,
        details={"records": len(records), "errors": errors},
    )


def fallback_augment(image: Image.Image, idx: int) -> Image.Image:
    if idx % 3 == 0:
        return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if idx % 3 == 1:
        return image.rotate(8, expand=False)
    return ImageEnhance.Brightness(image).enhance(1.12)
