from __future__ import annotations

import contextlib
import io
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import write_json

from .paths import DEFAULT_WORKSPACE_ROOT, root_relative
from .schemas import InstanceTarget, OperationResult
from .storage import artifact_ref
from .targets import local_image_paths


def export_label_studio(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
) -> OperationResult:
    tasks: list[dict[str, Any]] = []
    for target in targets:
        image_paths = local_image_paths(target, workspace_root=workspace_root)
        for image_path in image_paths:
            tasks.append(
                {
                    "data": {"image": str(image_path)},
                    "meta": {
                        "instance_id": target.instance_id,
                        "model_diagnosis": target.model_label.get("model_diagnosis"),
                        "evidence_status": target.model_label.get("evidence_status"),
                    },
                }
            )
    out_path = job_dir / "artifacts" / (params.get("output_name") or "label_studio_tasks.json")
    write_json(out_path, tasks)
    return OperationResult(
        operation_type="export_label_studio",
        status="ok",
        message=f"Exported {len(tasks)} Label Studio tasks.",
        targets_seen=len(targets),
        artifacts=[artifact_ref(out_path)],
        details={"tasks": len(tasks)},
    )


def open_fiftyone(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
) -> OperationResult:
    try:
        import fiftyone as fo
    except Exception as exc:
        return OperationResult(
            operation_type="open_fiftyone",
            status="not_available",
            message=f"fiftyone is not installed: {exc}",
            targets_seen=len(targets),
        )
    base_name = params.get("dataset_name") or "gophereye_data_agent"
    dataset_name = base_name if params.get("overwrite") else f"{base_name}_{job_dir.name}"
    if fo.dataset_exists(dataset_name) and params.get("overwrite"):
        dataset = fo.load_dataset(dataset_name)
        dataset.delete_samples()
    elif fo.dataset_exists(dataset_name):
        dataset_name = f"{base_name}_{job_dir.name}"
        dataset = fo.Dataset(dataset_name)
    else:
        dataset = fo.Dataset(dataset_name)
    samples = []
    for target in targets:
        for image_path in local_image_paths(target, workspace_root=workspace_root):
            samples.append(
                fo.Sample(
                    filepath=str(image_path),
                    instance_id=target.instance_id,
                    evidence_status=target.model_label.get("evidence_status"),
                    model_label=json.dumps(target.model_label.get("model_diagnosis"), ensure_ascii=False),
                )
            )
    if samples:
        dataset.add_samples(samples)
    manifest = job_dir / "artifacts" / "fiftyone_dataset.json"
    write_json(manifest, {"dataset_name": dataset_name, "samples": len(samples)})
    return OperationResult(
        operation_type="open_fiftyone",
        status="ok",
        message=f"Loaded {len(samples)} samples into FiftyOne dataset {dataset_name!r}.",
        targets_seen=len(targets),
        artifacts=[artifact_ref(manifest)],
        details={"dataset_name": dataset_name, "samples": len(samples)},
    )


def sync_hf_hub(job_dir: Path, params: dict[str, Any]) -> OperationResult:
    repo_id = params.get("repo_id")
    repo_type = params.get("repo_type") or "dataset"
    if not repo_id:
        return OperationResult(
            operation_type="sync_hf_hub",
            status="skipped",
            message="repo_id is required for Hugging Face Hub upload.",
        )
    try:
        from huggingface_hub import HfApi
    except Exception as exc:
        return OperationResult(operation_type="sync_hf_hub", status="not_available", message=str(exc))
    api = HfApi()
    api.upload_folder(
        repo_id=repo_id,
        repo_type=repo_type,
        folder_path=str(job_dir),
        path_in_repo=params.get("path_in_repo") or job_dir.name,
    )
    return OperationResult(
        operation_type="sync_hf_hub",
        status="ok",
        message=f"Uploaded job folder to Hugging Face Hub repo {repo_id}.",
        artifacts=[f"hf://{repo_type}/{repo_id}/{params.get('path_in_repo') or job_dir.name}"],
    )


def log_mlflow(job_dir: Path, params: dict[str, Any]) -> OperationResult:
    try:
        import mlflow
    except Exception as exc:
        return OperationResult(operation_type="log_mlflow", status="not_available", message=str(exc))
    logging.getLogger("mlflow").setLevel(logging.WARNING)
    experiment = params.get("experiment") or "gophereye_data_agent"
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        mlflow.set_experiment(experiment)
        with mlflow.start_run(run_name=job_dir.name):
            mlflow.log_param("job_id", job_dir.name)
            mlflow.log_artifacts(str(job_dir))
    return OperationResult(
        operation_type="log_mlflow",
        status="ok",
        message=f"Logged job {job_dir.name} to MLflow experiment {experiment!r}.",
    )


def version_dvc(job_dir: Path, params: dict[str, Any]) -> OperationResult:
    dvc = shutil.which("dvc")
    command = [dvc] if dvc else [sys.executable, "-m", "dvc"]
    if not dvc:
        try:
            __import__("dvc")
        except Exception:
            return OperationResult(operation_type="version_dvc", status="not_available", message="dvc CLI is not installed.")
    target = params.get("target") or root_relative(job_dir)
    if params.get("apply"):
        completed = subprocess.run([*command, "add", str(target)], cwd=job_dir.parents[2], text=True, capture_output=True)
        status = "ok" if completed.returncode == 0 else "failed"
        message = completed.stdout.strip() or completed.stderr.strip()
    else:
        status = "skipped"
        message = f"Dry-run: would run `dvc add {target}`."
    return OperationResult(operation_type="version_dvc", status=status, message=message)


def version_lakefs(job_dir: Path, params: dict[str, Any]) -> OperationResult:
    try:
        __import__("lakefs")
    except Exception as exc:
        return OperationResult(operation_type="version_lakefs", status="not_available", message=str(exc))
    return OperationResult(
        operation_type="version_lakefs",
        status="skipped",
        message="lakeFS Python client is available, but repository/branch/storage parameters must be configured before commits.",
        details={"required_params": ["repo", "branch", "path"]},
    )
