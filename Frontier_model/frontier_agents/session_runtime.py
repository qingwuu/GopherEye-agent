from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from src.single_model_wiki.core import (
    ROOT_DIR,
    now_utc,
    trim_text,
    write_text,
)
from src.gophereye_runtime.utils import parse_json_object


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
        "evidence_sufficiency": "uncertain",
        "single_surface_assessment": None,
        "nonblocking_image_limitations": [],
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
    "nonblocking_image_limitations",
    "allowed_follow_up_questions",
    "open_questions",
]
PROTECTED_MODEL_MEMORY_KEYS = {
    "session_id",
    "turn_id",
    "image_id",
    "image_path",
    "image_uri",
    "image_role",
    "visual_intake_id",
    "created_at",
    "updated_at",
    "first_seen_turn_id",
    "last_seen_turn_id",
    "source",
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
DIAGNOSTIC_IMPACTS = {
    "none",
    "minor_nonblocking",
    "blocks_symptom_inspection",
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
    "oil_spots",
    "angular_vein_limited_lesions",
    "white_gray_powdery_colonies",
    "webby_mycelium",
    "white_cottony_sporulation",
    "dark_chasmothecia",
    "sparse_sporulation",
    "vein_tracking",
    "superficial_surface_growth",
    "metallic_sheen",
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
EVIDENCE_SUFFICIENCY_VALUES = {
    "sufficient",
    "sufficient_single_surface",
    "sufficient_both_surfaces",
    "sufficient_with_nonblocking_limitations",
    "insufficient_need_adaxial",
    "insufficient_need_abaxial",
    "insufficient_need_opposite_surface",
    "insufficient_need_better_quality",
    "uncertain",
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
        found: List[str] = []
        mapped = STRUCTURE_SYNONYMS.get(text)
        if mapped in STRUCTURES:
            found.append(mapped)
        else:
            if "blade" in text or "leaf blade" in text:
                found.append("blade")
            if "lamina" in text:
                found.append("lamina")
            if "lobe" in text:
                found.append("lobes")
            if "serrated" in text or "margin" in text or "edge" in text:
                found.append("serrated_margin")
            if "petiole" in text:
                found.append("petiole")
            if "midrib" in text:
                found.append("midrib")
            if "primary vein" in text or "major vein" in text or "radiating vein" in text:
                found.append("primary_veins")
            if "secondary vein" in text:
                found.append("secondary_veins")
            if "apex" in text or "tip" in text:
                found.append("apex")
            if "base" in text:
                found.append("leaf_base")
            if "adaxial" in text or "upper surface" in text or "top surface" in text:
                found.append("adaxial_surface")
            if "abaxial" in text or "underside" in text or "lower surface" in text:
                found.append("abaxial_surface")
        for structure in found:
            _append_unique(canonical, structure)
        if raw and (not found or raw not in STRUCTURES):
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
        if "oil spot" in text or "oily spot" in text or "greasy lesion" in text or "greasy spot" in text:
            found.append("oil_spots")
        if any(token in text for token in ["angular", "vein limited", "vein-limited", "vein bounded", "vein-bounded"]):
            found.append("angular_vein_limited_lesions")
        if "powdery" in text:
            found.append("powdery_growth")
            if any(token in text for token in ["white", "gray", "grey", "colony", "colonies", "dusty", "floury"]):
                found.append("white_gray_powdery_colonies")
        if any(token in text for token in ["webby", "mycelium", "mycelial"]):
            found.append("webby_mycelium")
        if any(token in text for token in ["downy", "fuzzy", "fuzz", "sporulation"]):
            found.append("downy_fuzzy_growth")
        if any(token in text for token in ["cottony", "white down", "white fuzz", "white sporulation"]):
            found.append("white_cottony_sporulation")
        if any(token in text for token in ["chasmothecia", "cleistothecia", "black speck", "dark speck", "orange speck"]):
            found.append("dark_chasmothecia")
        if "sparse sporulation" in text or "patchy sporulation" in text:
            found.append("sparse_sporulation")
        if "vein tracking" in text:
            found.append("vein_tracking")
        if any(token in text for token in ["superficial", "surface growth", "surface colony"]):
            found.append("superficial_surface_growth")
        if "metallic sheen" in text:
            found.append("metallic_sheen")
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


def normalize_diagnostic_impact(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if raw in DIAGNOSTIC_IMPACTS:
        return raw
    text = _normalized_text(raw)
    if not text or text in {"none", "no impact", "not applicable"}:
        return "none"
    if any(token in text for token in ["block", "prevent", "cannot inspect", "unusable", "not visible"]):
        return "blocks_symptom_inspection"
    return "minor_nonblocking"


def normalize_fine_visual_features(value: Any, *, default_surface: str = "uncertain") -> List[Dict[str, str]]:
    features: List[Dict[str, str]] = []
    for item in _as_list(value):
        if isinstance(item, dict):
            feature = str(item.get("feature") or item.get("description") or "").strip()
            if not feature:
                continue
            surface = normalize_side_label(item.get("surface")) or default_surface
            features.append(
                {
                    "feature": feature,
                    "surface": surface,
                    "location": str(item.get("location") or "uncertain").strip() or "uncertain",
                    "diagnostic_relevance": str(item.get("diagnostic_relevance") or "unknown").strip() or "unknown",
                }
            )
        elif item is not None:
            text = str(item).strip()
            if text:
                features.append(
                    {
                        "feature": text,
                        "surface": default_surface,
                        "location": "uncertain",
                        "diagnostic_relevance": "unknown",
                    }
                )
    return features


def normalize_candidate_diseases(value: Any) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for item in _as_list(value):
        if isinstance(item, dict):
            disease = str(item.get("disease") or item.get("label") or "").strip()
            if not disease:
                continue
            confidence = str(item.get("confidence") or "unknown").strip()
            if confidence not in {"low", "moderate", "high", "very_high", "unknown"}:
                confidence = "unknown"
            supporting_evidence = item.get("supporting_evidence")
            candidates.append(
                {
                    "disease": disease,
                    "confidence": confidence,
                    "supporting_evidence": [str(evidence) for evidence in _as_list(supporting_evidence) if str(evidence).strip()],
                }
            )
        elif item is not None:
            disease = str(item).strip()
            if disease:
                candidates.append(
                    {
                        "disease": disease,
                        "confidence": "unknown",
                        "supporting_evidence": [],
                    }
                )
    return candidates


def normalize_evidence_sufficiency(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if raw in EVIDENCE_SUFFICIENCY_VALUES:
        return raw
    text = _normalized_text(raw)
    if "sufficient" in text and "single" in text:
        return "sufficient_single_surface"
    if "sufficient" in text and "both" in text:
        return "sufficient_both_surfaces"
    if "sufficient" in text and any(token in text for token in ["limitation", "nonblocking", "caution"]):
        return "sufficient_with_nonblocking_limitations"
    if text == "sufficient":
        return "sufficient"
    if "adaxial" in text or "upper" in text or "front" in text:
        return "insufficient_need_adaxial"
    if "abaxial" in text or "underside" in text or "back" in text or "lower" in text:
        return "insufficient_need_abaxial"
    if "quality" in text or "clearer" in text or "blur" in text:
        return "insufficient_need_better_quality"
    if "insufficient" in text or "opposite" in text:
        return "insufficient_need_opposite_surface"
    return "uncertain"


def _string_list(value: Any, *, max_items: int = 6) -> List[str]:
    items: List[str] = []
    for item in _as_list(value):
        if item is None:
            continue
        text = str(item).strip()
        if text and text not in items:
            items.append(text)
        if len(items) >= max_items:
            break
    return items


def _coerce_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 1 else None


def _coerce_confidence(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number > 1 and number <= 100:
        number = number / 100
    return max(0.0, min(1.0, number))


def normalize_recommended_next_image(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    text = _normalized_text(raw)
    if text in {"none", "no", "no next image", "not needed", "not required", "null"}:
        return None
    if any(token in text for token in ["close", "closer", "sharp", "quality", "glare", "same surface"]):
        return "close_up_symptomatic_area"
    if "opposite" in text:
        return "opposite_surface_same_leaf"
    if "adaxial" in text or "upper" in text or "front" in text:
        return "adaxial_surface"
    if "abaxial" in text or "underside" in text or "lower" in text or "back" in text:
        return "abaxial_surface"
    return raw


def _default_diagnostic_impact(quality_overall: str, quality_issues: Sequence[str]) -> str:
    if quality_overall == "unusable":
        return "blocks_symptom_inspection"
    if quality_issues:
        return "minor_nonblocking"
    return "none"


def _candidate_diseases_from_observation(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "candidate_diseases" in item:
        return normalize_candidate_diseases(item.get("candidate_diseases"))[:3]

    labels = (
        item.get("candidate_labels")
        or item.get("candidate_disease_labels")
        or item.get("candidates")
    )
    default_confidence = str(item.get("candidate_confidence") or "unknown").strip()
    if default_confidence not in {"low", "moderate", "high", "very_high", "unknown"}:
        default_confidence = "unknown"
    supporting_evidence = _string_list(
        item.get("candidate_supporting_evidence") or item.get("supporting_evidence"),
        max_items=3,
    )

    candidates: List[Dict[str, Any]] = []
    for label in _as_list(labels):
        if isinstance(label, dict):
            candidates.extend(normalize_candidate_diseases(label))
            continue
        disease = str(label).strip()
        if not disease:
            continue
        candidates.append(
            {
                "disease": disease,
                "confidence": default_confidence,
                "supporting_evidence": supporting_evidence,
            }
        )
        if len(candidates) >= 3:
            break
    return candidates[:3]


def _collect_text(value: Any) -> List[str]:
    collected: List[str] = []
    if value is None:
        return collected
    if isinstance(value, dict):
        for child in value.values():
            collected.extend(_collect_text(child))
        return collected
    if isinstance(value, list):
        for child in value:
            collected.extend(_collect_text(child))
        return collected
    text = str(value).strip()
    if text:
        collected.append(text)
    return collected


def _observation_findings(item: Dict[str, Any]) -> List[str]:
    for key in ["findings", "finding_notes", "observation_notes", "visual_findings"]:
        if key in item:
            return _string_list(_collect_text(item.get(key)), max_items=5)

    fallback: List[str] = []
    for key in [
        "visible_structure_notes",
        "structure_notes",
        "visible_symptom_notes",
        "symptom_notes",
        "fine_visual_features",
        "feature_notes",
        "features",
    ]:
        fallback.extend(_collect_text(item.get(key)))
    return _string_list(fallback, max_items=5)


def _positive_observation_findings(findings: Sequence[str]) -> List[str]:
    positive: List[str] = []
    negation_markers = [
        " no ",
        " not ",
        " without ",
        " absence ",
        " absent ",
        " missing ",
        " lacks ",
        " lack ",
        " not visible",
        " not resolved",
        " cannot be resolved",
        " is not resolved",
        " are not resolved",
    ]
    for finding in findings:
        text = f" {_normalized_text(finding)} "
        if any(marker in text for marker in negation_markers):
            continue
        _append_unique(positive, finding)
    return positive


def _visual_intake_from_observation(item: Dict[str, Any], *, fallback_order: int) -> tuple[Dict[str, Any], Dict[str, Any]]:
    image_quality = item.get("image_quality") if isinstance(item.get("image_quality"), dict) else {}
    side_assessment = item.get("side_assessment") if isinstance(item.get("side_assessment"), dict) else {}
    findings = _observation_findings(item)
    positive_findings = _positive_observation_findings(findings)

    image_order = (
        _coerce_int(item.get("image_order"))
        or _coerce_int(item.get("image_index"))
        or _coerce_int(item.get("order"))
        or fallback_order
    )
    side_label = (
        normalize_side_label(item.get("side_label"))
        or normalize_side_label(item.get("side"))
        or normalize_side_label(item.get("visible_surface"))
        or normalize_side_label(side_assessment.get("side_label"))
        or "uncertain"
    )
    side_confidence = _coerce_confidence(
        item.get("side_confidence")
        or item.get("surface_confidence")
        or side_assessment.get("confidence"),
        default=0.0 if side_label == "uncertain" else 0.6,
    )
    quality_overall = (
        normalize_quality_overall(item.get("quality_overall"))
        or normalize_quality_overall(item.get("quality"))
        or normalize_quality_overall(image_quality.get("overall"))
        or "usable_with_caution"
    )
    quality_issues, issue_notes = canonical_quality_issues(
        item.get("quality_issues")
        if "quality_issues" in item
        else image_quality.get("issues")
    )
    quality_notes = _string_list(
        item.get("quality_notes")
        or image_quality.get("quality_notes")
        or item.get("limitations"),
        max_items=3,
    )
    for note in issue_notes:
        _append_unique(quality_notes, note)

    diagnostic_impact = (
        normalize_diagnostic_impact(item.get("diagnostic_impact"))
        or normalize_diagnostic_impact(image_quality.get("diagnostic_impact"))
        or _default_diagnostic_impact(quality_overall, quality_issues)
    )
    is_leaf_image = item.get("is_leaf_image")
    if not isinstance(is_leaf_image, bool):
        is_leaf_image = side_label != "not_leaf"

    feature_source = (
        item.get("fine_visual_features")
        if "fine_visual_features" in item
        else item.get("feature_notes") or item.get("features") or findings
    )
    visible_symptom_source = item.get("visible_symptoms") or item.get("symptoms") or positive_findings
    visible_structure_source = item.get("visible_structures") or item.get("structures") or findings
    symptom_notes = _string_list(
        item.get("visible_symptom_notes") or item.get("symptom_notes") or findings,
        max_items=4,
    )
    structure_notes = _string_list(
        item.get("visible_structure_notes") or item.get("structure_notes") or findings,
        max_items=4,
    )

    visual_intake = {
        "image_order": image_order,
        "is_leaf_image": is_leaf_image,
        "image_quality": {
            "overall": quality_overall,
            "issues": quality_issues,
            "diagnostic_impact": diagnostic_impact,
            "quality_notes": quality_notes[:4],
        },
        "side_assessment": {
            "side_label": side_label,
            "confidence": side_confidence,
        },
        "visible_symptoms": _string_list(visible_symptom_source, max_items=8),
        "visible_symptom_notes": symptom_notes,
        "visible_structures": _string_list(visible_structure_source, max_items=8),
        "visible_structure_notes": structure_notes,
        "symptom_locations": _string_list(
            item.get("symptom_locations") or item.get("locations"),
            max_items=5,
        ),
        "fine_visual_features": normalize_fine_visual_features(
            feature_source,
            default_surface=side_label,
        )[:4],
        "candidate_diseases": _candidate_diseases_from_observation(item),
        "intake_summary": str(item.get("intake_summary") or item.get("summary") or "").strip()
        or "Visual observation recorded.",
    }
    visual_intake = normalize_visual_intake_payload(visual_intake)
    known_image_update = {
        "image_order": image_order,
        "side_label": side_label,
        "quality_overall": quality_overall,
    }
    return known_image_update, visual_intake


def _first_surface_from_intakes(visual_intakes: Sequence[Dict[str, Any]]) -> str | None:
    for item in visual_intakes:
        if not isinstance(item, dict):
            continue
        side_assessment = item.get("side_assessment")
        side = normalize_side_label((side_assessment or {}).get("side_label")) if isinstance(side_assessment, dict) else None
        if side and side not in {"uncertain", "mixed", "not_leaf"}:
            return side
    return None


def _derive_evidence_sufficiency(
    *,
    explicit_value: Any,
    recommended_next_image: str | None,
    visual_intakes: Sequence[Dict[str, Any]],
    diagnosis_verdict: Any,
) -> str:
    normalized = normalize_evidence_sufficiency(explicit_value)
    if normalized:
        return normalized
    if recommended_next_image == "close_up_symptomatic_area":
        return "insufficient_need_better_quality"
    if recommended_next_image == "opposite_surface_same_leaf":
        return "insufficient_need_opposite_surface"
    if recommended_next_image == "adaxial_surface":
        return "insufficient_need_adaxial"
    if recommended_next_image == "abaxial_surface":
        return "insufficient_need_abaxial"

    text = _normalized_text(diagnosis_verdict)
    if any(token in text for token in ["confirmed", "sufficient", "diagnostic"]):
        return "sufficient_single_surface"
    if any(token in text for token in ["possible", "not confirmed", "uncertain", "insufficient"]):
        return "uncertain"

    has_nonblocking_limitations = any(
        isinstance(item, dict)
        and isinstance(item.get("image_quality"), dict)
        and item["image_quality"].get("diagnostic_impact") == "minor_nonblocking"
        for item in visual_intakes
    )
    if visual_intakes and recommended_next_image is None and has_nonblocking_limitations:
        return "sufficient_with_nonblocking_limitations"
    if visual_intakes and recommended_next_image is None:
        return "uncertain"
    return "uncertain"


def _derive_single_surface_assessment(
    *,
    explicit_value: Any,
    recommended_next_image: str | None,
    visual_intakes: Sequence[Dict[str, Any]],
    evidence_sufficiency: str,
) -> Dict[str, Any] | None:
    if isinstance(explicit_value, dict):
        return explicit_value
    if explicit_value is not None:
        return {"note": str(explicit_value)}

    surface = _first_surface_from_intakes(visual_intakes)
    if not surface:
        return None

    if recommended_next_image == "opposite_surface_same_leaf":
        decision = "needs_opposite_surface"
        opposite_role = "needed_for_specific_uncertainty"
        rationale = "The visible surface does not resolve the remaining diagnostic uncertainty."
    elif recommended_next_image in {"adaxial_surface", "abaxial_surface"}:
        decision = "needs_specific_surface"
        opposite_role = "needed_for_specific_uncertainty"
        rationale = "A specific surface is needed to resolve the remaining diagnostic uncertainty."
    elif recommended_next_image == "close_up_symptomatic_area":
        decision = "nondiagnostic"
        opposite_role = "not_needed_yet"
        rationale = "The main uncertainty is unresolved detail on the visible symptomatic surface."
    elif evidence_sufficiency.startswith("sufficient"):
        decision = "diagnostic_single_surface"
        opposite_role = "not_needed"
        rationale = "The visible surface provides enough diagnostic evidence for the current conservative assessment."
    else:
        decision = "nondiagnostic"
        opposite_role = "not_needed_yet"
        rationale = "The visible surface is not yet diagnostic enough for a confirmed assessment."

    return {
        "visible_surface": surface,
        "single_surface_decision": decision,
        "opposite_surface_role": opposite_role,
        "rationale": rationale,
    }


def expand_compact_memory_update(memory_update: Dict[str, Any]) -> Dict[str, Any]:
    """Expand model semantic shortcuts into the persisted memory_update shape."""
    normalized = copy.deepcopy(memory_update)

    observations = None
    for key in ["image_observations", "visual_observations", "image_deltas", "visual_delta"]:
        if key in normalized:
            observations = normalized.pop(key)
            break
    observation_items = observations if isinstance(observations, list) else _as_list(observations)

    generated_known_updates: List[Dict[str, Any]] = []
    generated_visual_intakes: List[Dict[str, Any]] = []
    for idx, item in enumerate(observation_items, start=1):
        if not isinstance(item, dict):
            continue
        known_update, visual_intake = _visual_intake_from_observation(item, fallback_order=idx)
        generated_known_updates.append(known_update)
        generated_visual_intakes.append(visual_intake)

    if generated_known_updates and (
        not isinstance(normalized.get("known_image_updates"), list)
        or not normalized.get("known_image_updates")
    ):
        normalized["known_image_updates"] = generated_known_updates
    if generated_visual_intakes and (
        not isinstance(normalized.get("visual_intakes"), list)
        or not normalized.get("visual_intakes")
    ):
        normalized["visual_intakes"] = generated_visual_intakes

    if "present_evidence" in normalized and "evidence_present" not in normalized:
        normalized["evidence_present"] = normalized.pop("present_evidence")
    if "missing_evidence" in normalized and "evidence_missing" not in normalized:
        normalized["evidence_missing"] = normalized.pop("missing_evidence")
    if "uncertainties" in normalized and "open_questions" not in normalized:
        normalized["open_questions"] = normalized.pop("uncertainties")
    if "nonblocking_limitations" in normalized and "nonblocking_image_limitations" not in normalized:
        normalized["nonblocking_image_limitations"] = normalized.pop("nonblocking_limitations")
    if "image_limitations" in normalized and "nonblocking_image_limitations" not in normalized:
        normalized["nonblocking_image_limitations"] = normalized.pop("image_limitations")

    next_image_need = normalized.pop("next_image_need", None)
    if "recommended_next_image" in normalized:
        normalized["recommended_next_image"] = normalize_recommended_next_image(
            normalized.get("recommended_next_image")
        )
    else:
        normalized["recommended_next_image"] = normalize_recommended_next_image(next_image_need)

    diagnosis_verdict = normalized.pop("diagnosis_verdict", None)
    visual_intakes = normalized.get("visual_intakes") if isinstance(normalized.get("visual_intakes"), list) else []
    evidence_sufficiency = _derive_evidence_sufficiency(
        explicit_value=normalized.get("evidence_sufficiency"),
        recommended_next_image=normalized.get("recommended_next_image"),
        visual_intakes=visual_intakes,
        diagnosis_verdict=diagnosis_verdict,
    )
    normalized["evidence_sufficiency"] = evidence_sufficiency
    normalized["single_surface_assessment"] = _derive_single_surface_assessment(
        explicit_value=normalized.get("single_surface_assessment"),
        recommended_next_image=normalized.get("recommended_next_image"),
        visual_intakes=visual_intakes,
        evidence_sufficiency=evidence_sufficiency,
    )

    normalized.setdefault("summary", "")
    normalized.setdefault("user_goal", None)
    normalized.setdefault("current_diagnosis", None)
    normalized.setdefault("evidence_present", [])
    normalized.setdefault("evidence_missing", [])
    normalized.setdefault("nonblocking_image_limitations", [])
    normalized.setdefault("allowed_follow_up_questions", [])
    normalized.setdefault("open_questions", [])

    for key in [
        "evidence_present",
        "evidence_missing",
        "nonblocking_image_limitations",
        "allowed_follow_up_questions",
        "open_questions",
    ]:
        normalized[key] = _string_list(normalized.get(key), max_items=8 if key != "open_questions" else 5)

    return normalized


def normalize_visual_intake_payload(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    normalized = copy.deepcopy(item)

    image_quality = normalized.get("image_quality")
    if isinstance(image_quality, dict):
        overall = normalize_quality_overall(image_quality.get("overall"))
        if overall is not None:
            image_quality["overall"] = overall
        diagnostic_impact = normalize_diagnostic_impact(image_quality.get("diagnostic_impact"))
        if diagnostic_impact is not None:
            image_quality["diagnostic_impact"] = diagnostic_impact
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
    default_surface = (
        normalize_side_label((side_assessment or {}).get("side_label"))
        if isinstance(side_assessment, dict)
        else None
    ) or "uncertain"

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

    if "fine_visual_features" in normalized:
        normalized["fine_visual_features"] = normalize_fine_visual_features(
            normalized.get("fine_visual_features"),
            default_surface=default_surface,
        )

    if "candidate_diseases" in normalized:
        normalized["candidate_diseases"] = normalize_candidate_diseases(normalized.get("candidate_diseases"))

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
    if not isinstance(memory_update, dict) and isinstance(normalized.get("memory_delta"), dict):
        memory_update = normalized.pop("memory_delta")
        normalized["memory_update"] = memory_update
    if not isinstance(memory_update, dict):
        return normalized
    normalized.pop("memory_delta", None)
    memory_update = expand_compact_memory_update(memory_update)
    normalized["memory_update"] = memory_update

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
    if "evidence_sufficiency" in memory_update:
        memory_update["evidence_sufficiency"] = normalize_evidence_sufficiency(
            memory_update.get("evidence_sufficiency")
        )
    if isinstance(memory_update.get("single_surface_assessment"), str):
        memory_update["single_surface_assessment"] = {
            "note": memory_update["single_surface_assessment"]
        }
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
    for key in ["user_goal", "current_diagnosis", "evidence_sufficiency"]:
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
- memory_update: compact structured object for session memory.
- for visual/image turns, use memory_update.image_observations[] only for
  per-image fields such as image_order, side_label, quality_overall,
  quality_issues, findings, candidate_labels, candidate_confidence,
  candidate_supporting_evidence, and intake_summary.
- findings should be 1-3 natural-language sentences combining structures,
  symptoms, locations, and diagnostic texture. Do not split findings into
  visible_symptoms, visible_structures, symptom_locations, symptom_notes,
  structure_notes, or feature_notes.
- put evidence_present, evidence_missing, next_image_need, and open_questions
  at the memory_update top level.
- do not output full known_image_updates, visual_intakes, image_quality objects,
  side_assessment objects, fine_visual_features objects, candidate_diseases
  objects, evidence_sufficiency, single_surface_assessment, or
  recommended_next_image. App code expands compact observations into the schema.
- no agent_trace; route and selected agent path are code-owned turn metadata.
- no code-owned fields inside memory_update, including session_id, turn_id,
  image_id, image_path, image_uri, image_role, visual_intake_id, created_at,
  updated_at, first_seen_turn_id, last_seen_turn_id, or source.

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
        "fine_visual_features",
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
    for key in [
        "summary",
        "user_goal",
        "current_diagnosis",
        "evidence_sufficiency",
        "single_surface_assessment",
        "recommended_next_image",
    ]:
        memory[key] = value[key] if key in value else previous.get(key, memory.get(key))
    for key in [
        "evidence_present",
        "evidence_missing",
        "nonblocking_image_limitations",
        "allowed_follow_up_questions",
        "open_questions",
    ]:
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

    for list_key in [
        "evidence_present",
        "evidence_missing",
        "nonblocking_image_limitations",
        "allowed_follow_up_questions",
        "open_questions",
    ]:
        if not isinstance(memory[list_key], list):
            memory[list_key] = []
        memory[list_key] = [str(item) for item in memory[list_key]][:12]
    for text_key in ["summary", "user_goal", "current_diagnosis", "evidence_sufficiency", "recommended_next_image"]:
        if memory[text_key] is not None and not isinstance(memory[text_key], str):
            memory[text_key] = str(memory[text_key])
    if memory["single_surface_assessment"] is not None and not isinstance(memory["single_surface_assessment"], dict):
        memory["single_surface_assessment"] = {"note": str(memory["single_surface_assessment"])}
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


def compact_memory_for_prompt(memory: Dict[str, Any]) -> Dict[str, Any]:
    memory_dict = memory if isinstance(memory, dict) else default_memory()
    known_images = []
    known_by_id: Dict[str, str] = {}
    for item in memory_dict.get("known_images", []):
        normalized = normalize_known_image_item(item)
        if not normalized:
            continue
        image_id = str(normalized.get("image_id") or "")
        image_path = str(normalized.get("image_path") or "")
        if image_id and image_path:
            known_by_id[image_id] = image_path
        known_images.append(
            {
                "image_path": image_path,
                "side_label": normalized.get("side_label"),
                "quality_overall": normalized.get("quality_overall"),
            }
        )

    visual_intake_summaries = []
    for item in memory_dict.get("visual_intakes", []):
        if not isinstance(item, dict):
            continue
        side_assessment = item.get("side_assessment") if isinstance(item.get("side_assessment"), dict) else {}
        image_quality = item.get("image_quality") if isinstance(item.get("image_quality"), dict) else {}
        candidates = []
        for candidate in item.get("candidate_diseases", []) if isinstance(item.get("candidate_diseases"), list) else []:
            if not isinstance(candidate, dict):
                continue
            disease = str(candidate.get("disease") or "").strip()
            if not disease:
                continue
            confidence = str(candidate.get("confidence") or "unknown").strip()
            candidates.append(f"{disease}:{confidence}")
            if len(candidates) >= 3:
                break
        image_id = str(item.get("image_id") or "")
        visual_intake_summaries.append(
            {
                "image_path": known_by_id.get(image_id),
                "side_label": side_assessment.get("side_label"),
                "quality_overall": image_quality.get("overall"),
                "visible_symptoms": _string_list(item.get("visible_symptoms"), max_items=6),
                "candidate_diseases": candidates,
                "intake_summary": trim_text(str(item.get("intake_summary") or ""), 320),
            }
        )

    return {
        "summary": trim_text(str(memory_dict.get("summary") or ""), 500),
        "user_goal": memory_dict.get("user_goal"),
        "current_diagnosis": memory_dict.get("current_diagnosis"),
        "evidence_sufficiency": memory_dict.get("evidence_sufficiency"),
        "known_images": known_images[-8:],
        "visual_intake_summaries": visual_intake_summaries[-8:],
        "evidence_present": _string_list(memory_dict.get("evidence_present"), max_items=6),
        "evidence_missing": _string_list(memory_dict.get("evidence_missing"), max_items=6),
        "recommended_next_image": memory_dict.get("recommended_next_image"),
        "open_questions": _string_list(memory_dict.get("open_questions"), max_items=5),
    }


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
