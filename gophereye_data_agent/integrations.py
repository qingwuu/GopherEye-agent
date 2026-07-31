from __future__ import annotations

import contextlib
import base64
import io
import json
import logging
import mimetypes
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib import error, request

from src.gophereye_runtime.utils import write_json

from .paths import DEFAULT_WORKSPACE_ROOT, root_relative
from .schemas import InstanceTarget, OperationResult
from .storage import artifact_ref
from .targets import local_image_paths


GRAPE_LABEL_CONFIG = """
<View>
  <Image name="image" value="$image"/>
  <Choices name="disease" toName="image" choice="single" showInLine="true">
    <Choice value="powdery_mildew"/>
    <Choice value="downy_mildew"/>
    <Choice value="healthy"/>
    <Choice value="unknown"/>
    <Choice value="not_leaf"/>
  </Choices>
  <BrushLabels name="mask" toName="image">
    <Label value="leaf"/>
    <Label value="disease_region"/>
  </BrushLabels>
</View>
""".strip()


def path_to_data_url(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "image/jpeg"
    return f"data:{mime_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def export_label_studio(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
) -> OperationResult:
    tasks: list[dict[str, Any]] = []
    embed_images = bool(params.get("embed_images"))
    for target in targets:
        image_paths = local_image_paths(target, workspace_root=workspace_root)
        for image_path in image_paths:
            image_value = path_to_data_url(image_path) if embed_images else str(image_path)
            tasks.append(
                {
                    "data": {"image": image_value},
                    "meta": {
                        "instance_id": target.instance_id,
                        "sample_id": target.manifest.get("sample_id") or target.manifest.get("pair_id"),
                        "sample_type": target.manifest.get("sample_type"),
                        "image_count": target.manifest.get("image_count"),
                        "source_image": str(image_path),
                        "model_diagnosis": target.model_label.get("model_diagnosis"),
                        "evidence_status": target.model_label.get("evidence_status"),
                    },
                }
            )
    out_path = job_dir / "artifacts" / (params.get("output_name") or "label_studio_tasks.json")
    write_json(out_path, tasks)
    details: dict[str, Any] = {"tasks": len(tasks), "embedded_images": embed_images}
    message = f"Exported {len(tasks)} Label Studio tasks."
    status = "ok"
    if params.get("upload"):
        upload_result = upload_label_studio_tasks(tasks, params=params)
        details["upload"] = upload_result
        message += " " + upload_result["message"]
        if upload_result.get("status") != "ok":
            status = "failed"
    return OperationResult(
        operation_type="export_label_studio",
        status=status,
        message=message,
        targets_seen=len(targets),
        artifacts=[artifact_ref(out_path)],
        details=details,
    )


def label_studio_request(url: str, api_key: str, path: str, payload: Any) -> Any:
    endpoint = url.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    last_auth_error: error.HTTPError | None = None
    for auth_scheme in ("Token", "Bearer"):
        req = request.Request(
            endpoint,
            data=data,
            headers={
                "Authorization": f"{auth_scheme} {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            if exc.code in {401, 403}:
                last_auth_error = exc
                continue
            raise
    if last_auth_error is not None:
        raise PermissionError(
            "Label Studio rejected the API token "
            f"(HTTP {last_auth_error.code}). Set LABEL_STUDIO_API_KEY to the token from the same "
            "Label Studio account and local server you are using in the browser."
        ) from last_auth_error
    raise RuntimeError("Label Studio request failed without a response.")


def upload_label_studio_tasks(tasks: list[dict[str, Any]], *, params: dict[str, Any]) -> dict[str, Any]:
    url = params.get("url") or os.getenv("LABEL_STUDIO_URL") or "http://127.0.0.1:8080"
    api_key = params.get("api_key") or os.getenv("LABEL_STUDIO_API_KEY") or os.getenv("LABEL_STUDIO_TOKEN")
    if not api_key:
        return {
            "status": "skipped",
            "message": "Label Studio upload skipped: set LABEL_STUDIO_API_KEY or LABEL_STUDIO_TOKEN.",
        }
    try:
        project_id = params.get("project_id")
        if not project_id:
            created = label_studio_request(
                str(url),
                str(api_key),
                "/api/projects/",
                {
                    "title": params.get("project_title") or "GopherEye Data Agent",
                    "label_config": params.get("label_config") or GRAPE_LABEL_CONFIG,
                },
            )
            project_id = created.get("id")
        if not project_id:
            return {"status": "failed", "message": "Label Studio project id was not returned."}
        imported = label_studio_request(str(url), str(api_key), f"/api/projects/{project_id}/import", tasks)
        return {
            "status": "ok",
            "message": f"Uploaded {len(tasks)} tasks to Label Studio project {project_id}.",
            "url": str(url),
            "project_id": project_id,
            "response": imported,
        }
    except Exception as exc:
        return {"status": "failed", "message": f"Label Studio upload failed: {exc}", "url": str(url)}


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
    dataset.persistent = True
    samples = []
    for target in targets:
        for image_path in local_image_paths(target, workspace_root=workspace_root):
            samples.append(
                fo.Sample(
                    filepath=str(image_path),
                    instance_id=target.instance_id,
                    sample_id=target.manifest.get("sample_id") or target.manifest.get("pair_id"),
                    sample_type=target.manifest.get("sample_type"),
                    image_count=target.manifest.get("image_count"),
                    evidence_status=target.model_label.get("evidence_status"),
                    model_label=json.dumps(target.model_label.get("model_diagnosis"), ensure_ascii=False),
                )
            )
    if samples:
        dataset.add_samples(samples)
    manifest = job_dir / "artifacts" / "fiftyone_dataset.json"
    write_json(manifest, {"dataset_name": dataset_name, "samples": len(samples), "persistent": True})
    return OperationResult(
        operation_type="open_fiftyone",
        status="ok",
        message=f"Loaded {len(samples)} samples into FiftyOne dataset {dataset_name!r}.",
        targets_seen=len(targets),
        artifacts=[artifact_ref(manifest)],
        details={"dataset_name": dataset_name, "samples": len(samples)},
    )


def push_roboflow(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
) -> OperationResult:
    api_key = params.get("api_key") or os.getenv("ROBOFLOW_API_KEY")
    workspace_name = params.get("workspace") or os.getenv("ROBOFLOW_WORKSPACE")
    project_name = params.get("project") or os.getenv("ROBOFLOW_PROJECT")
    if not api_key or not workspace_name or not project_name:
        manifest = job_dir / "artifacts" / "roboflow_push_skipped.json"
        write_json(
            manifest,
            {
                "status": "skipped",
                "required_env": ["ROBOFLOW_API_KEY", "ROBOFLOW_WORKSPACE", "ROBOFLOW_PROJECT"],
            },
        )
        return OperationResult(
            operation_type="push_roboflow",
            status="skipped",
            message="Roboflow push skipped: set ROBOFLOW_API_KEY, ROBOFLOW_WORKSPACE, and ROBOFLOW_PROJECT.",
            targets_seen=len(targets),
            artifacts=[artifact_ref(manifest)],
        )
    try:
        from roboflow import Roboflow
    except Exception as exc:
        return OperationResult(
            operation_type="push_roboflow",
            status="not_available",
            message=f"roboflow package is not installed: {exc}",
            targets_seen=len(targets),
        )

    uploaded: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    try:
        project = Roboflow(api_key=api_key).workspace(workspace_name).project(project_name)
    except Exception as exc:
        return OperationResult(
            operation_type="push_roboflow",
            status="failed",
            message=f"Could not open Roboflow project {workspace_name}/{project_name}: {exc}",
            targets_seen=len(targets),
        )
    for target in targets:
        for image_path in local_image_paths(target, workspace_root=workspace_root):
            try:
                response = project.upload(str(image_path))
                uploaded.append({"instance_id": target.instance_id, "image_path": str(image_path), "response": response})
            except Exception as exc:
                errors.append({"instance_id": target.instance_id, "image_path": str(image_path), "error": str(exc)})
    manifest = job_dir / "artifacts" / "roboflow_push.json"
    write_json(manifest, {"uploaded": uploaded, "errors": errors})
    return OperationResult(
        operation_type="push_roboflow",
        status="ok" if not errors else "failed" if not uploaded else "ok",
        message=f"Uploaded {len(uploaded)} images to Roboflow; {len(errors)} errors.",
        targets_seen=len(targets),
        artifacts=[artifact_ref(manifest)],
        details={"uploaded": len(uploaded), "errors": errors},
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
