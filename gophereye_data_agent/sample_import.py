from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import safe_component

from .manifest_store import make_sample_manifest_row, read_manifest, upsert_manifest_rows, write_manifest
from .paths import root_relative


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def discover_sample_dirs(image_root: Path, sample_ids: list[str] | None = None) -> list[Path]:
    if not image_root.exists():
        raise FileNotFoundError(f"Image root does not exist: {image_root}")
    wanted = {str(sample_id) for sample_id in sample_ids or []}
    dirs = [path for path in image_root.iterdir() if path.is_dir() and path.name.isdigit()]
    if wanted:
        dirs = [path for path in dirs if path.name in wanted]
    return sorted(dirs, key=lambda path: int(path.name))


def image_files(sample_dir: Path) -> list[Path]:
    return sorted(path for path in sample_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def root_image_files(image_root: Path, sample_ids: list[str] | None = None) -> list[Path]:
    wanted = {str(sample_id) for sample_id in sample_ids or []}
    files = sorted(path for path in image_root.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
    if wanted:
        files = [path for path in files if path.stem in wanted or path.name in wanted]
    return files


def import_image_samples(
    image_root: Path,
    *,
    workspace_root: Path,
    sample_ids: list[str] | None = None,
    copy_images: bool = False,
    overwrite: bool = True,
) -> dict[str, Any]:
    sample_dirs = discover_sample_dirs(image_root, sample_ids=sample_ids)
    root_files = root_image_files(image_root, sample_ids=sample_ids)
    imported_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for sample_dir in sample_dirs:
        files = image_files(sample_dir)
        if not files:
            skipped.append({"sample_id": sample_dir.name, "reason": "no image files"})
            continue
        imported_rows.append(import_one_sample(sample_dir.name, files, workspace_root=workspace_root, copy_images=copy_images))

    for image_path in root_files:
        imported_rows.append(import_one_sample(image_path.stem, [image_path], workspace_root=workspace_root, copy_images=copy_images))

    rows = upsert_manifest_rows(workspace_root, imported_rows) if overwrite else append_new_manifest_rows(workspace_root, imported_rows)
    return {
        "workspace_root": root_relative(workspace_root) or str(workspace_root),
        "image_root": root_relative(image_root) or str(image_root),
        "copy_images": copy_images,
        "samples_seen": len(sample_dirs) + len(root_files),
        "samples_imported": len(imported_rows),
        "manifest_csv": root_relative(workspace_root / "dataset_manifest.csv"),
        "manifest_jsonl": root_relative(workspace_root / "dataset_manifest.jsonl"),
        "total_manifest_rows": len(rows),
        "imported": [
            {
                "sample_id": row["sample_id"],
                "instance_id": row["instance_id"],
                "sample_type": row["sample_type"],
                "image_count": row["image_count"],
                "image_paths": row["image_paths"],
                "side_1_path": row["side_1_path"],
                "side_2_path": row["side_2_path"],
            }
            for row in imported_rows
        ],
        "skipped": skipped,
    }


def import_one_sample(sample_id: str, files: list[Path], *, workspace_root: Path, copy_images: bool) -> dict[str, Any]:
    resolved_files = list(files)
    if copy_images:
        copied_files = []
        clean_sample_id = safe_component(sample_id)
        for index, source_path in enumerate(files, start=1):
            dest = workspace_root / "uploads" / "images" / f"sample_{clean_sample_id}" / f"image_{index}_{source_path.name}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest)
            copied_files.append(dest)
        resolved_files = copied_files
    return make_sample_manifest_row(sample_id, resolved_files)


def append_new_manifest_rows(workspace_root: Path, new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = read_manifest(workspace_root)
    existing_ids = {str(row.get("instance_id")) for row in existing}
    rows = existing + [row for row in new_rows if str(row.get("instance_id")) not in existing_ids]
    write_manifest(workspace_root, rows)
    return rows
