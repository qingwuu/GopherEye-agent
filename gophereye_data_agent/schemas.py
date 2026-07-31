from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OperationType(str, Enum):
    MODIFY_MANIFEST = "modify_manifest"
    MODIFY_INSTANCE_JSON = "modify_instance_json"
    SEGMENTATION = "segmentation"
    GRAPE_DISEASE_LABELING = "grape_disease_labeling"
    EMBEDDING = "embedding"
    AUGMENTATION = "augmentation"
    EXPORT_LABEL_STUDIO = "export_label_studio"
    OPEN_FIFTYONE = "open_fiftyone"
    SYNC_HF_HUB = "sync_hf_hub"
    LOG_MLFLOW = "log_mlflow"
    VERSION_DVC = "version_dvc"
    VERSION_LAKEFS = "version_lakefs"


class TargetSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal[
        "dataset",
        "workspace_instances",
        "pending_reviews",
        "completed_reviews",
        "reviewed_dataset",
        "explicit_paths",
    ] = "dataset"
    instance_ids: list[str] = Field(default_factory=list)
    image_ids: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)
    review_status: list[str] = Field(default_factory=list)
    evidence_status: list[str] = Field(default_factory=list)
    model_labels: list[str] = Field(default_factory=list)
    max_items: int | None = Field(default=50, ge=1)
    include_without_images: bool = False


class WritePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modify_dataset_manifest: bool = True
    require_apply_confirmation: bool = True
    ground_truth_allowed: bool = False
    audit_required: bool = True
    validate_after_write: bool = True


class JsonPatchAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["set", "add_to_list", "remove_key"] = "set"
    file: Literal[
        "manifest",
        "upload_record",
        "model_label",
        "human_review_template",
        "human_review_submitted",
        "custom",
    ]
    custom_file: str | None = None
    json_pointer: str = Field(description="RFC-6901-like JSON pointer, e.g. /corrections/group_id.")
    value: Any = None
    reason: str = ""


class DataOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_type: OperationType
    description: str = ""
    target_selector: TargetSelector | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    patch_actions: list[JsonPatchAction] = Field(default_factory=list)


class OperationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["gophereye.data_agent.operation_plan.v1"] = "gophereye.data_agent.operation_plan.v1"
    plan_id: str
    user_prompt: str
    created_at: str
    planner: Literal["rule", "openai", "anthropic", "manual"] = "rule"
    dry_run_default: bool = True
    target_selector: TargetSelector = Field(default_factory=TargetSelector)
    operations: list[DataOperation] = Field(default_factory=list)
    write_policy: WritePolicy = Field(default_factory=WritePolicy)
    notes: list[str] = Field(default_factory=list)


class InstanceTarget(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    instance_id: str
    instance_dir: str | None = None
    source: dict[str, Any] = Field(default_factory=dict)
    manifest: dict[str, Any] = Field(default_factory=dict)
    model_label: dict[str, Any] = Field(default_factory=dict)
    upload_record: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    image_links: list[dict[str, Any]] = Field(default_factory=list)


class OperationResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    operation_type: str
    status: Literal["ok", "skipped", "failed", "not_available"]
    message: str = ""
    targets_seen: int = 0
    artifacts: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class JobResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    job_id: str
    job_dir: str
    dry_run: bool
    plan: OperationPlan
    targets: list[InstanceTarget]
    operation_results: list[OperationResult] = Field(default_factory=list)
    status: Literal["ok", "partial", "failed"] = "ok"
