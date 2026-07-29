from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.gophereye_runtime.utils import now_utc, parse_json_object, stable_id, write_json

from .schemas import InstanceTarget, OperationResult
from .storage import artifact_ref


DEFAULT_GRAPE_LABELS = ["powdery_mildew", "downy_mildew", "healthy", "unknown", "not_leaf"]


class GrapeDiseaseLabelProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_type: str = "grape_disease_label_proposal"
    schema_version: str = "gophereye.data_agent.grape_disease_label_proposal.v1"
    proposal_id: str
    instance_id: str
    created_at: str
    disease: str
    confidence: str = "unknown"
    evidence: list[str] = Field(default_factory=list)
    source: dict[str, Any] = Field(default_factory=dict)
    review_status: str = "unreviewed"
    is_ground_truth: bool = False


def heuristic_label(target: InstanceTarget, allowed_labels: list[str]) -> GrapeDiseaseLabelProposal:
    model_label = target.model_label or {}
    diagnosis = model_label.get("model_diagnosis") if isinstance(model_label.get("model_diagnosis"), dict) else {}
    raw_label = str(diagnosis.get("label") or "").strip().lower().replace(" ", "_")
    evidence = []
    disease = raw_label if raw_label in allowed_labels else "unknown"
    confidence = str(diagnosis.get("confidence") or "unknown")

    text_blob = json.dumps(model_label, ensure_ascii=False).lower()
    if disease == "unknown":
        if "powdery" in text_blob:
            disease = "powdery_mildew"
            evidence.append("Existing model output mentions powdery mildew evidence.")
        elif "downy" in text_blob or "oil spot" in text_blob:
            disease = "downy_mildew"
            evidence.append("Existing model output mentions downy mildew or oil spot evidence.")
        elif "healthy_uniform_green" in text_blob or "healthy" in text_blob:
            disease = "healthy"
            evidence.append("Existing model output mentions healthy appearance.")
        elif "not_leaf" in text_blob:
            disease = "not_leaf"
            evidence.append("Existing model output indicates not_leaf.")

    if disease not in allowed_labels:
        disease = "unknown"

    for item in model_label.get("evidence_present") or []:
        if isinstance(item, str):
            evidence.append(item)
    return GrapeDiseaseLabelProposal(
        proposal_id=stable_id("gdl", target.instance_id, disease, now_utc()),
        instance_id=target.instance_id,
        created_at=now_utc(),
        disease=disease,
        confidence=confidence,
        evidence=evidence[:8],
        source={"method": "heuristic_existing_workspace_fields"},
    )


def openai_label(target: InstanceTarget, allowed_labels: list[str], *, model: str) -> GrapeDiseaseLabelProposal:
    from openai import OpenAI

    schema = GrapeDiseaseLabelProposal.model_json_schema()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or None)
    prompt = {
        "instance_id": target.instance_id,
        "allowed_labels": allowed_labels,
        "model_label": target.model_label,
        "review": target.review,
        "image_links": target.image_links,
    }
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "Return a grape disease label proposal only. It is not ground truth.",
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "grape_disease_label_proposal",
                "schema": schema,
                "strict": True,
            }
        },
    )
    raw = getattr(response, "output_text", "") or ""
    parsed = parse_json_object(raw) or json.loads(raw)
    proposal = GrapeDiseaseLabelProposal.model_validate(parsed)
    if proposal.disease not in allowed_labels:
        proposal.disease = "unknown"
    proposal.is_ground_truth = False
    proposal.review_status = "unreviewed"
    return proposal


def run_labeling(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
) -> OperationResult:
    allowed_labels = params.get("allowed_labels") or DEFAULT_GRAPE_LABELS
    provider = params.get("provider") or "heuristic"
    model = params.get("model") or "gpt-5-mini"
    out_dir = job_dir / "artifacts" / "labels"
    out_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[str] = []
    errors: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    for target in targets:
        try:
            if provider == "openai":
                proposal = openai_label(target, allowed_labels, model=model)
            else:
                proposal = heuristic_label(target, allowed_labels)
            path = out_dir / f"{target.instance_id}.grape_label_proposal.json"
            write_json(path, proposal.model_dump())
            artifacts.append(artifact_ref(path))
            proposals.append(proposal.model_dump())
        except Exception as exc:
            errors.append({"instance_id": target.instance_id, "error": str(exc)})

    return OperationResult(
        operation_type="grape_disease_labeling",
        status="ok" if not errors else "failed" if not proposals else "ok",
        message=f"Created {len(proposals)} label proposals; {len(errors)} errors.",
        targets_seen=len(targets),
        artifacts=artifacts,
        details={"proposals": proposals, "errors": errors},
    )
