from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.gophereye_runtime.utils import now_utc, parse_json_object, stable_id, write_json

from .schemas import InstanceTarget, OperationResult
from .storage import artifact_ref
from .targets import local_image_paths


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
    source: dict[str, str] = Field(default_factory=dict)
    review_status: str = "unreviewed"
    is_ground_truth: bool = False


def normalize_string_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None and str(item).strip()]
    return [str(value)]


def normalize_string_map(value: Any) -> dict[str, str]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items() if item is not None}
    return {"method": str(value)}


def normalize_disease_label(value: Any, allowed_labels: list[str]) -> str:
    disease = str(value or "unknown").strip().lower().replace(" ", "_").replace("-", "_")
    return disease if disease in allowed_labels else "unknown"


def normalize_label_payload(
    parsed: dict[str, Any],
    target: InstanceTarget,
    allowed_labels: list[str],
) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        raise ValueError("LLM labeler did not return a JSON object.")

    disease = normalize_disease_label(parsed.get("disease") or parsed.get("label"), allowed_labels)
    return {
        "record_type": "grape_disease_label_proposal",
        "schema_version": "gophereye.data_agent.grape_disease_label_proposal.v1",
        "proposal_id": str(parsed.get("proposal_id") or stable_id("gdl", target.instance_id, disease, now_utc())),
        "instance_id": target.instance_id,
        "created_at": str(parsed.get("created_at") or now_utc()),
        "disease": disease,
        "confidence": str(parsed.get("confidence") or "unknown"),
        "evidence": normalize_string_list(parsed.get("evidence") or parsed.get("reasoning") or parsed.get("notes"))[:8],
        "source": normalize_string_map(parsed.get("source")),
        "review_status": "unreviewed",
        "is_ground_truth": False,
    }


LABEL_SYSTEM_PROMPT = """You are the GopherEye Data Agent grape disease labeler.

Inspect the provided grape leaf image sample and return a label proposal only.
The sample may contain one image, a front/back pair, or more related images of the same leaf/sample.
Allowed disease labels are: powdery_mildew, downy_mildew, healthy, unknown, not_leaf.

Rules:
- This is not ground truth.
- Use unknown when image evidence is insufficient.
- Prefer conservative evidence-based labels.
- Evidence should mention visible image cues, not hidden assumptions.
"""


def require_ascii_api_key(env_name: str) -> str:
    key = os.getenv(env_name) or ""
    if not key:
        raise RuntimeError(f"{env_name} is not set.")
    try:
        key.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RuntimeError(f"{env_name} must be an ASCII API key. It looks like a placeholder or non-ASCII text.") from exc
    return key


def path_to_data_url(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def path_to_anthropic_image_block(path: Path) -> dict[str, Any]:
    data_url = path_to_data_url(path)
    header, data = data_url.split(",", 1)
    media_type = header.removeprefix("data:").split(";", 1)[0]
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": data,
        },
    }


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


def label_prompt_payload(target: InstanceTarget, allowed_labels: list[str], image_paths: list[Path]) -> dict[str, Any]:
    return {
        "instance_id": target.instance_id,
        "allowed_labels": allowed_labels,
        "manifest_row": target.manifest,
        "image_paths": [str(path) for path in image_paths],
        "instructions": "Return one grape disease label proposal for this image sample.",
    }


def finalize_proposal(proposal: GrapeDiseaseLabelProposal, target: InstanceTarget, allowed_labels: list[str], provider: str) -> GrapeDiseaseLabelProposal:
    proposal.instance_id = target.instance_id
    proposal.created_at = proposal.created_at or now_utc()
    if proposal.disease not in allowed_labels:
        proposal.disease = "unknown"
    proposal.is_ground_truth = False
    proposal.review_status = "unreviewed"
    proposal.source = {**proposal.source, "provider": provider}
    return proposal


def openai_label(
    target: InstanceTarget,
    allowed_labels: list[str],
    *,
    model: str,
    image_paths: list[Path],
) -> GrapeDiseaseLabelProposal:
    from openai import OpenAI

    client = OpenAI(api_key=require_ascii_api_key("OPENAI_API_KEY"))
    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": (
                json.dumps(label_prompt_payload(target, allowed_labels, image_paths), ensure_ascii=False)
                + "\n\nReturn only a JSON object with these keys: "
                "proposal_id, instance_id, created_at, disease, confidence, evidence, source, "
                "review_status, is_ground_truth. "
                "Use source as a simple string map, for example {\"method\":\"vision_llm\"}."
            ),
        }
    ]
    for image_path in image_paths:
        content.append({"type": "input_image", "image_url": path_to_data_url(image_path)})
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": LABEL_SYSTEM_PROMPT,
            },
            {"role": "user", "content": content},
        ],
    )
    raw = getattr(response, "output_text", "") or ""
    parsed = parse_json_object(raw) or json.loads(raw)
    proposal = GrapeDiseaseLabelProposal.model_validate(normalize_label_payload(parsed, target, allowed_labels))
    return finalize_proposal(proposal, target, allowed_labels, provider="openai")


def anthropic_label(
    target: InstanceTarget,
    allowed_labels: list[str],
    *,
    model: str,
    image_paths: list[Path],
) -> GrapeDiseaseLabelProposal:
    from anthropic import Anthropic

    client = Anthropic(api_key=require_ascii_api_key("ANTHROPIC_API_KEY"))
    schema = GrapeDiseaseLabelProposal.model_json_schema()
    content: list[dict[str, Any]] = []
    for idx, image_path in enumerate(image_paths, start=1):
        content.append({"type": "text", "text": f"Image {idx}: {image_path.name}"})
        content.append(path_to_anthropic_image_block(image_path))
    content.append(
        {
            "type": "text",
            "text": LABEL_SYSTEM_PROMPT
            + "\n\nInput JSON:\n"
            + json.dumps(label_prompt_payload(target, allowed_labels, image_paths), ensure_ascii=False),
        }
    )
    message = client.messages.create(
        model=model,
        max_tokens=1600,
        tools=[
            {
                "name": "submit_grape_disease_label_proposal",
                "description": "Submit the image-based grape disease label proposal.",
                "input_schema": schema,
            }
        ],
        tool_choice={"type": "tool", "name": "submit_grape_disease_label_proposal"},
        messages=[{"role": "user", "content": content}],
    )
    for block in message.content:
        if getattr(block, "type", None) == "tool_use":
            proposal = GrapeDiseaseLabelProposal.model_validate(
                normalize_label_payload(getattr(block, "input"), target, allowed_labels)
            )
            return finalize_proposal(proposal, target, allowed_labels, provider="anthropic")
    raise RuntimeError("Anthropic labeler did not return a tool call.")


def run_labeling(
    targets: list[InstanceTarget],
    *,
    job_dir: Path,
    params: dict[str, Any],
    workspace_root: Path,
) -> OperationResult:
    allowed_labels = params.get("allowed_labels") or DEFAULT_GRAPE_LABELS
    provider = params.get("provider") or "heuristic"
    model = params.get("model") or ("claude-sonnet-4-5" if provider == "anthropic" else "gpt-5-mini")
    write_artifacts = bool(params.get("write_artifacts", True))
    out_dir = job_dir / "artifacts" / "labels"
    if write_artifacts:
        out_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[str] = []
    errors: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    for target in targets:
        try:
            image_paths = local_image_paths(target, workspace_root=workspace_root)
            if provider == "openai":
                proposal = openai_label(target, allowed_labels, model=model, image_paths=image_paths)
            elif provider in {"anthropic", "claude"}:
                proposal = anthropic_label(target, allowed_labels, model=model, image_paths=image_paths)
            else:
                proposal = heuristic_label(target, allowed_labels)
            if write_artifacts:
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
        details={"proposals": proposals, "errors": errors, "write_artifacts": write_artifacts},
    )
