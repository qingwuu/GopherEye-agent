from __future__ import annotations

from pathlib import Path

from src.gophereye_runtime.utils import write_json

from .integrations import export_label_studio, log_mlflow, open_fiftyone, sync_hf_hub, version_dvc, version_lakefs
from .labeling import run_labeling
from .paths import DEFAULT_JOB_ROOT, DEFAULT_WORKSPACE_ROOT, root_relative
from .patch_engine import patch_instances
from .schemas import JobResult, OperationPlan, OperationResult, OperationType
from .storage import create_job_dir, write_audit_event, write_job_json
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
    write_job_json(job_dir, "operation_plan.json", plan.model_dump())
    targets = resolve_targets(plan.target_selector, workspace_root=workspace_root)
    write_job_json(job_dir, "resolved_targets.json", [target.model_dump() for target in targets])
    write_audit_event(
        job_dir,
        {
            "event_type": "job_started",
            "job_id": job_dir.name,
            "dry_run": not apply,
            "target_count": len(targets),
        },
    )

    operation_results: list[OperationResult] = []
    for operation in plan.operations:
        selector = operation.target_selector or plan.target_selector
        op_targets = targets if selector == plan.target_selector else resolve_targets(selector, workspace_root=workspace_root)
        try:
            if operation.operation_type == OperationType.MODIFY_INSTANCE_JSON:
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
                result = run_labeling(op_targets, job_dir=job_dir, params=operation.params)
            elif operation.operation_type == OperationType.EMBEDDING:
                result = run_embeddings(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.AUGMENTATION:
                result = run_augmentation(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.EXPORT_LABEL_STUDIO:
                result = export_label_studio(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
            elif operation.operation_type == OperationType.OPEN_FIFTYONE:
                result = open_fiftyone(op_targets, job_dir=job_dir, params=operation.params, workspace_root=workspace_root)
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
        write_audit_event(
            job_dir,
            {
                "event_type": "operation_finished",
                "operation_type": result.operation_type,
                "status": result.status,
                "message": result.message,
            },
        )

    status = "ok"
    blocking_statuses = {"failed", "not_available"}
    if any(result.status in blocking_statuses for result in operation_results):
        status = "partial" if any(result.status in {"ok", "skipped"} for result in operation_results) else "failed"
    job_result = JobResult(
        job_id=job_dir.name,
        job_dir=root_relative(job_dir) or str(job_dir),
        dry_run=not apply,
        plan=plan,
        targets=targets,
        operation_results=operation_results,
        status=status,  # type: ignore[arg-type]
    )
    write_json(job_dir / "job_result.json", job_result.model_dump())
    write_audit_event(job_dir, {"event_type": "job_finished", "status": status})
    return job_result
