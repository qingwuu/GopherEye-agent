from __future__ import annotations

from pathlib import Path

from src.gophereye_runtime.utils import write_json

from .integrations import export_label_studio, log_mlflow, open_fiftyone, push_roboflow, sync_hf_hub, version_dvc, version_lakefs
from .labeling import run_labeling
from .manifest_store import read_manifest, write_manifest
from .paths import DEFAULT_JOB_ROOT, DEFAULT_WORKSPACE_ROOT, root_relative
from .patch_engine import patch_instances
from .schemas import JobResult, OperationPlan, OperationResult, OperationType
from .storage import create_job_dir
from .targets import resolve_targets
from .vision import run_augmentation, run_embeddings, run_segmentation


def execute_plan(
    plan: OperationPlan,
    *,
    apply: bool = False,
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
    job_root: Path = DEFAULT_JOB_ROOT,
    job_dir: Path | None = None,
) -> JobResult:
    job_dir = job_dir or create_job_dir(job_root=job_root)
    targets = resolve_targets(plan.target_selector, workspace_root=workspace_root)

    operation_results: list[OperationResult] = []
    for operation in plan.operations:
        selector = operation.target_selector or plan.target_selector
        op_targets = targets if selector == plan.target_selector else resolve_targets(selector, workspace_root=workspace_root)
        try:
            if operation.operation_type in {OperationType.MODIFY_MANIFEST, OperationType.MODIFY_INSTANCE_JSON}:
                result = patch_instances(
                    op_targets,
                    operation.patch_actions,
                    job_dir=job_dir,
                    apply=apply,
                    workspace_root=workspace_root,
                )
            elif operation.operation_type == OperationType.SEGMENTATION:
                result = run_segmentation(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.GRAPE_DISEASE_LABELING:
                result = run_labeling(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.EMBEDDING:
                result = run_embeddings(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.AUGMENTATION:
                result = run_augmentation(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.EXPORT_LABEL_STUDIO:
                result = export_label_studio(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.OPEN_FIFTYONE:
                result = open_fiftyone(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.PUSH_ROBOFLOW:
                result = push_roboflow(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.SYNC_HF_HUB:
                result = sync_hf_hub(job_dir, operation.params)
            elif operation.operation_type == OperationType.LOG_MLFLOW:
                result = log_mlflow(job_dir, operation.params)
            elif operation.operation_type == OperationType.VERSION_DVC:
                result = version_dvc(job_dir, {**operation.params, "apply": apply})
            elif operation.operation_type == OperationType.VERSION_LAKEFS:
                result = version_lakefs(job_dir, operation.params)
            else:
                result = OperationResult(
                    operation_type=str(operation.operation_type),
                    status="skipped",
                    message="Unsupported operation.",
                    targets_seen=len(op_targets),
                )
        except Exception as exc:
            result = OperationResult(
                operation_type=str(operation.operation_type),
                status="failed",
                message=f"Operation raised {type(exc).__name__}: {exc}",
                targets_seen=len(op_targets),
            )
        operation_results.append(result)
        update_manifest_from_result(workspace_root, result)

    status = "ok"
    blocking_statuses = {"failed", "not_available"}
    if any(result.status in blocking_statuses for result in operation_results):
        status = "partial" if any(result.status in {"ok", "skipped"} for result in operation_results) else "failed"
    dry_run_operations = {
        OperationType.MODIFY_MANIFEST,
        OperationType.MODIFY_INSTANCE_JSON,
        OperationType.VERSION_DVC,
    }
    has_dry_run_operation = any(operation.operation_type in dry_run_operations for operation in plan.operations)
    job_result = JobResult(
        job_id=job_dir.name,
        job_dir=root_relative(job_dir) or str(job_dir),
        dry_run=has_dry_run_operation and not apply,
        plan=plan,
        targets=targets,
        operation_results=operation_results,
        status=status,  # type: ignore[arg-type]
    )
    write_json(job_dir / "run_summary.json", summarize_job_result(job_result))
    return job_result


def summarize_job_result(job_result: JobResult) -> dict[str, object]:
    operations = []
    for result in job_result.operation_results:
        row = {
            "operation_type": result.operation_type,
            "status": result.status,
            "message": result.message,
            "artifacts": result.artifacts,
        }
        errors = result.details.get("errors") if isinstance(result.details, dict) else None
        if errors:
            row["errors"] = errors
        operations.append(row)
    return {
        "job_id": job_result.job_id,
        "job_dir": job_result.job_dir,
        "status": job_result.status,
        "dry_run": job_result.dry_run,
        "target_count": len(job_result.targets),
        "targets": [target.instance_id for target in job_result.targets],
        "operations": operations,
    }


def update_manifest_from_result(workspace_root: Path, result: OperationResult) -> None:
    rows = read_manifest(workspace_root)
    if not rows:
        return
    by_id = {str(row.get("instance_id")): row for row in rows}
    changed = False

    if result.operation_type == "grape_disease_labeling":
        for proposal in result.details.get("proposals", []):
            instance_id = str(proposal.get("instance_id") or "")
            row = by_id.get(instance_id)
            if not row:
                continue
            row["label"] = proposal.get("disease") or "unknown"
            row["label_confidence"] = proposal.get("confidence") or "unknown"
            source = proposal.get("source", {}) if isinstance(proposal.get("source"), dict) else {}
            row["label_source"] = source.get("provider") or source.get("method") or "data_agent_labeling"
            for artifact in result.artifacts:
                if instance_id in artifact:
                    row["latest_label_artifact"] = artifact
                    break
            changed = True

    artifact_field_by_operation = {
        "segmentation": "latest_segmentation_artifact",
        "embedding": "latest_embedding_artifact",
        "augmentation": "latest_augmentation_artifact",
    }
    artifact_field = artifact_field_by_operation.get(result.operation_type)
    if artifact_field and result.artifacts:
        artifact_value = result.artifacts[-1]
        for row in rows:
            row[artifact_field] = artifact_value
        changed = True

    if changed:
        write_manifest(workspace_root, rows)
