from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from src.single_model_wiki.core import (
    DEFAULT_CATALOG_DIR,
    DEFAULT_WIKI_DIR,
    ROOT_DIR,
    load_or_build_catalog,
    now_utc,
    read_all_pages,
    read_pages_by_id,
    run_model,
    run_model_with_images,
    safe_print,
    select_pages_keyword_fallback,
    select_pages_with_model,
    timestamp_id,
    trim_text,
    write_text,
)


DEFAULT_SESSION_DIR = ROOT_DIR / "sessions"


def default_memory() -> Dict[str, Any]:
    return {
        "summary": "",
        "user_goal": None,
        "current_diagnosis": None,
        "known_images": [],
        "visual_intakes": [],
        "evidence_present": [],
        "evidence_missing": [],
        "recommended_next_image": None,
        "allowed_follow_up_questions": [],
        "open_questions": [],
    }


def default_id_history() -> Dict[str, Any]:
    return {
        "images": {},
        "visual_intakes": {},
        "counters": {},
        "events": [],
    }


def create_session(session_id: str, provider: str, model: str) -> Dict[str, Any]:
    now = now_utc()
    return {
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "provider": provider,
        "model": model,
        "short_term_memory": default_memory(),
        "id_history": default_id_history(),
        "messages": [],
        "turns": [],
    }


def session_path(session_id: str, session_dir: Path = DEFAULT_SESSION_DIR) -> Path:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", session_id).strip("_")
    if not clean:
        raise ValueError("session_id cannot be empty")
    return session_dir / f"{clean}.json"


def load_session(
    session_id: str,
    *,
    session_dir: Path = DEFAULT_SESSION_DIR,
    provider: str,
    model: str,
) -> Dict[str, Any]:
    path = session_path(session_id, session_dir)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return create_session(session_id, provider, model)


def save_session(session: Dict[str, Any], *, session_dir: Path = DEFAULT_SESSION_DIR) -> Path:
    session["updated_at"] = now_utc()
    path = session_path(session["session_id"], session_dir)
    write_text(path, json.dumps(session, ensure_ascii=False, indent=2))
    return path


def parse_json_object(text: str) -> Dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    match = re.search(r"\{[\s\S]*\}", stripped)
    if match:
        stripped = match.group(0)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


MEMORY_UPDATE_CORE_KEYS = [
    "summary",
    "evidence_present",
    "evidence_missing",
    "recommended_next_image",
    "allowed_follow_up_questions",
    "open_questions",
]
MEMORY_UPDATE_LIST_KEYS = [
    "known_image_updates",
    "visual_intakes",
    "evidence_present",
    "evidence_missing",
    "allowed_follow_up_questions",
    "open_questions",
]
PROTECTED_MODEL_MEMORY_KEYS = {
    "session_id",
    "turn_id",
    "image_id",
    "image_path",
    "visual_intake_id",
    "created_at",
    "updated_at",
}
ASSISTANT_ENVELOPE_SCHEMA_NAME = "schemas/envelopes/assistant_envelope.schema.json"
BASE_KNOWN_IMAGE_UPDATE_SCHEMA_NAME = "schemas/base/known_image_update.schema.json"
BASE_VISUAL_INTAKE_SCHEMA_NAME = "schemas/visual_intake.schema.json"
ENVELOPE_SCHEMA_PROFILES: Dict[str, Dict[str, Any]] = {
    "chat": {
        "schema_name": ASSISTANT_ENVELOPE_SCHEMA_NAME,
        "role_profile": "chat",
        "requires_visual_memory": False,
        "payload_schemas": ["schemas/base/memory_update.schema.json"],
    },
    "frontier_visual_intake_or_diagnosis": {
        "schema_name": ASSISTANT_ENVELOPE_SCHEMA_NAME,
        "role_profile": "frontier_visual_intake_or_diagnosis",
        "requires_visual_memory": True,
        "requires_image_ordered_visual_intakes": True,
        "payload_schemas": [
            "schemas/base/memory_update.schema.json",
            BASE_VISUAL_INTAKE_SCHEMA_NAME,
        ],
    },
    "frontier_grape_leaf_chat": {
        "schema_name": ASSISTANT_ENVELOPE_SCHEMA_NAME,
        "role_profile": "frontier_grape_leaf_chat",
        "requires_visual_memory": False,
        "payload_schemas": ["schemas/base/memory_update.schema.json"],
    },
    "frontier_data_management": {
        "schema_name": ASSISTANT_ENVELOPE_SCHEMA_NAME,
        "role_profile": "frontier_data_management",
        "requires_visual_memory": False,
        "payload_schemas": ["schemas/base/memory_update.schema.json"],
        "forbidden_actions": ["write_wiki", "write_ground_truth"],
    },
    "frontier_knowledge_management": {
        "schema_name": ASSISTANT_ENVELOPE_SCHEMA_NAME,
        "role_profile": "frontier_knowledge_management",
        "requires_visual_memory": False,
        "payload_schemas": ["schemas/base/memory_update.schema.json"],
    },
    "frontier_general_project_chat": {
        "schema_name": ASSISTANT_ENVELOPE_SCHEMA_NAME,
        "role_profile": "frontier_general_project_chat",
        "requires_visual_memory": False,
        "payload_schemas": ["schemas/base/memory_update.schema.json"],
    },
}
_SCHEMA_CACHE: Dict[str, Dict[str, Any]] = {}


def envelope_schema_profile(role: str) -> Dict[str, Any]:
    return ENVELOPE_SCHEMA_PROFILES.get(role, ENVELOPE_SCHEMA_PROFILES["chat"])


def frontier_envelope_role(task_type: str) -> str:
    return f"frontier_{task_type}"


def find_protected_memory_keys(value: Any, *, path: str = "memory_update") -> List[str]:
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in PROTECTED_MODEL_MEMORY_KEYS:
                found.append(child_path)
            found.extend(find_protected_memory_keys(child, path=child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            found.extend(find_protected_memory_keys(child, path=f"{path}[{idx}]"))
    return found


def load_schema(schema_name: str) -> Dict[str, Any]:
    schema = _SCHEMA_CACHE.get(schema_name)
    if schema is not None:
        return schema
    schema_path = ROOT_DIR / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8", errors="replace"))
    _SCHEMA_CACHE[schema_name] = schema
    return schema


def format_jsonschema_path(path: Sequence[Any]) -> str:
    if not path:
        return ""
    text = ""
    for part in path:
        if isinstance(part, int):
            text += f"[{part}]"
        else:
            text += f".{part}" if text else str(part)
    return text


def validate_payload_schema(value: Any, schema_name: str, *, label: str) -> List[str]:
    try:
        import jsonschema
    except Exception:
        return []

    schema = load_schema(schema_name)
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path)):
        suffix = format_jsonschema_path(list(error.path))
        location = f"{label}.{suffix}" if suffix else label
        errors.append(f"{location} does not satisfy {schema_name}: {error.message}")
    return errors


QUALITY_OVERALL_SYNONYMS = {
    "excellent": "good",
    "clear": "good",
    "good": "good",
    "fair": "usable_with_caution",
    "usable": "usable_with_caution",
    "usable with caution": "usable_with_caution",
    "usable_with_caution": "usable_with_caution",
    "limited": "usable_with_caution",
    "poor": "usable_with_caution",
    "bad": "unusable",
    "unusable": "unusable",
}

QUALITY_ISSUES = {
    "blurry",
    "dark",
    "overexposed",
    "poor_angle",
    "occluded",
    "low_resolution",
    "duplicate",
}
STRUCTURES = {
    "blade",
    "lamina",
    "lobes",
    "serrated_margin",
    "petiole",
    "midrib",
    "primary_veins",
    "secondary_veins",
    "apex",
    "leaf_base",
    "adaxial_surface",
    "abaxial_surface",
}
SYMPTOMS = {
    "chlorosis",
    "necrosis",
    "powdery_growth",
    "downy_fuzzy_growth",
    "vein_bounded_spots",
    "edge_curling",
    "wilting",
    "healthy_uniform_green",
    "unknown_spots",
    "lesion",
    "water_soaked_area",
    "yellow_halo",
    "insect_damage",
    "gall",
}

SIDE_LABEL_SYNONYMS = {
    "upper": "adaxial",
    "upper side": "adaxial",
    "top": "adaxial",
    "top side": "adaxial",
    "front": "adaxial",
    "adaxial": "adaxial",
    "lower": "abaxial",
    "lower side": "abaxial",
    "underside": "abaxial",
    "under side": "abaxial",
    "back": "abaxial",
    "abaxial": "abaxial",
    "both": "mixed",
    "mixed": "mixed",
    "uncertain": "uncertain",
    "unknown": "uncertain",
    "not leaf": "not_leaf",
    "not_leaf": "not_leaf",
}

STRUCTURE_SYNONYMS = {
    "leaf blade": "blade",
    "blade": "blade",
    "lamina": "lamina",
    "lobe": "lobes",
    "lobes": "lobes",
    "lobed margin": "lobes",
    "serrated margin": "serrated_margin",
    "serrated_margin": "serrated_margin",
    "margin": "serrated_margin",
    "petiole": "petiole",
    "midrib": "midrib",
    "primary vein": "primary_veins",
    "primary veins": "primary_veins",
    "primary_veins": "primary_veins",
    "secondary vein": "secondary_veins",
    "secondary veins": "secondary_veins",
    "secondary_veins": "secondary_veins",
    "apex": "apex",
    "tip": "apex",
    "base": "leaf_base",
    "leaf base": "leaf_base",
    "leaf_base": "leaf_base",
    "adaxial surface": "adaxial_surface",
    "adaxial_surface": "adaxial_surface",
    "upper surface": "adaxial_surface",
    "abaxial surface": "abaxial_surface",
    "abaxial_surface": "abaxial_surface",
    "lower surface": "abaxial_surface",
    "underside": "abaxial_surface",
}


def _normalized_text(value: Any) -> str:
    text = str(value).strip().lower().replace("_", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _append_unique(items: List[str], value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text and text not in items:
        items.append(text)


def normalize_quality_overall(value: Any) -> str | None:
    if value is None:
        return None
    text = _normalized_text(value)
    if text in QUALITY_OVERALL_SYNONYMS:
        return QUALITY_OVERALL_SYNONYMS[text]
    if "unusable" in text:
        return "unusable"
    if any(token in text for token in ["fair", "limited", "usable", "partial", "caution"]):
        return "usable_with_caution"
    if any(token in text for token in ["good", "clear", "sharp", "excellent"]):
        return "good"
    return "usable_with_caution"


def normalize_side_label(value: Any) -> str | None:
    if value is None:
        return None
    text = _normalized_text(value)
    return SIDE_LABEL_SYNONYMS.get(text)


def canonical_quality_issues(value: Any) -> tuple[List[str], List[str]]:
    canonical: List[str] = []
    notes: List[str] = []
    for item in _as_list(value):
        raw = str(item).strip()
        text = _normalized_text(raw)
        found: List[str] = []
        if raw in QUALITY_ISSUES:
            found.append(raw)
        if any(token in text for token in ["blur", "out of focus", "not sharp"]):
            found.append("blurry")
        if any(token in text for token in ["dark", "shadow", "underexposed"]):
            found.append("dark")
        if any(token in text for token in ["glare", "bright", "overexposed", "sunlight", "washed", "dappled", "uneven lighting"]):
            found.append("overexposed")
        if any(token in text for token in ["angle", "tilted", "perspective"]):
            found.append("poor_angle")
        if any(token in text for token in ["occluded", "overlap", "covered", "blocked", "partial occlusion"]):
            found.append("occluded")
        if any(token in text for token in ["low resolution", "low detail", "limited detail", "close up", "closeup", "fine lesion detail"]):
            found.append("low_resolution")
        if "duplicate" in text:
            found.append("duplicate")
        for issue in found:
            _append_unique(canonical, issue)
        if raw and (not found or raw not in QUALITY_ISSUES):
            _append_unique(notes, raw)
    return canonical, notes


def canonical_structures(value: Any) -> tuple[List[str], List[str]]:
    canonical: List[str] = []
    notes: List[str] = []
    for item in _as_list(value):
        raw = str(item).strip()
        text = _normalized_text(raw)
        mapped = STRUCTURE_SYNONYMS.get(text)
        if mapped in STRUCTURES:
            _append_unique(canonical, mapped)
            if raw != mapped:
                _append_unique(notes, raw)
        else:
            _append_unique(notes, raw)
    return canonical, notes


def canonical_symptoms(value: Any) -> tuple[List[str], List[str]]:
    canonical: List[str] = []
    notes: List[str] = []
    for item in _as_list(value):
        raw = str(item).strip()
        text = _normalized_text(raw)
        found: List[str] = []
        if raw in SYMPTOMS:
            found.append(raw)
        if any(token in text for token in ["chlorosis", "chlorotic", "yellow", "pale", "mottling", "mottle", "discoloration"]):
            found.append("chlorosis")
        if any(token in text for token in ["necrosis", "necrotic", "brown", "blackened", "dead tissue"]):
            found.append("necrosis")
        if "powdery" in text:
            found.append("powdery_growth")
        if any(token in text for token in ["downy", "fuzzy", "fuzz", "sporulation"]):
            found.append("downy_fuzzy_growth")
        if any(token in text for token in ["vein bounded", "vein limited", "angular"]):
            found.append("vein_bounded_spots")
        if any(token in text for token in ["curl", "curled", "curling"]):
            found.append("edge_curling")
        if any(token in text for token in ["wilt", "wilting"]):
            found.append("wilting")
        if any(token in text for token in ["healthy", "uniform green", "no visible symptoms"]):
            found.append("healthy_uniform_green")
        if any(token in text for token in ["spot", "speck", "dot", "dark mark"]):
            found.append("unknown_spots")
        if any(token in text for token in ["lesion", "mark"]):
            found.append("lesion")
        if "water soaked" in text or "water-soaked" in str(item).lower():
            found.append("water_soaked_area")
        if "halo" in text:
            found.append("yellow_halo")
        if "insect" in text:
            found.append("insect_damage")
        if "gall" in text:
            found.append("gall")
        for symptom in found:
            _append_unique(canonical, symptom)
        if raw and (not found or raw not in SYMPTOMS):
            _append_unique(notes, raw)
    return canonical, notes


def normalize_visual_intake_payload(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    normalized = copy.deepcopy(item)

    image_quality = normalized.get("image_quality")
    if isinstance(image_quality, dict):
        overall = normalize_quality_overall(image_quality.get("overall"))
        if overall is not None:
            image_quality["overall"] = overall
        issues, notes = canonical_quality_issues(image_quality.get("issues"))
        existing_notes = [str(note) for note in _as_list(image_quality.get("quality_notes")) if str(note).strip()]
        image_quality["issues"] = issues
        if notes or existing_notes:
            image_quality["quality_notes"] = existing_notes + [note for note in notes if note not in existing_notes]

    side_assessment = normalized.get("side_assessment")
    if isinstance(side_assessment, dict):
        side_label = normalize_side_label(side_assessment.get("side_label"))
        if side_label is not None:
            side_assessment["side_label"] = side_label

    if "visible_structures" in normalized:
        structures, notes = canonical_structures(normalized.get("visible_structures"))
        existing_notes = [str(note) for note in _as_list(normalized.get("visible_structure_notes")) if str(note).strip()]
        normalized["visible_structures"] = structures
        if notes or existing_notes:
            normalized["visible_structure_notes"] = existing_notes + [note for note in notes if note not in existing_notes]

    if "visible_symptoms" in normalized:
        symptoms, notes = canonical_symptoms(normalized.get("visible_symptoms"))
        existing_notes = [str(note) for note in _as_list(normalized.get("visible_symptom_notes")) if str(note).strip()]
        normalized["visible_symptoms"] = symptoms
        if notes or existing_notes:
            normalized["visible_symptom_notes"] = existing_notes + [note for note in notes if note not in existing_notes]

    return normalized


def normalize_known_image_update_payload(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    normalized = copy.deepcopy(item)
    side_label = normalize_side_label(normalized.get("side_label"))
    if side_label is not None or normalized.get("side_label") is not None:
        normalized["side_label"] = side_label
    quality = normalize_quality_overall(normalized.get("quality_overall"))
    if quality is not None or normalized.get("quality_overall") is not None:
        normalized["quality_overall"] = quality
    return normalized


def normalize_assistant_envelope_payload(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = copy.deepcopy(value)
    # Routing and selected agent path are code-owned turn metadata, not model-owned memory.
    normalized.pop("agent_trace", None)
    memory_update = normalized.get("memory_update")
    if not isinstance(memory_update, dict):
        return normalized

    if isinstance(memory_update.get("known_image_updates"), list):
        memory_update["known_image_updates"] = [
            normalize_known_image_update_payload(item)
            for item in memory_update.get("known_image_updates", [])
        ]
    if isinstance(memory_update.get("visual_intakes"), list):
        memory_update["visual_intakes"] = [
            normalize_visual_intake_payload(item)
            for item in memory_update.get("visual_intakes", [])
        ]
    return normalized


def validate_base_payloads(memory_update: Dict[str, Any], profile: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    known_updates = memory_update.get("known_image_updates")
    if isinstance(known_updates, list):
        for idx, item in enumerate(known_updates):
            errors.extend(
                validate_payload_schema(
                    item,
                    BASE_KNOWN_IMAGE_UPDATE_SCHEMA_NAME,
                    label=f"memory_update.known_image_updates[{idx}]",
                )
            )

    visual_intakes = memory_update.get("visual_intakes")
    if isinstance(visual_intakes, list):
        for idx, item in enumerate(visual_intakes):
            if not isinstance(item, dict):
                errors.append(f"memory_update.visual_intakes[{idx}] must be an object.")
                continue
            if profile.get("requires_image_ordered_visual_intakes"):
                image_order = item.get("image_order")
                if not isinstance(image_order, int) or image_order < 1:
                    errors.append(
                        f"memory_update.visual_intakes[{idx}].image_order must be an integer >= 1."
                    )
            errors.extend(
                validate_payload_schema(
                    item,
                    BASE_VISUAL_INTAKE_SCHEMA_NAME,
                    label=f"memory_update.visual_intakes[{idx}]",
                )
            )

    return errors


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


def validate_assistant_envelope(
    value: Any,
    *,
    role: str = "chat",
    expected_task_type: str | None = None,
) -> List[str]:
    profile = envelope_schema_profile(role)
    errors = []
    if not isinstance(value, dict):
        return ["Envelope must be a JSON object."]

    assistant_message = value.get("assistant_message")
    if not isinstance(assistant_message, str) or not assistant_message.strip():
        errors.append("assistant_message must be a non-empty string.")
    elif contains_cjk(assistant_message):
        errors.append("assistant_message must be written in English only.")

    memory_update = value.get("memory_update")
    if not isinstance(memory_update, dict):
        errors.append("memory_update must be an object.")
        memory_update = {}

    for key in MEMORY_UPDATE_CORE_KEYS:
        if key not in memory_update:
            errors.append(f"memory_update.{key} is required.")

    if "summary" in memory_update and not isinstance(memory_update.get("summary"), str):
        errors.append("memory_update.summary must be a string.")
    if "recommended_next_image" in memory_update and not (
        memory_update.get("recommended_next_image") is None
        or isinstance(memory_update.get("recommended_next_image"), str)
    ):
        errors.append("memory_update.recommended_next_image must be a string or null.")
    for key in ["user_goal", "current_diagnosis"]:
        if key in memory_update and not (memory_update.get(key) is None or isinstance(memory_update.get(key), str)):
            errors.append(f"memory_update.{key} must be a string or null.")
    for key in MEMORY_UPDATE_LIST_KEYS:
        if key in memory_update and not isinstance(memory_update.get(key), list):
            errors.append(f"memory_update.{key} must be a list.")

    if profile.get("requires_visual_memory"):
        for key in ["known_image_updates", "visual_intakes"]:
            if key not in memory_update:
                errors.append(f"memory_update.{key} is required for visual diagnosis.")

    protected_keys = find_protected_memory_keys(memory_update)
    if protected_keys:
        preview = ", ".join(protected_keys[:6])
        errors.append(f"memory_update must not include code-owned ID/timestamp fields: {preview}.")

    errors.extend(validate_base_payloads(memory_update, profile))

    return errors


def build_envelope_repair_prompt(
    *,
    original_prompt: str,
    invalid_output: str,
    errors: Sequence[str],
    role: str,
    expected_task_type: str | None = None,
) -> str:
    profile = envelope_schema_profile(role)
    expected_task_text = expected_task_type or "(not required)"
    return f"""Your previous response did not satisfy the required GopherEye JSON envelope.

Return ONLY corrected JSON. Do not include markdown fences or explanation.

Required schema profile:
{profile['schema_name']}

Role profile:
{profile.get('role_profile', role)}

Payload schemas for this role:
{json.dumps(profile.get("payload_schemas", []), ensure_ascii=False, indent=2)}

Expected task_type:
{expected_task_text}

Validation errors:
{json.dumps(list(errors), ensure_ascii=False, indent=2)}

The corrected response must have:
- assistant_message: non-empty English natural language string for the user.
- memory_update: structured object for session memory.
- no agent_trace; route and selected agent path are code-owned turn metadata.
- no code-owned fields inside memory_update, including session_id, turn_id,
  image_id, image_path, visual_intake_id, created_at, or updated_at.

Original task prompt:
{trim_text(original_prompt, 6000)}

Invalid model output:
{trim_text(invalid_output, 4000)}

Return corrected JSON now:"""


def fallback_assistant_message(parsed: Dict[str, Any] | None, raw: str) -> str:
    if parsed and isinstance(parsed.get("assistant_message"), str) and parsed["assistant_message"].strip():
        candidate = parsed["assistant_message"].strip()
        if not contains_cjk(candidate):
            return candidate
    stripped = raw.strip()
    if (
        not stripped
        or contains_cjk(stripped)
        or stripped.startswith(("{", "[", "```"))
        or '"assistant_message"' in stripped
        or '"memory_update"' in stripped
        or "Return JSON" in stripped
    ):
        return (
            "I could not produce a valid structured response for this turn. "
            "Please try again, or upload a clearer image if this is a diagnosis request."
        )
    return trim_text(stripped, 1200).strip()


def minimal_memory_update_after_envelope_failure(previous: Dict[str, Any], errors: Sequence[str]) -> Dict[str, Any]:
    open_questions = list(previous.get("open_questions") or [])
    open_questions.append("Last model response failed JSON envelope validation.")
    return {
        "summary": previous.get("summary") or "Last model response failed JSON envelope validation.",
        "evidence_present": previous.get("evidence_present") or [],
        "evidence_missing": previous.get("evidence_missing") or [],
        "recommended_next_image": previous.get("recommended_next_image"),
        "allowed_follow_up_questions": previous.get("allowed_follow_up_questions") or [],
        "open_questions": open_questions[-12:],
        "validation_errors": list(errors)[:12],
    }


def resolve_assistant_envelope(
    raw: str,
    *,
    role: str,
    original_prompt: str,
    expected_task_type: str | None = None,
    repair_callback: Any | None = None,
) -> Dict[str, Any]:
    attempts = []
    parsed = parse_json_object(raw)
    normalized_parsed = normalize_assistant_envelope_payload(parsed)
    errors = validate_assistant_envelope(normalized_parsed, role=role, expected_task_type=expected_task_type)
    attempts.append(
        {
            "attempt": "initial",
            "raw": raw,
            "parsed_json": parsed is not None,
            "envelope_valid": not errors,
            "errors": errors,
        }
    )
    final_raw = raw
    final_parsed = normalized_parsed
    final_errors = errors

    if errors and repair_callback is not None:
        repair_prompt = build_envelope_repair_prompt(
            original_prompt=original_prompt,
            invalid_output=raw,
            errors=errors,
            role=role,
            expected_task_type=expected_task_type,
        )
        repair_raw = repair_callback(repair_prompt)
        repair_parsed = parse_json_object(repair_raw)
        normalized_repair_parsed = normalize_assistant_envelope_payload(repair_parsed)
        repair_errors = validate_assistant_envelope(
            normalized_repair_parsed,
            role=role,
            expected_task_type=expected_task_type,
        )
        attempts.append(
            {
                "attempt": "repair",
                "raw": repair_raw,
                "parsed_json": repair_parsed is not None,
                "envelope_valid": not repair_errors,
                "errors": repair_errors,
            }
        )
        final_raw = repair_raw
        final_parsed = normalized_repair_parsed
        final_errors = repair_errors

    envelope_valid = not final_errors
    if envelope_valid and final_parsed:
        final_normalized_raw = json.dumps(final_parsed, ensure_ascii=False, indent=2)
        return {
            "assistant_message": final_parsed["assistant_message"].strip(),
            "memory_update": final_parsed["memory_update"],
            "parsed_json": True,
            "envelope_valid": True,
            "fallback_used": False,
            "final_raw": final_normalized_raw,
            "final_parsed": final_parsed,
            "validation_errors": [],
            "attempts": attempts,
            "schema_profile": envelope_schema_profile(role)["schema_name"],
            "role_profile": envelope_schema_profile(role).get("role_profile", role),
        }

    return {
        "assistant_message": fallback_assistant_message(final_parsed, final_raw),
        "memory_update": None,
        "parsed_json": final_parsed is not None,
        "envelope_valid": False,
        "fallback_used": True,
        "final_raw": final_raw,
        "final_parsed": final_parsed,
        "validation_errors": final_errors,
        "attempts": attempts,
        "schema_profile": envelope_schema_profile(role)["schema_name"],
        "role_profile": envelope_schema_profile(role).get("role_profile", role),
    }


def ensure_id_history(session: Dict[str, Any]) -> Dict[str, Any]:
    history = session.get("id_history")
    if not isinstance(history, dict):
        history = default_id_history()
        session["id_history"] = history
    for key, default_value in default_id_history().items():
        if key not in history or not isinstance(history[key], type(default_value)):
            history[key] = default_value.copy() if isinstance(default_value, dict) else list(default_value)
    return history


def append_id_event(session: Dict[str, Any], event: Dict[str, Any]) -> None:
    history = ensure_id_history(session)
    events = history.setdefault("events", [])
    events.append({"created_at": now_utc(), **event})
    history["events"] = events[-500:]


def safe_id_component(value: str, *, max_len: int = 96) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_")
    clean = clean or "item"
    return clean[:max_len].strip("_") or "item"


def unique_id(base_id: str, used_ids: Sequence[str]) -> str:
    used = set(used_ids)
    if base_id not in used:
        return base_id
    suffix = 2
    while True:
        candidate = f"{base_id}_{suffix:02d}"
        if candidate not in used:
            return candidate
        suffix += 1


def get_or_create_image_id(
    session: Dict[str, Any],
    ref: str,
    *,
    turn_id: int | None = None,
) -> str:
    history = ensure_id_history(session)
    images = history.setdefault("images", {})
    ref = str(ref)

    for image_id, record in images.items():
        if isinstance(record, dict) and record.get("source_ref") == ref:
            record["last_seen_turn_id"] = turn_id
            record["updated_at"] = now_utc()
            return str(image_id)

    proposed_id = stable_image_id(ref)
    existing_record = images.get(proposed_id)
    if proposed_id in images and (
        not isinstance(existing_record, dict) or existing_record.get("source_ref") != ref
    ):
        proposed_id = unique_id(proposed_id, list(images.keys()))

    now = now_utc()
    images[proposed_id] = {
        "entity_type": "image",
        "source_ref": ref,
        "created_at": now,
        "updated_at": now,
        "first_seen_turn_id": turn_id,
        "last_seen_turn_id": turn_id,
        "source": "code_generated",
    }
    append_id_event(
        session,
        {
            "event": "created_id",
            "entity_type": "image",
            "entity_id": proposed_id,
            "source_ref": ref,
            "turn_id": turn_id,
        },
    )
    return proposed_id


def get_or_create_visual_intake_id(
    session: Dict[str, Any],
    image_id: str,
    *,
    turn_id: int | None = None,
) -> str:
    history = ensure_id_history(session)
    visual_intakes = history.setdefault("visual_intakes", {})
    image_id = str(image_id)

    for visual_intake_id, record in visual_intakes.items():
        if isinstance(record, dict) and record.get("image_id") == image_id:
            record["last_used_turn_id"] = turn_id
            record["updated_at"] = now_utc()
            return str(visual_intake_id)

    base_id = f"vi_{safe_id_component(image_id)}"
    visual_intake_id = unique_id(base_id, list(visual_intakes.keys()))
    now = now_utc()
    visual_intakes[visual_intake_id] = {
        "entity_type": "visual_intake",
        "image_id": image_id,
        "created_at": now,
        "updated_at": now,
        "first_used_turn_id": turn_id,
        "last_used_turn_id": turn_id,
        "source": "code_generated",
    }
    append_id_event(
        session,
        {
            "event": "created_id",
            "entity_type": "visual_intake",
            "entity_id": visual_intake_id,
            "image_id": image_id,
            "turn_id": turn_id,
        },
    )
    return visual_intake_id


def hydrate_id_history_from_session(session: Dict[str, Any]) -> None:
    history = ensure_id_history(session)
    memory = session.setdefault("short_term_memory", default_memory())

    for item in memory.get("known_images", []):
        normalized = normalize_known_image_item(item)
        if not normalized:
            continue
        image_id = normalized["image_id"]
        history["images"].setdefault(
            image_id,
            {
                "entity_type": "image",
                "source_ref": normalized["image_path"],
                "created_at": normalized.get("created_at") or now_utc(),
                "updated_at": normalized.get("updated_at") or now_utc(),
                "first_seen_turn_id": normalized.get("first_seen_turn_id"),
                "last_seen_turn_id": normalized.get("last_seen_turn_id"),
                "source": "hydrated_from_session",
            },
        )

    for item in memory.get("visual_intakes", []):
        if not isinstance(item, dict):
            continue
        image_id = item.get("image_id")
        if not image_id:
            continue
        visual_intake_id = item.get("visual_intake_id") or get_or_create_visual_intake_id(
            session,
            str(image_id),
        )
        item["visual_intake_id"] = str(visual_intake_id)
        history["visual_intakes"].setdefault(
            str(visual_intake_id),
            {
                "entity_type": "visual_intake",
                "image_id": str(image_id),
                "created_at": item.get("created_at") or now_utc(),
                "updated_at": item.get("updated_at") or now_utc(),
                "source": "hydrated_from_session",
            },
        )


def attached_image_maps(
    attached_image_manifest: Sequence[Dict[str, Any]],
) -> tuple[Dict[str, str], Dict[int, str]]:
    by_id: Dict[str, str] = {}
    by_order: Dict[int, str] = {}
    for item in attached_image_manifest:
        image_id = item.get("image_id")
        if image_id:
            by_id[str(image_id)] = str(image_id)
        try:
            order = int(item.get("image_order"))
        except (TypeError, ValueError):
            continue
        if image_id:
            by_order[order] = str(image_id)
    return by_id, by_order


def infer_image_id_from_model_item(
    item: Dict[str, Any],
    *,
    attached_image_manifest: Sequence[Dict[str, Any]],
    known_images: Sequence[Dict[str, Any]],
) -> str | None:
    attached_by_id, attached_by_order = attached_image_maps(attached_image_manifest)
    known_ids = {str(image["image_id"]) for image in known_images if image.get("image_id")}

    image_id = item.get("image_id")
    if image_id and (str(image_id) in attached_by_id or str(image_id) in known_ids):
        return str(image_id)

    image_order = item.get("image_order") or item.get("image_index")
    try:
        order = int(image_order)
    except (TypeError, ValueError):
        order = None
    if order is not None and order in attached_by_order:
        return attached_by_order[order]

    if len(attached_by_order) == 1:
        return next(iter(attached_by_order.values()))
    return None


def apply_known_image_updates(
    known_images: Sequence[Dict[str, Any]],
    model_updates: Any,
    *,
    attached_image_manifest: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_id = {str(item["image_id"]): dict(item) for item in known_images if item.get("image_id")}
    updates = model_updates if isinstance(model_updates, list) else []
    for update in updates:
        if not isinstance(update, dict):
            continue
        image_id = infer_image_id_from_model_item(
            update,
            attached_image_manifest=attached_image_manifest,
            known_images=list(by_id.values()),
        )
        if not image_id or image_id not in by_id:
            continue
        for field in ["side_label", "quality_overall"]:
            if update.get(field) is not None:
                by_id[image_id][field] = str(update[field])
        by_id[image_id]["updated_at"] = now_utc()
    return list(by_id.values())


def normalize_visual_intakes(
    previous: Any,
    incoming: Any,
    *,
    session: Dict[str, Any],
    attached_image_manifest: Sequence[Dict[str, Any]],
    known_images: Sequence[Dict[str, Any]],
    turn_id: int | None,
    max_items: int = 24,
) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    previous_items = previous if isinstance(previous, list) else []
    for item in previous_items:
        if not isinstance(item, dict):
            continue
        image_id = item.get("image_id")
        if not image_id:
            continue
        visual_intake_id = get_or_create_visual_intake_id(session, str(image_id), turn_id=turn_id)
        merged[visual_intake_id] = {**item, "visual_intake_id": visual_intake_id, "image_id": str(image_id)}

    allowed_fields = {
        "is_leaf_image",
        "image_quality",
        "side_assessment",
        "visible_symptoms",
        "visible_symptom_notes",
        "visible_structures",
        "visible_structure_notes",
        "symptom_locations",
        "candidate_diseases",
        "intake_summary",
    }
    incoming_items = incoming if isinstance(incoming, list) else []
    for item in incoming_items:
        if not isinstance(item, dict):
            continue
        image_id = infer_image_id_from_model_item(
            item,
            attached_image_manifest=attached_image_manifest,
            known_images=known_images,
        )
        if not image_id:
            continue
        visual_intake_id = get_or_create_visual_intake_id(session, image_id, turn_id=turn_id)
        old = merged.get(visual_intake_id, {})
        sanitized = {key: item[key] for key in allowed_fields if key in item}
        now = now_utc()
        merged[visual_intake_id] = {
            **old,
            **sanitized,
            "visual_intake_id": visual_intake_id,
            "image_id": image_id,
            "created_at": old.get("created_at") or now,
            "updated_at": now,
            "source": "model_memory_update",
        }

    return list(merged.values())[-max_items:]


def normalize_memory(
    value: Any,
    previous: Dict[str, Any],
    *,
    session: Dict[str, Any],
    attached_image_manifest: Sequence[Dict[str, Any]] = (),
    turn_id: int | None = None,
) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return previous
    memory = default_memory()
    for key in ["summary", "user_goal", "current_diagnosis", "recommended_next_image"]:
        memory[key] = value[key] if key in value else previous.get(key)
    for key in ["evidence_present", "evidence_missing", "allowed_follow_up_questions", "open_questions"]:
        memory[key] = value[key] if key in value else previous.get(key, [])

    code_known_images = merge_known_images(previous.get("known_images", []), [])
    memory["known_images"] = apply_known_image_updates(
        code_known_images,
        value.get("known_image_updates") or value.get("known_images"),
        attached_image_manifest=attached_image_manifest,
    )
    memory["visual_intakes"] = normalize_visual_intakes(
        previous.get("visual_intakes", []),
        value.get("visual_intakes", []),
        session=session,
        attached_image_manifest=attached_image_manifest,
        known_images=memory["known_images"],
        turn_id=turn_id,
        max_items=24,
    )

    for list_key in ["evidence_present", "evidence_missing", "allowed_follow_up_questions", "open_questions"]:
        if not isinstance(memory[list_key], list):
            memory[list_key] = []
        memory[list_key] = [str(item) for item in memory[list_key]][:12]
    for text_key in ["summary", "user_goal", "current_diagnosis", "recommended_next_image"]:
        if memory[text_key] is not None and not isinstance(memory[text_key], str):
            memory[text_key] = str(memory[text_key])
    return memory


def stable_image_id(ref: str) -> str:
    stem = Path(ref).stem if not ref.startswith(("http://", "https://", "data:", "file://")) else "image"
    clean_stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_") or "image"
    digest = hashlib.sha1(ref.encode("utf-8", errors="replace")).hexdigest()[:10]
    return f"img_{clean_stem}_{digest}"


def normalize_known_image_item(item: Any) -> Dict[str, Any] | None:
    if isinstance(item, str):
        return {
            "image_id": stable_image_id(item),
            "image_path": item,
            "image_role": "user_upload",
        }
    if not isinstance(item, dict):
        return None
    image_path = item.get("image_path") or item.get("path") or item.get("uri")
    image_id = item.get("image_id")
    if not image_path and not image_id:
        return None
    image_path = str(image_path or image_id)
    image_id = str(image_id or stable_image_id(image_path))
    out = dict(item)
    out["image_id"] = image_id
    out["image_path"] = image_path
    out.setdefault("image_role", "user_upload")
    return out


def merge_known_images(previous: Any, incoming: Any, max_items: int = 24) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for seq in [previous if isinstance(previous, list) else [], incoming if isinstance(incoming, list) else []]:
        for item in seq:
            normalized = normalize_known_image_item(item)
            if not normalized:
                continue
            key = normalized["image_id"]
            old = merged.pop(key, {})
            combined = {**old, **normalized}
            if old.get("first_seen_turn_id") is not None:
                combined["first_seen_turn_id"] = old["first_seen_turn_id"]
            if old.get("created_at") is not None:
                combined["created_at"] = old["created_at"]
            merged[key] = combined
    return list(merged.values())[-max_items:]


def merge_records_by_id(previous: Any, incoming: Any, *, id_key: str, max_items: int) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for seq in [previous if isinstance(previous, list) else [], incoming if isinstance(incoming, list) else []]:
        for item in seq:
            if not isinstance(item, dict):
                continue
            record_id = item.get(id_key)
            if not record_id:
                image_id = item.get("image_id", "unknown_image")
                record_id = f"{id_key}_{image_id}_{len(merged) + 1}"
                item = {**item, id_key: record_id}
            key = str(record_id)
            old = merged.get(key, {})
            merged[key] = {**old, **item}
    return list(merged.values())[-max_items:]


def register_image_refs(
    session: Dict[str, Any],
    image_refs: Sequence[str],
    *,
    turn_id: int,
) -> List[Dict[str, Any]]:
    if not image_refs:
        return []
    memory = session.setdefault("short_term_memory", default_memory())
    existing = memory.get("known_images", [])
    incoming = []
    for ref in image_refs:
        image_id = get_or_create_image_id(session, ref, turn_id=turn_id)
        incoming.append(
            {
                "image_id": image_id,
                "image_path": ref,
                "image_role": "user_upload",
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "first_seen_turn_id": turn_id,
                "last_seen_turn_id": turn_id,
            }
        )
    memory["known_images"] = merge_known_images(existing, incoming)
    return incoming


def is_external_image_ref(ref: str) -> bool:
    return ref.startswith(("http://", "https://", "data:", "file://"))


def resolve_local_image_ref(ref: str, *, session_dir: Path, session_id: str) -> str | None:
    if is_external_image_ref(ref):
        return ref

    raw = Path(ref).expanduser()
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend(
            [
                Path.cwd() / raw,
                ROOT_DIR / raw,
                session_dir / session_id / "images" / raw,
            ]
        )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve().as_uri()
    return None


def image_path_from_known_image(item: Any) -> str | None:
    normalized = normalize_known_image_item(item)
    if not normalized:
        return None
    return str(normalized.get("image_path") or "")


def collect_image_records_for_context(
    session: Dict[str, Any],
    current_image_refs: Sequence[str],
    *,
    image_context: str,
    max_attached_images: int,
) -> List[Dict[str, Any]]:
    if image_context == "none":
        return []
    records: List[Dict[str, Any]] = []
    known_by_path: Dict[str, Dict[str, Any]] = {}
    for item in session.get("short_term_memory", {}).get("known_images", []):
        normalized = normalize_known_image_item(item)
        if normalized:
            known_by_path[str(normalized["image_path"])] = normalized
    if image_context == "current":
        for ref in current_image_refs:
            normalized = known_by_path.get(str(ref)) or normalize_known_image_item(str(ref))
            if normalized:
                records.append(normalized)
    if image_context == "session":
        for item in session.get("short_term_memory", {}).get("known_images", []):
            normalized = normalize_known_image_item(item)
            if normalized:
                records.append(normalized)

    merged: Dict[str, Dict[str, Any]] = {}
    for record in records:
        key = str(record["image_id"])
        old = merged.pop(key, {})
        merged[key] = {**old, **record}

    deduped = list(merged.values())
    if max_attached_images > 0:
        deduped = deduped[-max_attached_images:]
    return deduped


def resolve_vlm_image_refs(
    records: Sequence[Dict[str, Any]],
    *,
    session_dir: Path,
    session_id: str,
) -> tuple[List[str], List[str], List[Dict[str, Any]]]:
    resolved = []
    missing = []
    attached = []
    for idx, record in enumerate(records, start=1):
        ref = image_path_from_known_image(record)
        if not ref:
            continue
        uri = resolve_local_image_ref(ref, session_dir=session_dir, session_id=session_id)
        if uri:
            resolved.append(uri)
            attached.append(
                {
                    "image_order": idx,
                    "image_id": record.get("image_id") or stable_image_id(ref),
                    "image_path": ref,
                    "image_uri": uri,
                    "image_role": record.get("image_role", "user_upload"),
                    "first_seen_turn_id": record.get("first_seen_turn_id"),
                    "last_seen_turn_id": record.get("last_seen_turn_id"),
                }
            )
        else:
            missing.append(ref)
    return resolved, missing, attached


def recent_messages(
    session: Dict[str, Any],
    limit: int,
    *,
    exclude_last: bool = False,
) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []
    messages = session.get("messages", [])
    if exclude_last:
        messages = messages[:-1]
    return messages[-limit:]


def render_recent_messages(messages: Sequence[Dict[str, Any]]) -> str:
    if not messages:
        return "(no previous messages)"
    lines = []
    for msg in messages:
        image_refs = msg.get("image_refs") or []
        suffix = f" image_refs={image_refs}" if image_refs else ""
        lines.append(f"{msg['role'].upper()}[{msg['turn_id']}]{suffix}: {msg['content']}")
    return "\n".join(lines)


def render_pages(pages: Sequence[Dict[str, Any]]) -> str:
    if not pages:
        return "(no wiki pages selected)"
    blocks = []
    for page in pages:
        blocks.append(
            f"""[PAGE id={page['id']} path={page['path']} title={page['title']}]
{page['text']}
[/PAGE]"""
        )
    return "\n\n".join(blocks)


def build_selection_query(session: Dict[str, Any], user_message: str) -> str:
    memory = session.get("short_term_memory", {})
    parts = [
        user_message,
        memory.get("summary") or "",
        memory.get("current_diagnosis") or "",
        " ".join(memory.get("evidence_present") or []),
        " ".join(memory.get("evidence_missing") or []),
    ]
    return "\n".join(part for part in parts if part)


def select_pages(
    *,
    session: Dict[str, Any],
    user_message: str,
    selection_mode: str,
    provider: str,
    model: str,
    max_selected_files: int,
    max_page_chars: int,
    wiki_dir: Path,
    catalog_dir: Path,
) -> List[Dict[str, Any]]:
    catalog = load_or_build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)
    query = build_selection_query(session, user_message)

    if selection_mode == "none":
        selected_ids: List[str] = []
    elif selection_mode == "full":
        return read_all_pages(catalog=catalog, wiki_dir=wiki_dir, max_page_chars=max_page_chars)
    elif selection_mode == "keyword":
        selected_ids = select_pages_keyword_fallback(
            query,
            catalog=catalog,
            max_selected_files=max_selected_files,
        )
    elif selection_mode == "model":
        selected_ids = select_pages_with_model(
            query,
            catalog=catalog,
            provider=provider,
            model=model,
            max_selected_files=max_selected_files,
        )
        if not selected_ids:
            selected_ids = select_pages_keyword_fallback(
                query,
                catalog=catalog,
                max_selected_files=max_selected_files,
            )
    else:
        raise ValueError(f"Unsupported selection_mode: {selection_mode}")

    return read_pages_by_id(
        selected_ids,
        catalog=catalog,
        wiki_dir=wiki_dir,
        max_page_chars=max_page_chars,
    )


def build_chat_prompt(
    *,
    session: Dict[str, Any],
    user_message: str,
    image_refs: Sequence[str],
    pages: Sequence[Dict[str, Any]],
    recent_turns: int,
    attached_image_manifest: Sequence[Dict[str, Any]],
    missing_image_refs: Sequence[str],
) -> str:
    current_turn = {
        "role": "user",
        "content": user_message,
        "image_refs": list(image_refs),
    }
    return f"""You are GopherEye's controlled diagnostic wiki chatbot.

You must return ONLY valid JSON with this exact top-level shape:
{{
  "assistant_message": "short professional English answer to the user",
  "memory_update": {{
    "summary": "compact memory of the session so far",
    "user_goal": null,
    "current_diagnosis": null,
    "known_image_updates": [
      {{
        "image_order": 1,
        "side_label": null,
        "quality_overall": null
      }}
    ],
    "visual_intakes": [
      {{
        "image_order": 1,
        "is_leaf_image": true,
        "image_quality": {{"overall": "good", "issues": [], "quality_notes": []}},
        "side_assessment": {{"side_label": "uncertain", "confidence": 0.0}},
        "visible_symptoms": [],
        "visible_symptom_notes": [],
        "visible_structures": [],
        "visible_structure_notes": [],
        "symptom_locations": [],
        "candidate_diseases": [],
        "intake_summary": "short visual evidence summary"
      }}
    ],
    "evidence_present": [],
    "evidence_missing": [],
    "recommended_next_image": null,
    "allowed_follow_up_questions": [],
    "open_questions": []
  }}
}}

Use only:
1. short-term memory,
2. recent transcript,
3. attached image pixels and attached image manifest,
4. selected wiki pages,
5. current user message.

Rules:
- Keep the assistant_message short, professional, and app-appropriate.
- Write assistant_message in English only.
- Do not invent visual evidence that is not in memory, transcript, or current message.
- If evidence is incomplete, keep uncertainty visible.
- If another image is needed, name the exact next image.
- If images are attached to this model call, inspect those image pixels and update
  known_image_updates and visual_intakes in memory_update.
- If no image pixels are attached, rely only on existing visual_intakes and text.
- Preserve important facts in memory_update.
- Drop irrelevant small talk from memory_update.
- Stay within grape leaf diagnosis and GopherEye project knowledge.
- Do not recommend treatment unless a reviewed management page is included.
- Do not create or modify session_id, turn_id, image_id, image_path,
  visual_intake_id, created_at, or updated_at fields.
- For image-specific updates, use only image_order from the attached image
  manifest. The app code will map image_order to image_id and assign stable IDs.
- Do not output agent_trace. Route and selected agent path are app-owned metadata.
- Use canonical values when obvious, and put natural-language botanical detail in
  quality_notes, visible_symptom_notes, visible_structure_notes, evidence_present,
  evidence_missing, or intake_summary.

Current short-term memory JSON:
{json.dumps(session.get("short_term_memory", default_memory()), ensure_ascii=False, indent=2)}

Recent transcript, last {recent_turns} messages:
{render_recent_messages(recent_messages(session, recent_turns, exclude_last=True))}

Attached image manifest for this model call:
{json.dumps(list(attached_image_manifest), ensure_ascii=False, indent=2)}

The actual image pixels are attached to the VLM in the same order as this
manifest. When updating visual_intakes, use the matching image_order.

Image refs that were requested but could not be loaded:
{json.dumps(list(missing_image_refs), ensure_ascii=False, indent=2)}

Selected wiki pages:
{render_pages(pages)}

Current user message JSON:
{json.dumps(current_turn, ensure_ascii=False, indent=2)}

Return JSON now:"""


def run_chat_turn(
    user_message: str,
    *,
    session_id: str,
    provider: str,
    model: str,
    selection_mode: str = "model",
    image_refs: Sequence[str] = (),
    max_selected_files: int = 6,
    max_page_chars: int = 12000,
    recent_turns: int = 8,
    max_new_tokens: int = 900,
    image_context: str = "session",
    max_attached_images: int = 8,
    session_dir: Path = DEFAULT_SESSION_DIR,
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> Dict[str, Any]:
    session = load_session(session_id, session_dir=session_dir, provider=provider, model=model)
    session["provider"] = provider
    session["model"] = model
    hydrate_id_history_from_session(session)

    user_turn_id = len(session.get("messages", [])) + 1
    user_row = {
        "turn_id": user_turn_id,
        "role": "user",
        "content": user_message,
        "created_at": now_utc(),
        "image_refs": list(image_refs),
    }
    session.setdefault("messages", []).append(user_row)
    register_image_refs(session, image_refs, turn_id=user_turn_id)

    pages = select_pages(
        session=session,
        user_message=user_message,
        selection_mode=selection_mode,
        provider=provider,
        model=model,
        max_selected_files=max_selected_files,
        max_page_chars=max_page_chars,
        wiki_dir=wiki_dir,
        catalog_dir=catalog_dir,
    )
    requested_image_records = collect_image_records_for_context(
        session,
        image_refs,
        image_context=image_context,
        max_attached_images=max_attached_images,
    )
    attached_image_refs, missing_image_refs, attached_image_manifest = resolve_vlm_image_refs(
        requested_image_records,
        session_dir=session_dir,
        session_id=session_id,
    )

    prompt = build_chat_prompt(
        session=session,
        user_message=user_message,
        image_refs=image_refs,
        pages=pages,
        recent_turns=recent_turns,
        attached_image_manifest=attached_image_manifest,
        missing_image_refs=missing_image_refs,
    )
    raw = run_model_with_images(
        prompt,
        provider=provider,
        model=model,
        image_refs=attached_image_refs,
        max_new_tokens=max_new_tokens,
    )
    envelope = resolve_assistant_envelope(
        raw,
        role="chat",
        original_prompt=prompt,
        repair_callback=lambda repair_prompt: run_model_with_images(
            repair_prompt,
            provider=provider,
            model=model,
            image_refs=attached_image_refs,
            max_new_tokens=max_new_tokens,
        ),
    )
    assistant_message = envelope["assistant_message"]
    previous_memory = session.get("short_term_memory", default_memory())
    memory_update = envelope["memory_update"]
    if not envelope["envelope_valid"]:
        memory_update = minimal_memory_update_after_envelope_failure(
            previous_memory,
            envelope["validation_errors"],
        )
    session["short_term_memory"] = normalize_memory(
        memory_update,
        previous_memory,
        session=session,
        attached_image_manifest=attached_image_manifest,
        turn_id=user_turn_id,
    )

    assistant_turn_id = len(session.get("messages", [])) + 1
    assistant_row = {
        "turn_id": assistant_turn_id,
        "role": "assistant",
        "content": assistant_message,
        "created_at": now_utc(),
    }
    session["messages"].append(assistant_row)
    turn_meta = {
        "user_turn_id": user_turn_id,
        "assistant_turn_id": assistant_turn_id,
        "provider": provider,
        "model": model,
        "selection_mode": selection_mode,
        "image_context": image_context,
        "max_attached_images": max_attached_images,
        "requested_image_records": requested_image_records,
        "attached_image_refs": attached_image_refs,
        "attached_image_manifest": attached_image_manifest,
        "missing_image_refs": missing_image_refs,
        "selected_pages": [
            {"id": page["id"], "path": page["path"], "title": page["title"]}
            for page in pages
        ],
        "raw_model_output": raw,
        "repair_model_output": envelope["attempts"][1]["raw"] if len(envelope["attempts"]) > 1 else None,
        "final_model_output": envelope["final_raw"],
        "parsed_json": envelope["parsed_json"],
        "envelope_valid": envelope["envelope_valid"],
        "envelope_schema": envelope["schema_profile"],
        "envelope_role_profile": envelope["role_profile"],
        "envelope_validation_errors": envelope["validation_errors"],
        "envelope_fallback_used": envelope["fallback_used"],
        "envelope_attempts": [
            {key: value for key, value in attempt.items() if key != "raw"}
            for attempt in envelope["attempts"]
        ],
        "created_at": now_utc(),
    }
    session.setdefault("turns", []).append(turn_meta)
    path = save_session(session, session_dir=session_dir)

    return {
        "session_path": str(path),
        "session_id": session_id,
        "assistant_message": assistant_message,
        "short_term_memory": session["short_term_memory"],
        "id_history": session.get("id_history", default_id_history()),
        "selected_pages": turn_meta["selected_pages"],
        "attached_image_refs": attached_image_refs,
        "attached_image_manifest": attached_image_manifest,
        "missing_image_refs": missing_image_refs,
        "parsed_json": envelope["parsed_json"],
        "envelope_valid": envelope["envelope_valid"],
        "envelope_schema": envelope["schema_profile"],
        "envelope_role_profile": envelope["role_profile"],
        "envelope_validation_errors": envelope["validation_errors"],
        "envelope_fallback_used": envelope["fallback_used"],
    }


def list_sessions(session_dir: Path = DEFAULT_SESSION_DIR) -> List[Path]:
    if not session_dir.exists():
        return []
    return sorted(session_dir.glob("*.json"))


def print_chat_result(result: Dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        safe_print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    safe_print(result["assistant_message"])
    safe_print("")
    safe_print(f"session_id: {result['session_id']}")
    safe_print(f"session_path: {result['session_path']}")
    safe_print("attached_image_refs:")
    for image_ref in result.get("attached_image_refs", []):
        safe_print(f"- {image_ref}")
    if result.get("attached_image_manifest"):
        safe_print("attached_image_manifest:")
        safe_print(json.dumps(result["attached_image_manifest"], ensure_ascii=False, indent=2))
    if result.get("missing_image_refs"):
        safe_print("missing_image_refs:")
        for image_ref in result.get("missing_image_refs", []):
            safe_print(f"- {image_ref}")
    safe_print("selected_pages:")
    for page in result.get("selected_pages", []):
        safe_print(f"- {page['path']}")
    safe_print("short_term_memory:")
    safe_print(json.dumps(result["short_term_memory"], ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a multi-turn GopherEye wiki chat session.")
    parser.add_argument("message", nargs="?", help="User message for this turn.")
    parser.add_argument("--session-id", default=None, help="Reuse this ID to continue a session.")
    parser.add_argument("--provider", choices=["transformers", "openai", "qwen-vl", "transformers-vl", "echo"], default="transformers")
    parser.add_argument("--model", default=None)
    parser.add_argument("--selection-mode", choices=["model", "full", "keyword", "none"], default="model")
    parser.add_argument("--image-ref", action="append", default=[], help="Optional image ID/path to remember in the turn.")
    parser.add_argument(
        "--image-context",
        choices=["session", "current", "none"],
        default="session",
        help="Which images should be loaded and attached to VLM calls: current turn only, full session, or none.",
    )
    parser.add_argument(
        "--max-attached-images",
        type=int,
        default=8,
        help="Maximum number of session images to attach to a VLM call. Use 0 for no limit.",
    )
    parser.add_argument("--max-selected-files", type=int, default=6)
    parser.add_argument("--max-page-chars", type=int, default=12000)
    parser.add_argument("--recent-turns", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=900)
    parser.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list-sessions", action="store_true")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if args.list_sessions:
        for path in list_sessions(session_dir):
            safe_print(str(path))
        return

    if not args.message:
        raise SystemExit("Provide a message, or use --list-sessions.")

    session_id = args.session_id or f"session_{timestamp_id()}"
    model = args.model or os.getenv("OPENAI_MODEL")
    if not model:
        model = "Qwen/Qwen2.5-VL-7B-Instruct" if args.provider in {"qwen-vl", "transformers-vl"} else "Qwen/Qwen2.5-7B-Instruct"
    result = run_chat_turn(
        args.message,
        session_id=session_id,
        provider=args.provider,
        model=model,
        selection_mode=args.selection_mode,
        image_refs=args.image_ref,
        max_selected_files=args.max_selected_files,
        max_page_chars=args.max_page_chars,
        recent_turns=args.recent_turns,
        max_new_tokens=args.max_new_tokens,
        image_context=args.image_context,
        max_attached_images=args.max_attached_images,
        session_dir=session_dir,
    )
    print_chat_result(result, as_json=args.json)


if __name__ == "__main__":
    main()
