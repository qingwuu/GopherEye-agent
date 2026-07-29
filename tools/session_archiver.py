from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.gophereye_runtime.utils import (
    local_path_from_ref as runtime_local_path_from_ref,
    normalize_repo_path,
    now_utc,
    parse_json_object,
    read_json,
    read_jsonl,
    root_relative as runtime_root_relative,
    safe_component,
    safe_print,
    stable_id,
    write_json,
    write_jsonl,
)


DEFAULT_ARCHIVE_ROOT = ROOT_DIR / "data_agent"
DEFAULT_DATA_ROOT = DEFAULT_ARCHIVE_ROOT
DEFAULT_FRONTIER_SESSION_DIR = ROOT_DIR / "sessions" / "frontier"
SCHEMA_DIR = ROOT_DIR / "schemas" / "data_agent"

REVIEW_DECISIONS = {
    "accept_model_label",
    "correct_label",
    "reject_not_leaf",
    "reject_unusable_image",
    "needs_more_evidence",
}
INGESTIBLE_REVIEW_DECISIONS = {"accept_model_label", "correct_label"}


def normalize_path(path_text: str | Path) -> Path:
    return normalize_repo_path(ROOT_DIR, path_text)


def root_relative(path: str | Path | None) -> str | None:
    return runtime_root_relative(ROOT_DIR, path)


def local_path_from_ref(ref: str | None) -> Path | None:
    return runtime_local_path_from_ref(ROOT_DIR, ref)


def ensure_layout(data_root: Path) -> Dict[str, Path]:
    paths = {
        "root": data_root,
        "instances": data_root / "instances",
        "uploads": data_root / "uploads",
        "upload_images": data_root / "uploads" / "images",
        "indexes": data_root / "indexes",
        "review_queue": data_root / "review_queue",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def validate_with_schema(value: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
    schema_path = SCHEMA_DIR / schema_name
    if not schema_path.exists():
        return {"valid": None, "note": f"schema file not found: {root_relative(schema_path)}"}

    try:
        import jsonschema
    except Exception:
        return {"valid": None, "note": "jsonschema is not installed; JSON parsed successfully."}

    schema = read_json(schema_path)
    try:
        jsonschema.validate(instance=value, schema=schema)
    except jsonschema.ValidationError as exc:
        return {"valid": False, "error": exc.message}
    return {"valid": True}


def load_session_from_args(session_path: str | None, session_id: str | None, session_dir: Path) -> tuple[Path, Dict[str, Any]]:
    if session_path:
        path = normalize_path(session_path)
    elif session_id:
        path = session_dir / f"{safe_component(session_id)}.json"
    else:
        raise ValueError("Provide --session-path or --session-id.")

    if not path.exists():
        raise FileNotFoundError(f"Session file not found: {path}")
    session = read_json(path)
    if not isinstance(session, dict):
        raise ValueError(f"Session file is not a JSON object: {path}")
    return path, session


def iter_session_files(session_dir: Path) -> List[Path]:
    if not session_dir.exists():
        return []
    return sorted(path for path in session_dir.glob("*.json") if path.is_file())


def load_session_file(session_path: Path) -> Dict[str, Any]:
    session = read_json(session_path)
    if not isinstance(session, dict):
        raise ValueError(f"Session file is not a JSON object: {session_path}")
    return session


def is_archiveable_turn(turn: Dict[str, Any]) -> bool:
    task_type = ((turn.get("route") or {}).get("task_type") or "")
    if task_type == "visual_intake_or_diagnosis":
        return True
    return bool(turn.get("attached_image_manifest") or turn.get("requested_image_records"))


def archiveable_turns(session: Dict[str, Any], *, include_all_turns: bool = False) -> List[Dict[str, Any]]:
    turns = session.get("turns") or []
    if not isinstance(turns, list):
        return []
    out = [turn for turn in turns if isinstance(turn, dict)]
    if include_all_turns:
        return out
    return [turn for turn in out if is_archiveable_turn(turn)]


def find_turn(session: Dict[str, Any], turn_id: int | None) -> Dict[str, Any]:
    turns = session.get("turns") or []
    if not isinstance(turns, list) or not turns:
        raise ValueError("Session has no turn metadata to capture.")

    if turn_id is not None:
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            if turn.get("user_turn_id") == turn_id or turn.get("assistant_turn_id") == turn_id:
                return turn
        raise ValueError(f"No session turn found for turn id {turn_id}.")

    for turn in reversed(turns):
        if not isinstance(turn, dict):
            continue
        task_type = ((turn.get("route") or {}).get("task_type") or "")
        if task_type == "visual_intake_or_diagnosis":
            return turn
        if turn.get("attached_image_manifest") or turn.get("requested_image_records"):
            return turn
    return turns[-1]


def message_for_turn(session: Dict[str, Any], turn_id: int | None) -> Dict[str, Any] | None:
    if turn_id is None:
        return None
    for message in session.get("messages", []) or []:
        if isinstance(message, dict) and message.get("turn_id") == turn_id:
            return message
    return None


def has_record_value(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def merge_image_record(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if has_record_value(value):
            merged[key] = value
    return merged


def unique_image_items(session: Dict[str, Any], turn: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for key in ["attached_image_manifest", "requested_image_records"]:
        for item in turn.get(key) or []:
            if isinstance(item, dict):
                candidates.append(dict(item))

    user_message = message_for_turn(session, turn.get("user_turn_id"))
    for ref in (user_message or {}).get("image_refs") or []:
        candidates.append({"image_path": ref, "image_role": "user_upload"})

    known_by_path: Dict[str, Dict[str, Any]] = {}
    for item in session.get("short_term_memory", {}).get("known_images", []) or []:
        if not isinstance(item, dict):
            continue
        image_path = item.get("image_path") or item.get("source_ref")
        if image_path:
            known_by_path[str(image_path)] = item

    deduped: Dict[str, Dict[str, Any]] = {}
    for item in candidates:
        source_ref = item.get("image_path") or item.get("image_uri") or item.get("source_ref")
        if source_ref and str(source_ref) in known_by_path:
            item = {**known_by_path[str(source_ref)], **item}
        image_id = item.get("image_id") or stable_id("img", source_ref or item)
        item["image_id"] = str(image_id)
        item.setdefault("image_role", "user_upload")
        dedupe_key = str(image_id)
        if dedupe_key in deduped:
            item = merge_image_record(deduped[dedupe_key], item)
        deduped[dedupe_key] = item
    return list(deduped.values())


def copy_image_if_requested(data_root: Path, image_id: str, item: Dict[str, Any], copy_images: bool) -> Dict[str, Any]:
    if not copy_images:
        return {"copy_status": "not_requested", "stored_path": None}

    source = (
        local_path_from_ref(item.get("image_uri"))
        or local_path_from_ref(item.get("image_path"))
        or local_path_from_ref(item.get("source_ref"))
    )
    if source is None or not source.exists() or not source.is_file():
        return {"copy_status": "source_missing", "stored_path": None}

    target_dir = data_root / "uploads" / "images" / safe_component(image_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    shutil.copy2(source, target)
    return {"copy_status": "copied", "stored_path": root_relative(target)}


def build_upload_record(
    *,
    data_root: Path,
    instance_id: str,
    session: Dict[str, Any],
    turn: Dict[str, Any],
    image_items: Sequence[Dict[str, Any]],
    copy_images: bool,
) -> Dict[str, Any]:
    created_at = now_utc()
    uploads = []
    for image in image_items:
        image_id = str(image["image_id"])
        copy_info = copy_image_if_requested(data_root, image_id, image, copy_images)
        uploads.append(
            {
                "record_type": "upload_record",
                "schema_version": "data_agent.upload_record.v1",
                "upload_record_id": stable_id("upload", instance_id, image_id),
                "instance_id": instance_id,
                "image_id": image_id,
                "source_ref": image.get("image_path") or image.get("image_uri") or image.get("source_ref"),
                "image_uri": image.get("image_uri"),
                "stored_path": copy_info["stored_path"],
                "copy_status": copy_info["copy_status"],
                "image_role": image.get("image_role", "user_upload"),
                "session_id": session.get("session_id"),
                "turn_id": turn.get("user_turn_id"),
                "first_seen_turn_id": image.get("first_seen_turn_id"),
                "last_seen_turn_id": image.get("last_seen_turn_id"),
                "created_at": created_at,
                "review_status": "unreviewed",
                "is_ground_truth": False,
            }
        )

    return {
        "record_type": "upload_record_collection",
        "schema_version": "data_agent.upload_record_collection.v1",
        "instance_id": instance_id,
        "created_at": created_at,
        "uploads": uploads,
    }


def memory_update_for_turn(session: Dict[str, Any], turn: Dict[str, Any]) -> Dict[str, Any]:
    parsed = parse_json_object(turn.get("final_model_output"))
    if parsed and isinstance(parsed.get("memory_update"), dict):
        return parsed["memory_update"]
    memory = session.get("short_term_memory") or {}
    return memory if isinstance(memory, dict) else {}


def coerce_text_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        if isinstance(item, str):
            out.append(item)
        elif item is not None:
            out.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
    return out


def extract_visual_intakes(memory_update: Dict[str, Any], session: Dict[str, Any]) -> List[Dict[str, Any]]:
    value = memory_update.get("visual_intakes")
    if not isinstance(value, list):
        value = session.get("short_term_memory", {}).get("visual_intakes") or []
    return [item for item in value if isinstance(item, dict)]


def candidate_from_visual_intakes(visual_intakes: Sequence[Dict[str, Any]]) -> tuple[str | None, str | None]:
    for intake in visual_intakes:
        candidates = intake.get("candidate_diseases") or []
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            disease = candidate.get("disease")
            if disease:
                return str(disease), str(candidate.get("confidence") or "unknown")
    return None, None


def normalize_current_diagnosis(raw: Any, visual_intakes: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    label: str | None = None
    confidence: str | None = None
    if isinstance(raw, dict):
        label = raw.get("disease") or raw.get("label") or raw.get("diagnosis")
        confidence_value = raw.get("confidence") or raw.get("confidence_level")
        confidence = str(confidence_value) if confidence_value is not None else None
    elif isinstance(raw, str) and raw.strip():
        label = raw.strip()

    if not label:
        label, confidence = candidate_from_visual_intakes(visual_intakes)

    return {
        "label": label or "unknown",
        "confidence": confidence or "unknown",
        "raw_current_diagnosis": raw,
    }


def evidence_status(memory_update: Dict[str, Any], turn: Dict[str, Any], diagnosis_label: str) -> str:
    sufficiency = str(memory_update.get("evidence_sufficiency") or "")
    evidence_missing = coerce_text_list(memory_update.get("evidence_missing"))
    missing_images = [str(item) for item in turn.get("missing_image_refs") or []]
    recommended_next = memory_update.get("recommended_next_image")
    has_recommended_next = (
        recommended_next is not None
        and str(recommended_next).strip().lower() not in {"", "none", "null"}
    )
    if sufficiency == "sufficient_single_surface" and diagnosis_label and diagnosis_label != "unknown":
        return "single_surface_sufficient_label"
    if sufficiency.startswith("insufficient"):
        return "insufficient_evidence"
    if evidence_missing or missing_images or has_recommended_next:
        return "insufficient_evidence"
    if diagnosis_label and diagnosis_label != "unknown":
        return "provisional_label"
    return "insufficient_evidence"


def build_model_label(
    *,
    instance_id: str,
    session_path: Path,
    session: Dict[str, Any],
    turn: Dict[str, Any],
    image_items: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    parsed_final = parse_json_object(turn.get("final_model_output"))
    memory_update = memory_update_for_turn(session, turn)
    visual_intakes = extract_visual_intakes(memory_update, session)
    current_diagnosis = memory_update.get("current_diagnosis")
    if current_diagnosis is None:
        current_diagnosis = session.get("short_term_memory", {}).get("current_diagnosis")
    diagnosis = normalize_current_diagnosis(current_diagnosis, visual_intakes)
    status = evidence_status(memory_update, turn, diagnosis["label"])

    return {
        "record_type": "model_label",
        "schema_version": "data_agent.model_label.v1",
        "model_label_id": stable_id("ml", instance_id, turn.get("assistant_turn_id")),
        "instance_id": instance_id,
        "created_at": now_utc(),
        "label_source": "existing_session_agent_output",
        "generation_status": "machine_generated",
        "review_status": "unreviewed",
        "is_ground_truth": False,
        "evidence_status": status,
        "source": {
            "session_id": session.get("session_id"),
            "session_path": root_relative(session_path),
            "user_turn_id": turn.get("user_turn_id"),
            "assistant_turn_id": turn.get("assistant_turn_id"),
        },
        "model": {
            "provider": turn.get("provider") or session.get("provider"),
            "model": turn.get("model") or session.get("model"),
            "model_profile": turn.get("model_profile") or session.get("model_profile"),
        },
        "route": turn.get("route"),
        "context_label": turn.get("context_label"),
        "image_ids": [str(item["image_id"]) for item in image_items],
        "assistant_message": message_for_turn(session, turn.get("assistant_turn_id")) or {},
        "model_diagnosis": diagnosis,
        "visual_intakes": visual_intakes,
        "evidence_present": coerce_text_list(memory_update.get("evidence_present")),
        "evidence_missing": coerce_text_list(memory_update.get("evidence_missing")),
        "recommended_next_image": memory_update.get("recommended_next_image"),
        "selected_pages": turn.get("selected_pages") or [],
        "envelope": {
            "parsed_json": bool(turn.get("parsed_json")),
            "valid": bool(turn.get("envelope_valid")),
            "schema": turn.get("envelope_schema"),
            "fallback_used": bool(turn.get("envelope_fallback_used")),
            "validation_errors": turn.get("envelope_validation_errors") or [],
        },
        "raw_artifacts": {
            "raw_model_output_path": "raw_model_output.json",
            "final_model_output_path": "final_model_output.json",
            "selected_pages_path": "selected_pages.json",
            "session_excerpt_path": "session_excerpt.json",
        },
    }


def build_human_review_template(model_label: Dict[str, Any], upload_record: Dict[str, Any]) -> Dict[str, Any]:
    diagnosis = model_label.get("model_diagnosis") or {}
    return {
        "record_type": "human_review",
        "schema_version": "data_agent.human_review.v1",
        "review_id": stable_id("review", model_label["model_label_id"]),
        "instance_id": model_label["instance_id"],
        "model_label_id": model_label["model_label_id"],
        "created_at": now_utc(),
        "review_status": "draft",
        "reviewer": "",
        "reviewed_at": None,
        "decision": "needs_more_evidence",
        "human_reviewed_label": {
            "disease": None,
            "severity": None,
            "leaf_side": None,
            "evidence_sufficiency": "unknown",
            "confidence": "unknown",
            "notes": "",
        },
        "model_label_summary": {
            "model_diagnosis": diagnosis,
            "evidence_status": model_label.get("evidence_status"),
            "evidence_present": model_label.get("evidence_present") or [],
            "evidence_missing": model_label.get("evidence_missing") or [],
            "recommended_next_image": model_label.get("recommended_next_image"),
            "image_ids": model_label.get("image_ids") or [],
        },
        "upload_summary": [
            {
                "image_id": row.get("image_id"),
                "source_ref": row.get("source_ref"),
                "stored_path": row.get("stored_path"),
                "copy_status": row.get("copy_status"),
            }
            for row in upload_record.get("uploads", [])
        ],
        "corrections": {},
        "do_not_ingest_reason": None,
    }


def build_session_excerpt(session: Dict[str, Any], turn: Dict[str, Any]) -> Dict[str, Any]:
    user_message = message_for_turn(session, turn.get("user_turn_id"))
    assistant_message = message_for_turn(session, turn.get("assistant_turn_id"))
    return {
        "record_type": "session_excerpt",
        "schema_version": "data_agent.session_excerpt.v1",
        "session_id": session.get("session_id"),
        "user_message": user_message,
        "assistant_message": assistant_message,
        "turn": {
            key: value
            for key, value in turn.items()
            if key
            not in {
                "raw_model_output",
                "repair_model_output",
                "final_model_output",
            }
        },
    }


def build_model_output_artifact(field_name: str, turn: Dict[str, Any]) -> Dict[str, Any]:
    raw_text = turn.get(field_name)
    return {
        "record_type": "model_output_artifact",
        "schema_version": "data_agent.model_output_artifact.v1",
        "source_field": field_name,
        "raw_text": raw_text,
        "parsed_json": parse_json_object(raw_text),
    }


def build_manifest(
    *,
    data_root: Path,
    instance_id: str,
    session_path: Path,
    model_label: Dict[str, Any],
    upload_record: Dict[str, Any],
) -> Dict[str, Any]:
    instance_dir = data_root / "instances" / instance_id
    files = {
        "manifest": "manifest.json",
        "upload_record": "upload_record.json",
        "model_label": "model_label.json",
        "human_review_template": "human_review.template.json",
        "human_review_submitted": "human_review.submitted.json",
        "selected_pages": "selected_pages.json",
        "raw_model_output": "raw_model_output.json",
        "final_model_output": "final_model_output.json",
        "session_excerpt": "session_excerpt.json",
        "audit_events": "audit_events.jsonl",
    }
    return {
        "record_type": "data_agent_instance_manifest",
        "schema_version": "data_agent.instance_manifest.v1",
        "instance_id": instance_id,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "review_status": "unreviewed",
        "is_ground_truth": False,
        "source": model_label.get("source"),
        "session_path": root_relative(session_path),
        "instance_dir": root_relative(instance_dir),
        "image_ids": model_label.get("image_ids") or [],
        "model_label_id": model_label.get("model_label_id"),
        "review_id": stable_id("review", model_label["model_label_id"]),
        "files": files,
        "linked_files": {
            "uploads": [
                {
                    "image_id": row.get("image_id"),
                    "source_ref": row.get("source_ref"),
                    "stored_path": row.get("stored_path"),
                }
                for row in upload_record.get("uploads", [])
            ]
        },
        "boundary": {
            "llm_calls_created_by_data_agent": 0,
            "label_source": "machine_generated_unreviewed",
            "wiki_write_allowed": False,
            "human_review_required_for_ground_truth": True,
        },
    }


def preserve_existing_review_state(instance_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    existing_manifest_path = instance_dir / "manifest.json"
    if existing_manifest_path.exists():
        existing_manifest = read_json(existing_manifest_path)
        if isinstance(existing_manifest, dict) and existing_manifest.get("review_status") == "reviewed":
            manifest["review_status"] = "reviewed"
            manifest["is_ground_truth"] = bool(existing_manifest.get("is_ground_truth"))

    submitted_path = instance_dir / "human_review.submitted.json"
    if not submitted_path.exists():
        return manifest

    submitted = read_json(submitted_path)
    if not isinstance(submitted, dict):
        return manifest

    if submitted.get("review_status") == "reviewed":
        manifest["review_status"] = "reviewed"
        manifest["is_ground_truth"] = submitted.get("decision") in INGESTIBLE_REVIEW_DECISIONS
        manifest["files"]["human_review_submitted"] = "human_review.submitted.json"
    return manifest


def append_audit_event(instance_dir: Path, event: Dict[str, Any]) -> None:
    path = instance_dir / "audit_events.jsonl"
    rows = read_jsonl(path)
    event_id = event.get("event_id")
    if event_id and any(row.get("event_id") == event_id for row in rows):
        return
    rows.append(event)
    write_jsonl(path, rows)


def capture_turn(
    *,
    data_root: Path,
    session_path: Path,
    session: Dict[str, Any],
    turn: Dict[str, Any],
    copy_images: bool,
    rebuild_index: bool = True,
) -> Dict[str, Any]:
    ensure_layout(data_root)
    image_items = unique_image_items(session, turn)
    instance_id = stable_id(
        "inst",
        session.get("session_id"),
        turn.get("user_turn_id"),
        turn.get("assistant_turn_id"),
        [item.get("image_id") for item in image_items],
    )
    instance_dir = data_root / "instances" / instance_id
    instance_dir.mkdir(parents=True, exist_ok=True)

    upload_record = build_upload_record(
        data_root=data_root,
        instance_id=instance_id,
        session=session,
        turn=turn,
        image_items=image_items,
        copy_images=copy_images,
    )
    model_label = build_model_label(
        instance_id=instance_id,
        session_path=session_path,
        session=session,
        turn=turn,
        image_items=image_items,
    )
    review_template = build_human_review_template(model_label, upload_record)
    manifest = build_manifest(
        data_root=data_root,
        instance_id=instance_id,
        session_path=session_path,
        model_label=model_label,
        upload_record=upload_record,
    )
    manifest = preserve_existing_review_state(instance_dir, manifest)

    write_json(instance_dir / "upload_record.json", upload_record)
    write_json(instance_dir / "model_label.json", model_label)
    write_json(instance_dir / "human_review.template.json", review_template)
    write_json(instance_dir / "selected_pages.json", turn.get("selected_pages") or [])
    write_json(instance_dir / "raw_model_output.json", build_model_output_artifact("raw_model_output", turn))
    write_json(instance_dir / "final_model_output.json", build_model_output_artifact("final_model_output", turn))
    write_json(instance_dir / "session_excerpt.json", build_session_excerpt(session, turn))
    write_json(instance_dir / "manifest.json", manifest)
    append_audit_event(
        instance_dir,
        {
            "event_id": stable_id("event", "capture_turn", instance_id),
            "event_type": "capture_turn",
            "created_at": now_utc(),
            "instance_id": instance_id,
            "model_label_id": model_label["model_label_id"],
            "source_session_path": root_relative(session_path),
            "copy_images": copy_images,
        },
    )
    index_summary = rebuild_indexes(data_root) if rebuild_index else {"deferred": True}
    return {
        "instance_id": instance_id,
        "instance_dir": root_relative(instance_dir),
        "model_label_id": model_label["model_label_id"],
        "review_status": model_label["review_status"],
        "evidence_status": model_label["evidence_status"],
        "image_ids": model_label["image_ids"],
        "human_review_template": root_relative(instance_dir / "human_review.template.json"),
        "indexes": index_summary,
    }


def archive_sessions(
    *,
    data_root: Path,
    session_dir: Path,
    copy_images: bool = True,
    include_all_turns: bool = False,
) -> Dict[str, Any]:
    ensure_layout(data_root)
    archived: List[Dict[str, Any]] = []
    skipped_sessions: List[Dict[str, Any]] = []
    failed_turns: List[Dict[str, Any]] = []

    for session_path in iter_session_files(session_dir):
        try:
            session = load_session_file(session_path)
        except Exception as exc:
            skipped_sessions.append({"session_path": root_relative(session_path), "error": str(exc)})
            continue

        turns = archiveable_turns(session, include_all_turns=include_all_turns)
        if not turns:
            skipped_sessions.append(
                {
                    "session_path": root_relative(session_path),
                    "session_id": session.get("session_id"),
                    "reason": "no archiveable turns",
                }
            )
            continue

        for turn in turns:
            try:
                result = capture_turn(
                    data_root=data_root,
                    session_path=session_path,
                    session=session,
                    turn=turn,
                    copy_images=copy_images,
                    rebuild_index=False,
                )
            except Exception as exc:
                failed_turns.append(
                    {
                        "session_path": root_relative(session_path),
                        "session_id": session.get("session_id"),
                        "user_turn_id": turn.get("user_turn_id"),
                        "assistant_turn_id": turn.get("assistant_turn_id"),
                        "error": str(exc),
                    }
                )
                continue
            archived.append(
                {
                    "session_path": root_relative(session_path),
                    "session_id": session.get("session_id"),
                    "user_turn_id": turn.get("user_turn_id"),
                    "assistant_turn_id": turn.get("assistant_turn_id"),
                    "instance_id": result.get("instance_id"),
                    "instance_dir": result.get("instance_dir"),
                    "review_status": result.get("review_status"),
                    "evidence_status": result.get("evidence_status"),
                    "image_ids": result.get("image_ids") or [],
                }
            )

    indexes = rebuild_indexes(data_root)
    reviewed_index = build_reviewed_index(data_root)
    return {
        "archive_root": root_relative(data_root),
        "session_dir": root_relative(session_dir),
        "copy_images": copy_images,
        "include_all_turns": include_all_turns,
        "sessions_seen": len(iter_session_files(session_dir)),
        "turns_archived": len(archived),
        "archived": archived,
        "skipped_sessions": skipped_sessions,
        "failed_turns": failed_turns,
        "indexes": indexes,
        "reviewed_index": reviewed_index,
    }


def instance_dir_for(data_root: Path, instance_id: str) -> Path:
    return data_root / "instances" / safe_component(instance_id)


def load_instance_file(data_root: Path, instance_id: str, filename: str) -> Dict[str, Any]:
    path = instance_dir_for(data_root, instance_id) / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing instance file: {path}")
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"Instance file is not a JSON object: {path}")
    return value


def validate_review_for_import(review: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if review.get("record_type") != "human_review":
        errors.append("record_type must be human_review.")
    if review.get("review_status") != "reviewed":
        errors.append("review_status must be reviewed before import.")
    if not str(review.get("reviewer") or "").strip():
        errors.append("reviewer is required.")
    if not str(review.get("reviewed_at") or "").strip():
        errors.append("reviewed_at is required.")
    decision = review.get("decision")
    if decision not in REVIEW_DECISIONS:
        errors.append(f"decision must be one of {sorted(REVIEW_DECISIONS)}.")
    label = review.get("human_reviewed_label")
    if not isinstance(label, dict):
        errors.append("human_reviewed_label must be an object.")
    elif decision in INGESTIBLE_REVIEW_DECISIONS and not str(label.get("disease") or "").strip():
        errors.append("human_reviewed_label.disease is required for ingestible reviews.")
    return errors


def import_review(data_root: Path, instance_id: str | None, review_file: str | None) -> Dict[str, Any]:
    ensure_layout(data_root)
    review_path = normalize_path(review_file) if review_file else None
    if review_path is None:
        if not instance_id:
            raise ValueError("Provide --instance-id or --review-file.")
        review_path = instance_dir_for(data_root, instance_id) / "human_review.submitted.json"
    if not review_path.exists():
        raise FileNotFoundError(f"Review file not found: {review_path}")

    review = read_json(review_path)
    if not isinstance(review, dict):
        raise ValueError(f"Review file is not a JSON object: {review_path}")
    errors = validate_review_for_import(review)
    schema_result = validate_with_schema(review, "human_review.schema.json")
    if schema_result.get("valid") is False:
        errors.append(f"schema validation failed: {schema_result.get('error')}")
    if errors:
        return {"imported": False, "review_file": root_relative(review_path), "errors": errors}

    resolved_instance_id = str(review.get("instance_id") or instance_id)
    if not resolved_instance_id:
        raise ValueError("Review file does not include instance_id.")
    instance_dir = instance_dir_for(data_root, resolved_instance_id)
    if not instance_dir.exists():
        raise FileNotFoundError(f"Instance directory not found: {instance_dir}")

    submitted_path = instance_dir / "human_review.submitted.json"
    write_json(submitted_path, review)

    manifest = load_instance_file(data_root, resolved_instance_id, "manifest.json")
    manifest["updated_at"] = now_utc()
    manifest["review_status"] = "reviewed"
    manifest["is_ground_truth"] = review.get("decision") in INGESTIBLE_REVIEW_DECISIONS
    manifest["files"]["human_review_submitted"] = "human_review.submitted.json"
    write_json(instance_dir / "manifest.json", manifest)

    append_audit_event(
        instance_dir,
        {
            "event_id": stable_id("event", "import_review", review.get("review_id")),
            "event_type": "import_review",
            "created_at": now_utc(),
            "instance_id": resolved_instance_id,
            "review_id": review.get("review_id"),
            "decision": review.get("decision"),
            "is_ground_truth": manifest["is_ground_truth"],
        },
    )
    indexes = rebuild_indexes(data_root)
    reviewed_index = build_reviewed_index(data_root)
    return {
        "imported": True,
        "instance_id": resolved_instance_id,
        "review_id": review.get("review_id"),
        "decision": review.get("decision"),
        "is_ground_truth": manifest["is_ground_truth"],
        "submitted_review_path": root_relative(submitted_path),
        "indexes": indexes,
        "reviewed_index": reviewed_index,
    }


def iter_instance_dirs(data_root: Path) -> List[Path]:
    root = data_root / "instances"
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def pending_queue_row(instance_dir: Path, manifest: Dict[str, Any], model_label: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "record_type": "review_queue_item",
        "schema_version": "data_agent.review_queue_item.v1",
        "queue_status": "pending",
        "instance_id": manifest.get("instance_id"),
        "model_label_id": model_label.get("model_label_id"),
        "created_at": now_utc(),
        "instance_dir": root_relative(instance_dir),
        "human_review_template": root_relative(instance_dir / "human_review.template.json"),
        "evidence_status": model_label.get("evidence_status"),
        "image_ids": model_label.get("image_ids") or [],
        "model_diagnosis": model_label.get("model_diagnosis"),
    }


def completed_queue_row(instance_dir: Path, manifest: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "record_type": "review_queue_item",
        "schema_version": "data_agent.review_queue_item.v1",
        "queue_status": "completed",
        "instance_id": manifest.get("instance_id"),
        "model_label_id": manifest.get("model_label_id"),
        "review_id": review.get("review_id"),
        "reviewed_at": review.get("reviewed_at"),
        "decision": review.get("decision"),
        "is_ground_truth": review.get("decision") in INGESTIBLE_REVIEW_DECISIONS,
        "instance_dir": root_relative(instance_dir),
    }


def rebuild_indexes(data_root: Path) -> Dict[str, Any]:
    ensure_layout(data_root)
    uploads: List[Dict[str, Any]] = []
    labels: List[Dict[str, Any]] = []
    reviews: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    completed: List[Dict[str, Any]] = []

    for instance_dir in iter_instance_dirs(data_root):
        manifest_path = instance_dir / "manifest.json"
        model_label_path = instance_dir / "model_label.json"
        upload_record_path = instance_dir / "upload_record.json"
        if not manifest_path.exists() or not model_label_path.exists() or not upload_record_path.exists():
            continue
        manifest = read_json(manifest_path)
        model_label = read_json(model_label_path)
        upload_record = read_json(upload_record_path)
        if isinstance(upload_record, dict):
            uploads.extend(row for row in upload_record.get("uploads", []) if isinstance(row, dict))
        if isinstance(model_label, dict):
            labels.append(model_label)

        submitted_path = instance_dir / "human_review.submitted.json"
        if submitted_path.exists():
            review = read_json(submitted_path)
            if isinstance(review, dict):
                reviews.append(review)
                if review.get("review_status") == "reviewed":
                    completed.append(completed_queue_row(instance_dir, manifest, review))
                    continue
        pending.append(pending_queue_row(instance_dir, manifest, model_label))

    write_jsonl(data_root / "indexes" / "uploads.jsonl", uploads)
    write_jsonl(data_root / "indexes" / "model_labels.jsonl", labels)
    write_jsonl(data_root / "indexes" / "human_reviews.jsonl", reviews)
    write_jsonl(data_root / "review_queue" / "pending.jsonl", pending)
    write_jsonl(data_root / "review_queue" / "completed.jsonl", completed)
    return {
        "uploads": len(uploads),
        "model_labels": len(labels),
        "human_reviews": len(reviews),
        "pending_reviews": len(pending),
        "completed_reviews": len(completed),
    }


def reviewed_dataset_record(
    *,
    instance_dir: Path,
    manifest: Dict[str, Any],
    model_label: Dict[str, Any],
    review: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "record_type": "reviewed_dataset_record",
        "schema_version": "data_agent.reviewed_dataset_record.v1",
        "dataset_record_id": stable_id("ds", review.get("review_id")),
        "created_at": now_utc(),
        "instance_id": manifest.get("instance_id"),
        "instance_dir": root_relative(instance_dir),
        "model_label_id": model_label.get("model_label_id"),
        "review_id": review.get("review_id"),
        "source": model_label.get("source"),
        "image_ids": model_label.get("image_ids") or [],
        "image_links": manifest.get("linked_files", {}).get("uploads", []),
        "human_reviewed_label": review.get("human_reviewed_label"),
        "review_decision": review.get("decision"),
        "model_label_summary": review.get("model_label_summary") or {
            "model_diagnosis": model_label.get("model_diagnosis"),
            "evidence_status": model_label.get("evidence_status"),
        },
        "selected_pages": model_label.get("selected_pages") or [],
        "is_ground_truth": True,
        "wiki_ingestion_allowed": False,
    }


def build_reviewed_index(data_root: Path) -> Dict[str, Any]:
    ensure_layout(data_root)
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for instance_dir in iter_instance_dirs(data_root):
        submitted_path = instance_dir / "human_review.submitted.json"
        manifest_path = instance_dir / "manifest.json"
        model_label_path = instance_dir / "model_label.json"
        if not submitted_path.exists() or not manifest_path.exists() or not model_label_path.exists():
            continue
        review = read_json(submitted_path)
        if not isinstance(review, dict):
            continue
        if review.get("review_status") != "reviewed" or review.get("decision") not in INGESTIBLE_REVIEW_DECISIONS:
            skipped.append(
                {
                    "instance_id": review.get("instance_id"),
                    "review_id": review.get("review_id"),
                    "decision": review.get("decision"),
                    "reason": "not_ingestible_as_ground_truth",
                }
            )
            continue
        manifest = read_json(manifest_path)
        model_label = read_json(model_label_path)
        rows.append(reviewed_dataset_record(instance_dir=instance_dir, manifest=manifest, model_label=model_label, review=review))

    rows.sort(key=lambda row: str(row.get("dataset_record_id")))
    write_jsonl(data_root / "indexes" / "reviewed_dataset_index.jsonl", rows)
    return {"reviewed_dataset_records": len(rows), "skipped_reviews": skipped}


def list_pending(data_root: Path) -> Dict[str, Any]:
    rebuild_indexes(data_root)
    pending_path = data_root / "review_queue" / "pending.jsonl"
    return {"pending": read_jsonl(pending_path)}


def show_instance(data_root: Path, instance_id: str) -> Dict[str, Any]:
    instance_dir = instance_dir_for(data_root, instance_id)
    if not instance_dir.exists():
        raise FileNotFoundError(f"Instance directory not found: {instance_dir}")
    result: Dict[str, Any] = {"instance_dir": root_relative(instance_dir)}
    for name in ["manifest", "upload_record", "model_label", "human_review.template", "human_review.submitted"]:
        path = instance_dir / f"{name}.json"
        if path.exists():
            result[name.replace(".", "_")] = read_json(path)
    return result


def validate_instance(data_root: Path, instance_id: str) -> Dict[str, Any]:
    instance_dir = instance_dir_for(data_root, instance_id)
    checks = []
    targets = [
        ("manifest.json", "instance_manifest.schema.json"),
        ("upload_record.json", "upload_record.schema.json"),
        ("model_label.json", "model_label.schema.json"),
        ("human_review.template.json", "human_review.schema.json"),
        ("human_review.submitted.json", "human_review.schema.json"),
    ]
    for filename, schema_name in targets:
        path = instance_dir / filename
        if not path.exists():
            if filename == "human_review.submitted.json":
                continue
            checks.append({"file": filename, "valid": False, "error": "missing"})
            continue
        value = read_json(path)
        if not isinstance(value, dict):
            checks.append({"file": filename, "valid": False, "error": "not a JSON object"})
            continue
        result = validate_with_schema(value, schema_name)
        checks.append({"file": filename, **result})
    return {"instance_id": instance_id, "checks": checks, "valid": all(item.get("valid") is not False for item in checks)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic Session Archive for GopherEye session outputs.")
    parser.add_argument(
        "--archive-root",
        "--data-root",
        dest="archive_root",
        default=str(DEFAULT_ARCHIVE_ROOT),
        help="Runtime archive root directory. Defaults to the existing data_agent/ store.",
    )
    sub = parser.add_subparsers(dest="command")

    archive_all_parser = sub.add_parser(
        "archive-all",
        help="Archive every capture-worthy turn from every Frontier session, then rebuild indexes.",
    )
    archive_all_parser.add_argument("--session-dir", default=str(DEFAULT_FRONTIER_SESSION_DIR))
    archive_all_parser.add_argument(
        "--no-copy-images",
        action="store_true",
        help="Do not copy local image files into the archive image store.",
    )
    archive_all_parser.add_argument(
        "--include-all-turns",
        action="store_true",
        help="Archive non-visual turns too. By default only visual/image turns are archived.",
    )

    sub.add_parser("init", help="Create the session archive runtime directory layout.")

    capture = sub.add_parser("capture-turn", help="Capture one existing session turn as an unreviewed archive instance.")
    capture.add_argument("--session-path", default=None)
    capture.add_argument("--session-id", default=None)
    capture.add_argument("--session-dir", default=str(DEFAULT_FRONTIER_SESSION_DIR))
    capture.add_argument("--turn-id", type=int, default=None, help="User or assistant turn id. Defaults to latest visual turn.")
    capture.add_argument("--copy-images", action="store_true", help="Copy local image files into the archive image store.")

    import_parser = sub.add_parser("import-review", help="Import a human-edited review JSON into an instance.")
    import_parser.add_argument("--instance-id", default=None)
    import_parser.add_argument("--review-file", default=None)

    show_parser = sub.add_parser("show-instance", help="Print instance manifest, label, upload, and review data.")
    show_parser.add_argument("instance_id")

    validate_parser = sub.add_parser("validate-instance", help="Validate an instance against archive schemas.")
    validate_parser.add_argument("instance_id")

    sub.add_parser("list-pending", help="List model labels waiting for human review.")
    sub.add_parser("rebuild-indexes", help="Rebuild upload, label, review, and queue JSONL indexes.")
    sub.add_parser("build-reviewed-index", help="Build reviewed_dataset_index.jsonl from imported human reviews.")

    args = parser.parse_args()
    command = args.command or "archive-all"
    data_root = normalize_path(args.archive_root)

    try:
        if command == "archive-all":
            result = archive_sessions(
                data_root=data_root,
                session_dir=normalize_path(getattr(args, "session_dir", str(DEFAULT_FRONTIER_SESSION_DIR))),
                copy_images=not getattr(args, "no_copy_images", False),
                include_all_turns=getattr(args, "include_all_turns", False),
            )
        elif command == "init":
            paths = ensure_layout(data_root)
            result = {"data_root": root_relative(data_root), "created": {key: root_relative(path) for key, path in paths.items()}}
        elif command == "capture-turn":
            session_path, session = load_session_from_args(args.session_path, args.session_id, normalize_path(args.session_dir))
            turn = find_turn(session, args.turn_id)
            result = capture_turn(
                data_root=data_root,
                session_path=session_path,
                session=session,
                turn=turn,
                copy_images=args.copy_images,
            )
        elif command == "import-review":
            result = import_review(data_root, args.instance_id, args.review_file)
        elif command == "show-instance":
            result = show_instance(data_root, args.instance_id)
        elif command == "validate-instance":
            result = validate_instance(data_root, args.instance_id)
        elif command == "list-pending":
            result = list_pending(data_root)
        elif command == "rebuild-indexes":
            result = rebuild_indexes(data_root)
        elif command == "build-reviewed-index":
            result = build_reviewed_index(data_root)
        else:
            raise ValueError(f"Unknown command: {command}")
    except Exception as exc:
        safe_print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc

    safe_print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
