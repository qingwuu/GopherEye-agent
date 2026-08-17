from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Sequence

from .image_io import resolve_image_path
from . import session_runtime as wiki_chat
from .config import DEFAULT_CONFIG_PATH, load_model_config
from .pipeline import route_task
from .providers import ModelResponse, create_backend
from .wiki2_diagnosis_prompt import build_wiki2_diagnosis_prompt_parts
from .wiki2_intake_prompt import build_wiki2_intake_prompt_parts
from .wiki2_prompt import build_wiki2_prompt_parts
from .wiki2_retrieval import (
    DEFAULT_WIKI2_CATALOG_DIR,
    DEFAULT_WIKI2_DIR,
    SIGNAL_KEYWORDS,
    infer_disease_candidates,
    is_visual_query,
    select_wiki2_context,
    select_wiki2_context_from_signals,
    select_wiki2_intake_context,
)
from src.gophereye_runtime.reflection import decide_retrieval_need
from src.gophereye_runtime.utils import now_utc, parse_json_object, timestamp_id


FRONTIER_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTIER_DIR.parent
DEFAULT_WIKI2_SESSION_DIR = REPO_ROOT / "sessions" / "wiki2"

AUTO = "auto"


def empty_wiki2_retrieval(reason: str) -> Dict[str, Any]:
    return {
        "catalog_stats": {},
        "retrieval_trace": {
            "retrieval_system": "wiki2",
            "retrieval_decision": "no_retrieve",
            "reason": reason,
            "selected_detailed_count": 0,
        },
        "selected_parent_pages": [],
        "selected_pages": [],
        "context_text": "(no wiki2 detailed pages selected)",
        "context_chars": 0,
    }


def resolve_auto_int(value: int | str | None, *, default: int, minimum: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, str):
        if value.strip().lower() == AUTO:
            return default
        try:
            value = int(value)
        except ValueError:
            return default
    return max(minimum, int(value))


def resolve_max_attached_images(value: int | str | None, *, image_refs: Sequence[str], image_context: str) -> int:
    if not (value is None or (isinstance(value, str) and value.strip().lower() == AUTO)):
        return resolve_auto_int(value, default=1, minimum=0)
    if image_context == "none":
        return 0
    if image_refs:
        return min(4, max(1, len(image_refs)))
    if image_context == "session":
        return 3
    return 0


def resolve_stage1_image_max_edge(value: int | str | None, *, image_refs: Sequence[str]) -> int:
    if value is None:
        return 1024
    if isinstance(value, str):
        text = value.strip().lower()
        if text == AUTO:
            return 1024 if len(image_refs) != 1 else 1280
        if text in {"original", "full", "none", "0"}:
            return 0
        try:
            value = int(text)
        except ValueError:
            return 1024
    return max(0, int(value))


def resolve_pipeline_mode(mode: str | None, *, user_message: str, route: Dict[str, Any], image_refs: Sequence[str]) -> str:
    requested = str(mode or AUTO).strip().lower()
    if requested in {"single", "staged"}:
        return requested
    return "staged" if is_visual_query(user_message, route, image_refs) else "single"


def prepare_wiki2_model_images(
    *,
    image_refs: Sequence[str],
    image_manifest: Sequence[Dict[str, Any]],
    session_dir: Path,
    session_id: str,
    max_edge: int,
    jpeg_quality: int = 85,
) -> tuple[list[str], list[Dict[str, Any]]]:
    if max_edge <= 0 or not image_refs:
        return list(image_refs), [dict(item) for item in image_manifest]

    try:
        from PIL import Image, ImageOps
    except Exception:
        manifest = []
        for item in image_manifest:
            enriched = dict(item)
            enriched["model_image_preprocessing"] = {
                "status": "skipped",
                "reason": "Pillow unavailable",
                "requested_max_edge": max_edge,
            }
            manifest.append(enriched)
        return list(image_refs), manifest

    out_dir = session_dir / session_id / "derived_images"
    out_dir.mkdir(parents=True, exist_ok=True)
    model_refs: list[str] = []
    model_manifest: list[Dict[str, Any]] = []
    for idx, image_ref in enumerate(image_refs, start=1):
        original_manifest = dict(image_manifest[idx - 1]) if idx - 1 < len(image_manifest) else {"image_order": idx}
        try:
            source_path = resolve_image_path(image_ref)
            with Image.open(source_path) as image:
                image = ImageOps.exif_transpose(image)
                original_size = [int(image.width), int(image.height)]
                if image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                elif image.mode == "L":
                    image = image.convert("RGB")
                scale = min(1.0, float(max_edge) / float(max(image.width, image.height)))
                if scale < 1.0:
                    new_size = (
                        max(1, int(round(image.width * scale))),
                        max(1, int(round(image.height * scale))),
                    )
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
                digest_source = f"{source_path}|{source_path.stat().st_mtime_ns}|{source_path.stat().st_size}|{max_edge}|{jpeg_quality}"
                digest = hashlib.sha1(digest_source.encode("utf-8", errors="replace")).hexdigest()[:12]
                out_path = out_dir / f"stage1_img{idx}_{max_edge}_{digest}.jpg"
                if not out_path.exists():
                    image.save(out_path, format="JPEG", quality=jpeg_quality, optimize=True)
                model_ref = out_path.resolve().as_uri()
                model_refs.append(model_ref)
                enriched = {
                    **original_manifest,
                    "model_image_uri": model_ref,
                    "model_image_path": str(out_path),
                    "original_image_uri": image_ref,
                    "original_size": original_size,
                    "model_size": [int(image.width), int(image.height)],
                    "model_image_preprocessing": {
                        "status": "resized" if scale < 1.0 else "reencoded",
                        "max_edge": max_edge,
                        "jpeg_quality": jpeg_quality,
                    },
                }
                model_manifest.append(enriched)
        except Exception as exc:
            model_refs.append(image_ref)
            enriched = {
                **original_manifest,
                "model_image_uri": image_ref,
                "model_image_preprocessing": {
                    "status": "failed_using_original",
                    "reason": str(exc),
                    "requested_max_edge": max_edge,
                },
            }
            model_manifest.append(enriched)
    return model_refs, model_manifest


def compact_prompt_image_manifest(image_manifest: Sequence[Dict[str, Any]]) -> list[Dict[str, Any]]:
    compact: list[Dict[str, Any]] = []
    for item in image_manifest:
        preprocessing = item.get("model_image_preprocessing") if isinstance(item.get("model_image_preprocessing"), dict) else {}
        compact.append(
            {
                "image_order": item.get("image_order"),
                "image_id": item.get("image_id"),
                "image_path": item.get("image_path"),
                "image_role": item.get("image_role"),
                "original_size": item.get("original_size"),
                "model_size": item.get("model_size"),
                "model_image_preprocessing": {
                    key: preprocessing.get(key)
                    for key in ["status", "max_edge", "jpeg_quality"]
                    if preprocessing.get(key) is not None
                },
            }
        )
    return compact


def auto_budget_defaults(*, route: Dict[str, Any], image_refs: Sequence[str]) -> Dict[str, int]:
    visual = is_visual_query("", route, image_refs)
    image_count = len(image_refs)
    if visual:
        return {
            "single_max_detailed_pages": 8,
            "single_max_context_chars": 6500,
            "single_max_output_tokens": 1800,
            "stage1_max_context_chars": 2400 if image_count <= 2 else 3000,
            "stage1_max_output_tokens": 1800,
            "stage2_max_detailed_pages": 10 if image_count <= 2 else 12,
            "stage2_max_context_chars": 7500 if image_count <= 2 else 9000,
            "stage3_max_output_tokens": 3200,
        }
    return {
        "single_max_detailed_pages": 6,
        "single_max_context_chars": 5000,
        "single_max_output_tokens": 1600,
        "stage1_max_context_chars": 2200,
        "stage1_max_output_tokens": 900,
        "stage2_max_detailed_pages": 8,
        "stage2_max_context_chars": 6500,
        "stage3_max_output_tokens": 1800,
    }


def selected_pages_meta(retrieval: Dict[str, Any]) -> list[Dict[str, Any]]:
    return [
        {
            "id": page.get("id"),
            "path": page.get("path"),
            "title": page.get("title"),
            "page_type": page.get("page_type"),
            "parent_path": page.get("parent_path"),
            "source_section": page.get("source_section"),
            "disease_id": page.get("disease_id"),
            "section_role": page.get("section_role"),
            "selection_reason": page.get("selection_reason"),
            "included_chars": page.get("included_chars"),
        }
        for page in retrieval.get("selected_pages", [])
    ]


def retrieval_meta(retrieval: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "catalog_stats": retrieval.get("catalog_stats"),
        "retrieval_trace": retrieval.get("retrieval_trace"),
        "selected_parent_pages": retrieval.get("selected_parent_pages"),
        "selected_pages": selected_pages_meta(retrieval),
        "context_chars": retrieval.get("context_chars"),
    }


def prompt_metrics(prompt_parts: Any, retrieval: Dict[str, Any], attached_image_manifest: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "stable_prefix_chars": len(prompt_parts.stable_prefix),
        "dynamic_context_chars": len(prompt_parts.dynamic_context),
        "total_prompt_chars": len(prompt_parts.as_text()),
        "wiki2_context_chars": retrieval.get("context_chars"),
        "selected_detailed_pages": len(retrieval.get("selected_pages", [])),
        "attached_image_count": len(attached_image_manifest),
    }


def aggregate_usage(stage_usages: Sequence[tuple[str, Dict[str, Any] | None]]) -> Dict[str, Any]:
    aggregate: Dict[str, Any] = {"stages": []}
    for stage, usage in stage_usages:
        usage = usage or {}
        aggregate["stages"].append({"stage": stage, "usage": usage})
        for key, value in usage.items():
            if isinstance(value, int):
                aggregate[key] = int(aggregate.get(key, 0)) + value
            elif isinstance(value, dict):
                nested = aggregate.setdefault(key, {})
                if isinstance(nested, dict):
                    for nested_key, nested_value in value.items():
                        if isinstance(nested_value, int):
                            nested[nested_key] = int(nested.get(nested_key, 0)) + nested_value
    return aggregate


def fallback_visual_signal_vector(
    *,
    user_message: str,
    image_refs: Sequence[str],
    raw: str,
    reason: str,
) -> Dict[str, Any]:
    candidate_hints = []
    for disease_id in infer_disease_candidates(user_message):
        candidate_hints.append(
            {
                "disease_id": disease_id,
                "support": "possible",
                "reasons": ["explicit user text disease hint"],
                "needed_detail_roles": ["visual_evidence_thresholds", "feature_checklist", "differentials"],
            }
        )
    if image_refs and not candidate_hints:
        candidate_hints.append(
            {
                "disease_id": "others",
                "support": "unresolved",
                "reasons": ["Stage 1 did not return parseable disease-specific visual hints."],
                "needed_detail_roles": ["visual_patterns", "required_handling", "differentials"],
            }
        )
    return {
        "diagnostic_stage": "visual_intake",
        "plant_part": "uncertain",
        "visible_surfaces": [
            {
                "image_order": idx,
                "surface": "uncertain",
                "confidence": "low",
                "reason": "No parseable Stage 1 surface classification.",
            }
            for idx, _ in enumerate(image_refs, start=1)
        ],
        "global_visual_signals": ["surface_uncertain", "insufficient_close_detail", "unresolved_leaf_spot_pattern"]
        if image_refs
        else [],
        "surface_observations": [],
        "candidate_hints": candidate_hints,
        "evidence_present": [],
        "evidence_missing": ["Stage 1 visual signal parsing failed."],
        "needed_detail_pages": [
            {
                "disease_id": item["disease_id"],
                "roles": item["needed_detail_roles"],
                "reason": "Fallback terminal retrieval request.",
            }
            for item in candidate_hints
        ],
        "next_retrieval_focus": ["terminal detailed disease evidence pages"],
        "stage1_parse_fallback": {
            "reason": reason,
            "raw_preview": raw[:600],
        },
    }


def known_stage1_signal_names() -> list[str]:
    names: set[str] = set()
    for values in SIGNAL_KEYWORDS.values():
        names.update(values)
    names.update(
        [
            "upper_surface_visible",
            "underside_visible",
            "surface_uncertain",
            "insufficient_close_detail",
            "noncanonical_leaf_spot_pattern",
            "unresolved_leaf_spot_pattern",
        ]
    )
    return sorted(names)


def quoted_values_after_key(raw: str, key: str, *, max_items: int = 12) -> list[str]:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\[([\s\S]{{0,1600}})', raw)
    if not match:
        return []
    allowed = set(known_stage1_signal_names())
    values: list[str] = []
    for value in re.findall(r'"([A-Za-z0-9_ -]+)"', match.group(1)):
        cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
        if cleaned in allowed and cleaned not in values:
            values.append(cleaned)
        if len(values) >= max_items:
            break
    return values


def signals_from_partial_raw(raw: str) -> list[str]:
    lower = raw.lower()
    signals = quoted_values_after_key(raw, "global_visual_signals", max_items=12)
    for name in known_stage1_signal_names():
        if name in lower and name not in signals:
            signals.append(name)
    return signals[:12]


def visible_surfaces_from_partial_raw(raw: str, image_refs: Sequence[str]) -> list[Dict[str, Any]]:
    surfaces: list[Dict[str, Any]] = []
    surface_names = ["adaxial", "abaxial", "mixed", "uncertain"]
    confidence_names = ["high", "moderate", "low"]
    for idx, _ in enumerate(image_refs, start=1):
        window_match = re.search(rf'"image_order"\s*:\s*{idx}([\s\S]{{0,700}})', raw)
        window = window_match.group(1).lower() if window_match else ""
        surface = next((name for name in surface_names if f'"{name}"' in window or name in window), "uncertain")
        confidence = next((name for name in confidence_names if f'"{name}"' in window or name in window), "low")
        reason_match = re.search(r'"reason"\s*:\s*"([^"]{0,120})"', window)
        surfaces.append(
            {
                "image_order": idx,
                "surface": surface,
                "confidence": confidence,
                "reason": reason_match.group(1).strip() if reason_match else "Recovered from partial Stage 1 output.",
            }
        )
    return surfaces


def add_salvaged_candidate(
    candidates: list[Dict[str, Any]],
    disease_id: str,
    *,
    support: str,
    reason: str,
    roles: Sequence[str],
) -> None:
    existing = next((item for item in candidates if item.get("disease_id") == disease_id), None)
    if existing:
        if reason not in existing.setdefault("reasons", []):
            existing["reasons"].append(reason)
        for role in roles:
            if role not in existing.setdefault("needed_detail_roles", []):
                existing["needed_detail_roles"].append(role)
        if existing.get("support") in {"negative", "weakened", "unresolved"} and support in {"possible", "supporting"}:
            existing["support"] = support
        return
    candidates.append(
        {
            "disease_id": disease_id,
            "support": support,
            "reasons": [reason],
            "needed_detail_roles": list(roles),
        }
    )


def candidate_hints_from_partial_raw(raw: str, signals: Sequence[str]) -> list[Dict[str, Any]]:
    lower = raw.lower()
    signal_set = set(signals)
    candidates: list[Dict[str, Any]] = []
    downy_support = any(name in signal_set for name in SIGNAL_KEYWORDS["downy_mildew_support"])
    downy_absent = any(name in signal_set for name in SIGNAL_KEYWORDS["downy_mildew_weaken"])
    powdery_support = any(name in signal_set for name in SIGNAL_KEYWORDS["powdery_mildew_support"])
    powdery_absent = any(name in signal_set for name in SIGNAL_KEYWORDS["powdery_mildew_weaken"])
    others_support = any(name in signal_set for name in SIGNAL_KEYWORDS["others_support"])
    healthy_support = any(name in signal_set for name in SIGNAL_KEYWORDS["healthy_support"])

    if "downy_mildew" in lower or downy_support or downy_absent:
        add_salvaged_candidate(
            candidates,
            "downy_mildew",
            support="possible" if downy_support else "weakened",
            reason="salvaged downy-related visual signal",
            roles=["visual_evidence_thresholds", "feature_checklist", "differentials", "image_requests"]
            if downy_support
            else ["visual_evidence_thresholds", "differentials", "image_requests"],
        )
    if "powdery_mildew" in lower or powdery_support or powdery_absent:
        add_salvaged_candidate(
            candidates,
            "powdery_mildew",
            support="supporting" if powdery_support else "weakened",
            reason="salvaged powdery-related visual signal",
            roles=["visual_evidence_thresholds", "feature_checklist", "differentials"]
            if powdery_support
            else ["visual_evidence_thresholds", "differentials"],
        )
    if "others" in lower or others_support:
        add_salvaged_candidate(
            candidates,
            "others",
            support="possible",
            reason="salvaged noncanonical or unresolved leaf-spot signal",
            roles=["visual_patterns", "required_handling", "differentials"],
        )
    if "healthy" in lower or healthy_support:
        add_salvaged_candidate(
            candidates,
            "healthy",
            support="possible",
            reason="salvaged healthy or low-symptom signal",
            roles=["minimum_evidence", "differentials"],
        )
    return candidates


def salvage_visual_signal_vector(
    *,
    raw: str,
    user_message: str,
    image_refs: Sequence[str],
) -> Dict[str, Any] | None:
    signals = signals_from_partial_raw(raw)
    candidate_hints = candidate_hints_from_partial_raw(raw, signals)
    if not signals and not candidate_hints:
        return None
    evidence_missing = []
    if any(signal.endswith("_absent") for signal in signals):
        evidence_missing.extend([signal for signal in signals if signal.endswith("_absent")][:4])
    return {
        "diagnostic_stage": "visual_intake",
        "plant_part": "grape_leaf" if "grape_leaf" in raw.lower() or "grape" in user_message.lower() else "uncertain",
        "visible_surfaces": visible_surfaces_from_partial_raw(raw, image_refs),
        "global_visual_signals": signals[:10],
        "surface_observations": [],
        "candidate_hints": candidate_hints,
        "evidence_present": [signal for signal in signals if not signal.endswith("_absent")][:6],
        "evidence_missing": evidence_missing[:6],
        "needed_detail_pages": [
            {
                "disease_id": item["disease_id"],
                "roles": item.get("needed_detail_roles") or [],
                "reason": "Recovered from partial Stage 1 output.",
            }
            for item in candidate_hints
        ],
        "next_retrieval_focus": ["terminal detailed disease evidence pages"],
        "stage1_parse_salvage": {
            "reason": "Stage 1 JSON was incomplete or invalid, but visual signals were recovered from raw output.",
        },
    }


def extract_visual_signal_vector(raw: str, *, user_message: str, image_refs: Sequence[str]) -> Dict[str, Any]:
    parsed = parse_json_object(raw)
    if isinstance(parsed, dict):
        vector = parsed.get("visual_signal_vector")
        if isinstance(vector, dict):
            vector = dict(vector)
            vector.setdefault("diagnostic_stage", "visual_intake")
            vector.setdefault("candidate_hints", [])
            vector.setdefault("global_visual_signals", [])
            vector.setdefault("evidence_present", [])
            vector.setdefault("evidence_missing", [])
            return vector
        if any(key in parsed for key in ["candidate_hints", "global_visual_signals", "visible_surfaces"]):
            parsed.setdefault("diagnostic_stage", "visual_intake")
            return parsed
    salvaged = salvage_visual_signal_vector(
        raw=raw,
        user_message=user_message,
        image_refs=image_refs,
    )
    if salvaged:
        return salvaged
    return fallback_visual_signal_vector(
        user_message=user_message,
        image_refs=image_refs,
        raw=raw,
        reason="Stage 1 response did not contain visual_signal_vector.",
    )


def json_string_value(raw: str, key: str) -> str | None:
    key_pattern = f'"{key}"'
    key_pos = raw.find(key_pattern)
    if key_pos < 0:
        return None
    colon_pos = raw.find(":", key_pos + len(key_pattern))
    if colon_pos < 0:
        return None
    quote_pos = raw.find('"', colon_pos + 1)
    if quote_pos < 0:
        return None
    idx = quote_pos + 1
    escaped = False
    while idx < len(raw):
        char = raw[idx]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            try:
                return json.loads(raw[quote_pos : idx + 1])
            except json.JSONDecodeError:
                return None
        idx += 1
    return None


def confidence_float(value: Any) -> float:
    text = str(value or "").strip().lower()
    if text == "high":
        return 0.9
    if text == "moderate":
        return 0.65
    if text == "low":
        return 0.35
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def sentence_from_signals(prefix: str, values: Sequence[Any], *, fallback: str) -> str:
    signals = [str(value).replace("_", " ") for value in values if str(value or "").strip()]
    if not signals:
        return fallback
    return f"{prefix}: {', '.join(signals[:4])}."


def compact_list(values: Any, *, max_items: int) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def memory_update_from_visual_signal_vector(
    *,
    visual_signal_vector: Dict[str, Any],
    user_message: str,
) -> Dict[str, Any]:
    candidate_hints = [
        item
        for item in visual_signal_vector.get("candidate_hints", [])
        if isinstance(item, dict) and item.get("disease_id")
    ]
    candidate_labels = [str(item.get("disease_id")) for item in candidate_hints][:3]
    primary = candidate_labels[0] if candidate_labels else "unresolved"
    surfaces = visual_signal_vector.get("visible_surfaces") if isinstance(visual_signal_vector.get("visible_surfaces"), list) else []
    observations = visual_signal_vector.get("surface_observations") if isinstance(visual_signal_vector.get("surface_observations"), list) else []
    observations_by_order: Dict[int, Dict[str, Any]] = {}
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        try:
            order = int(observation.get("image_order"))
        except (TypeError, ValueError):
            continue
        observations_by_order[order] = observation

    image_observations: list[Dict[str, Any]] = []
    for idx, surface in enumerate(surfaces, start=1):
        if not isinstance(surface, dict):
            continue
        try:
            image_order = int(surface.get("image_order") or idx)
        except (TypeError, ValueError):
            image_order = idx
        observation = observations_by_order.get(image_order, {})
        present = compact_list(observation.get("signals_present"), max_items=4)
        absent = compact_list(observation.get("signals_absent"), max_items=4)
        distribution = str(observation.get("distribution") or "").strip()
        texture = str(observation.get("diagnostic_texture") or "").strip()
        findings = [
            sentence_from_signals(
                "Visible signals",
                present,
                fallback="Visible leaf symptoms were recorded from Stage 1.",
            ),
            sentence_from_signals(
                "Missing canonical signs",
                absent,
                fallback=texture or distribution or "Fine diagnostic texture remains incompletely resolved.",
            ),
        ]
        if distribution and distribution not in findings[0]:
            findings[0] = f"{findings[0].rstrip()} Distribution: {distribution}."
        image_observations.append(
            {
                "image_order": image_order,
                "is_leaf_image": visual_signal_vector.get("plant_part") == "grape_leaf",
                "side_label": surface.get("surface") or "uncertain",
                "side_confidence": confidence_float(surface.get("confidence")),
                "quality_overall": "good",
                "quality_issues": [],
                "diagnostic_impact": "none",
                "quality_notes": [],
                "findings": findings[:2],
                "candidate_labels": candidate_labels,
                "candidate_confidence": "moderate" if candidate_labels else "unknown",
                "candidate_supporting_evidence": compact_list(
                    visual_signal_vector.get("evidence_present"),
                    max_items=2,
                ),
                "intake_summary": f"Stage 1 visual intake supports {primary} as the leading route.",
            }
        )

    if not image_observations:
        image_observations = [
            {
                "image_order": 1,
                "is_leaf_image": visual_signal_vector.get("plant_part") == "grape_leaf",
                "side_label": "uncertain",
                "side_confidence": 0.0,
                "quality_overall": "usable_with_caution",
                "quality_issues": [],
                "diagnostic_impact": "minor_nonblocking",
                "quality_notes": [],
                "findings": ["Stage 1 visual signals were recorded, but per-image detail was incomplete."],
                "candidate_labels": candidate_labels,
                "candidate_confidence": "unknown",
                "candidate_supporting_evidence": compact_list(visual_signal_vector.get("evidence_present"), max_items=2),
                "intake_summary": "Stage 1 visual intake recorded provisional diagnostic signals.",
            }
        ]

    evidence_present = compact_list(visual_signal_vector.get("evidence_present"), max_items=6)
    if not evidence_present:
        evidence_present = compact_list(visual_signal_vector.get("global_visual_signals"), max_items=6)
    evidence_missing = compact_list(visual_signal_vector.get("evidence_missing"), max_items=6)
    next_need = "close_up_same_surface" if any("macro" in item or "detail" in item for item in evidence_missing) else None
    return {
        "summary": f"Stage 3 JSON was salvaged after truncation. Stage 1 visual intake supports {primary} with unresolved visual diagnosis boundaries.",
        "user_goal": user_message,
        "current_diagnosis": f"Possible {primary}." if primary != "unresolved" else "Unresolved visual diagnosis.",
        "image_observations": image_observations,
        "evidence_present": evidence_present,
        "evidence_missing": evidence_missing,
        "diagnosis_verdict": "possible_not_confirmed",
        "next_image_need": next_need,
        "nonblocking_limitations": ["Stage 3 JSON was truncated; memory was reconstructed from Stage 1 signals."],
        "allowed_follow_up_questions": [],
        "open_questions": [],
    }


def salvage_diagnosis_envelope(
    *,
    raw: str,
    visual_signal_vector: Dict[str, Any],
    user_message: str,
    route: Dict[str, Any],
    original_prompt: str,
) -> Dict[str, Any] | None:
    assistant_message = json_string_value(raw, "assistant_message")
    if not assistant_message:
        stripped = raw.strip()
        if stripped.startswith("## Assessment"):
            assistant_message = stripped
    if not assistant_message:
        return None
    payload = {
        "assistant_message": assistant_message.strip(),
        "memory_update": memory_update_from_visual_signal_vector(
            visual_signal_vector=visual_signal_vector,
            user_message=user_message,
        ),
    }
    envelope = wiki_chat.resolve_assistant_envelope(
        json.dumps(payload, ensure_ascii=False),
        role=wiki_chat.frontier_envelope_role(route["task_type"]),
        expected_task_type=route["task_type"],
        original_prompt=original_prompt,
    )
    if envelope["envelope_valid"]:
        envelope["attempts"].append(
            {
                "attempt": "local_stage3_truncation_salvage",
                "parsed_json": True,
                "envelope_valid": True,
                "errors": [],
            }
        )
        return envelope
    return None


def run_single_wiki2_turn(
    *,
    backend: Any,
    profile_name: str,
    profile_model: str,
    session: Dict[str, Any],
    user_turn_id: int,
    user_message: str,
    image_refs: Sequence[str],
    route: Dict[str, Any],
    retrieval_decision: Dict[str, Any],
    selection_query: str,
    max_detailed_pages: int,
    max_context_chars: int,
    max_children_per_parent: int,
    include_parent_pages: str,
    recent_turns: int,
    max_output_tokens: int,
    image_context: str,
    max_attached_images: int,
    repair_envelope: bool,
    clean_session_id: str,
    session_dir: Path,
    wiki2_dir: Path,
    wiki2_catalog_dir: Path,
) -> Dict[str, Any]:
    if retrieval_decision.get("retrieval_decision") == "no_retrieve":
        retrieval = empty_wiki2_retrieval(str(retrieval_decision.get("retrieval_reason") or "not needed"))
    else:
        retrieval = select_wiki2_context(
            selection_query,
            route=route,
            memory=session.get("short_term_memory", wiki_chat.default_memory()),
            image_refs=image_refs,
            max_detailed_pages=max_detailed_pages,
            max_context_chars=max_context_chars,
            max_children_per_parent=max_children_per_parent,
            include_parent_pages=include_parent_pages,
            wiki2_dir=wiki2_dir,
            catalog_dir=wiki2_catalog_dir,
        )
        retrieval.setdefault("retrieval_trace", {})["retrieval_decision"] = retrieval_decision

    requested_image_records = wiki_chat.collect_image_records_for_context(
        session,
        image_refs,
        image_context=image_context,
        max_attached_images=max_attached_images,
    )
    attached_image_refs, missing_image_refs, attached_image_manifest = wiki_chat.resolve_vlm_image_refs(
        requested_image_records,
        session_dir=session_dir,
        session_id=clean_session_id,
    )

    prompt_parts = build_wiki2_prompt_parts(
        session=session,
        user_message=user_message,
        image_refs=image_refs,
        route=route,
        retrieval=retrieval,
        recent_turns=recent_turns,
        attached_image_manifest=attached_image_manifest,
        missing_image_refs=missing_image_refs,
        profile_name=profile_name,
    )
    prompt_text = prompt_parts.as_text()
    model_response = backend.generate(
        prompt_text,
        image_refs=attached_image_refs,
        max_output_tokens=max_output_tokens,
    )
    raw = model_response.text
    repair_response: ModelResponse | None = None

    def repair_callback(repair_prompt: str) -> str:
        nonlocal repair_response
        repair_response = backend.generate(
            repair_prompt,
            image_refs=attached_image_refs,
            max_output_tokens=max(max_output_tokens, 1800),
        )
        return repair_response.text

    envelope = wiki_chat.resolve_assistant_envelope(
        raw,
        role=wiki_chat.frontier_envelope_role(route["task_type"]),
        expected_task_type=route["task_type"],
        original_prompt=prompt_text,
        repair_callback=repair_callback if repair_envelope else None,
    )
    return {
        "pipeline_mode": "single",
        "retrieval": retrieval,
        "requested_image_records": requested_image_records,
        "attached_image_refs": attached_image_refs,
        "attached_image_manifest": attached_image_manifest,
        "missing_image_refs": missing_image_refs,
        "raw_model_output": raw,
        "repair_model_output": repair_response.text if repair_response else None,
        "final_model_output": envelope["final_raw"],
        "envelope": envelope,
        "usage": model_response.usage,
        "repair_usage": repair_response.usage if repair_response else None,
        "backend_meta": model_response.backend_meta,
        "repair_backend_meta": repair_response.backend_meta if repair_response else None,
        "prompt_metrics": {
            **prompt_metrics(prompt_parts, retrieval, attached_image_manifest),
            "pipeline_mode": "single",
        },
        "stages": {},
        "memory_mapping_image_manifest": attached_image_manifest,
    }


def run_staged_wiki2_turn(
    *,
    backend: Any,
    profile_name: str,
    session: Dict[str, Any],
    user_message: str,
    image_refs: Sequence[str],
    route: Dict[str, Any],
    retrieval_decision: Dict[str, Any],
    selection_query: str,
    stage1_max_context_chars: int,
    stage1_max_output_tokens: int,
    stage1_image_max_edge: int,
    stage2_max_detailed_pages: int,
    stage2_max_context_chars: int,
    max_children_per_parent: int,
    include_parent_pages: str,
    recent_turns: int,
    stage3_max_output_tokens: int,
    image_context: str,
    max_attached_images: int,
    stage3_images: bool,
    repair_envelope: bool,
    clean_session_id: str,
    session_dir: Path,
    wiki2_dir: Path,
    wiki2_catalog_dir: Path,
) -> Dict[str, Any]:
    requested_image_records = wiki_chat.collect_image_records_for_context(
        session,
        image_refs,
        image_context=image_context,
        max_attached_images=max_attached_images,
    )
    attached_image_refs, missing_image_refs, attached_image_manifest = wiki_chat.resolve_vlm_image_refs(
        requested_image_records,
        session_dir=session_dir,
        session_id=clean_session_id,
    )
    stage1_image_refs, stage1_image_manifest = prepare_wiki2_model_images(
        image_refs=attached_image_refs,
        image_manifest=attached_image_manifest,
        session_dir=session_dir,
        session_id=clean_session_id,
        max_edge=stage1_image_max_edge,
    )
    stage1_prompt_image_manifest = compact_prompt_image_manifest(stage1_image_manifest)

    intake_retrieval = select_wiki2_intake_context(
        max_context_chars=stage1_max_context_chars,
        wiki2_dir=wiki2_dir,
        catalog_dir=wiki2_catalog_dir,
    )
    intake_retrieval.setdefault("retrieval_trace", {})["retrieval_decision"] = retrieval_decision
    intake_prompt_parts = build_wiki2_intake_prompt_parts(
        session=session,
        user_message=user_message,
        image_refs=image_refs,
        route=route,
        retrieval=intake_retrieval,
        recent_turns=recent_turns,
        attached_image_manifest=stage1_prompt_image_manifest,
        missing_image_refs=missing_image_refs,
        profile_name=profile_name,
    )
    intake_prompt_text = intake_prompt_parts.as_text()
    intake_response = backend.generate(
        intake_prompt_text,
        image_refs=stage1_image_refs,
        max_output_tokens=stage1_max_output_tokens,
    )
    visual_signal_vector = extract_visual_signal_vector(
        intake_response.text,
        user_message=user_message,
        image_refs=image_refs,
    )

    terminal_retrieval = select_wiki2_context_from_signals(
        query=selection_query,
        visual_signal_vector=visual_signal_vector,
        route=route,
        memory=session.get("short_term_memory", wiki_chat.default_memory()),
        image_refs=image_refs,
        max_detailed_pages=stage2_max_detailed_pages,
        max_context_chars=stage2_max_context_chars,
        max_children_per_parent=max_children_per_parent,
        include_parent_pages=include_parent_pages,
        wiki2_dir=wiki2_dir,
        catalog_dir=wiki2_catalog_dir,
    )
    terminal_retrieval.setdefault("retrieval_trace", {})["retrieval_decision"] = retrieval_decision

    final_image_refs = stage1_image_refs if stage3_images else []
    final_image_manifest = stage1_image_manifest if stage3_images else []
    final_prompt_image_manifest = compact_prompt_image_manifest(final_image_manifest)
    diagnosis_prompt_parts = build_wiki2_diagnosis_prompt_parts(
        session=session,
        user_message=user_message,
        image_refs=image_refs,
        route=route,
        retrieval=terminal_retrieval,
        visual_signal_vector=visual_signal_vector,
        recent_turns=recent_turns,
        stage1_image_manifest=stage1_prompt_image_manifest,
        attached_image_manifest=final_prompt_image_manifest,
        missing_image_refs=missing_image_refs,
        profile_name=profile_name,
    )
    diagnosis_prompt_text = diagnosis_prompt_parts.as_text()
    diagnosis_response = backend.generate(
        diagnosis_prompt_text,
        image_refs=final_image_refs,
        max_output_tokens=stage3_max_output_tokens,
    )
    raw = diagnosis_response.text
    repair_response: ModelResponse | None = None

    def repair_callback(repair_prompt: str) -> str:
        nonlocal repair_response
        repair_response = backend.generate(
            repair_prompt,
            image_refs=final_image_refs,
            max_output_tokens=max(stage3_max_output_tokens, 2000),
        )
        return repair_response.text

    envelope = wiki_chat.resolve_assistant_envelope(
        raw,
        role=wiki_chat.frontier_envelope_role(route["task_type"]),
        expected_task_type=route["task_type"],
        original_prompt=diagnosis_prompt_text,
        repair_callback=repair_callback if repair_envelope else None,
    )
    if not envelope["envelope_valid"]:
        salvaged_envelope = salvage_diagnosis_envelope(
            raw=raw,
            visual_signal_vector=visual_signal_vector,
            user_message=user_message,
            route=route,
            original_prompt=diagnosis_prompt_text,
        )
        if salvaged_envelope is not None:
            envelope = salvaged_envelope

    intake_metrics = prompt_metrics(intake_prompt_parts, intake_retrieval, stage1_prompt_image_manifest)
    diagnosis_metrics = prompt_metrics(diagnosis_prompt_parts, terminal_retrieval, final_prompt_image_manifest)
    combined_usage = aggregate_usage(
        [
            ("stage1_visual_intake", intake_response.usage),
            ("stage3_diagnosis", diagnosis_response.usage),
        ]
    )

    return {
        "pipeline_mode": "staged",
        "retrieval": terminal_retrieval,
        "requested_image_records": requested_image_records,
        "attached_image_refs": attached_image_refs,
        "attached_image_manifest": attached_image_manifest,
        "stage1_model_image_refs": stage1_image_refs,
        "stage1_model_image_manifest": stage1_image_manifest,
        "missing_image_refs": missing_image_refs,
        "raw_model_output": raw,
        "repair_model_output": repair_response.text if repair_response else None,
        "final_model_output": envelope["final_raw"],
        "envelope": envelope,
        "usage": combined_usage,
        "repair_usage": repair_response.usage if repair_response else None,
        "backend_meta": {
            "stage1": intake_response.backend_meta,
            "stage3": diagnosis_response.backend_meta,
        },
        "repair_backend_meta": repair_response.backend_meta if repair_response else None,
        "prompt_metrics": {
            **diagnosis_metrics,
            "pipeline_mode": "staged",
            "stage1_prompt_chars": intake_metrics["total_prompt_chars"],
            "stage3_prompt_chars": diagnosis_metrics["total_prompt_chars"],
            "total_text_prompt_chars": intake_metrics["total_prompt_chars"] + diagnosis_metrics["total_prompt_chars"],
            "stage1_wiki2_context_chars": intake_retrieval.get("context_chars"),
            "stage2_wiki2_context_chars": terminal_retrieval.get("context_chars"),
            "stage1_attached_image_count": len(stage1_image_manifest),
            "stage3_attached_image_count": len(final_image_manifest),
            "stage1_image_max_edge": stage1_image_max_edge,
        },
        "stages": {
            "stage1_visual_intake": {
                "retrieval": retrieval_meta(intake_retrieval),
                "visual_signal_vector": visual_signal_vector,
                "usage": intake_response.usage,
                "prompt_metrics": intake_metrics,
                "raw_model_output": intake_response.text,
                "model_image_manifest": stage1_image_manifest,
            },
            "stage2_terminal_retrieval": {
                "retrieval": retrieval_meta(terminal_retrieval),
                "visual_signal_vector": visual_signal_vector,
            },
            "stage3_diagnosis": {
                "usage": diagnosis_response.usage,
                "prompt_metrics": diagnosis_metrics,
                "images_attached": bool(stage3_images),
            },
        },
        "memory_mapping_image_manifest": attached_image_manifest,
    }


def run_wiki2_turn(
    user_message: str,
    *,
    session_id: str | None = None,
    profile_name: str | None = None,
    config_path: str | Path | None = None,
    image_refs: Sequence[str] = (),
    pipeline_mode: str | None = AUTO,
    max_detailed_pages: int | str | None = AUTO,
    max_context_chars: int | str | None = AUTO,
    max_children_per_parent: int | str | None = AUTO,
    include_parent_pages: str = "never",
    recent_turns: int | str | None = AUTO,
    max_output_tokens: int | str | None = AUTO,
    stage1_max_context_chars: int | str | None = AUTO,
    stage1_max_output_tokens: int | str | None = AUTO,
    stage1_image_max_edge: int | str | None = AUTO,
    stage2_max_detailed_pages: int | str | None = AUTO,
    stage2_max_context_chars: int | str | None = AUTO,
    stage3_max_output_tokens: int | str | None = AUTO,
    stage3_images: bool = False,
    image_context: str = "current",
    max_attached_images: int | str | None = AUTO,
    repair_envelope: bool = False,
    session_dir: Path = DEFAULT_WIKI2_SESSION_DIR,
    wiki2_dir: Path = DEFAULT_WIKI2_DIR,
    wiki2_catalog_dir: Path = DEFAULT_WIKI2_CATALOG_DIR,
) -> Dict[str, Any]:
    config = load_model_config(config_path or DEFAULT_CONFIG_PATH)
    profile = config.get_profile(profile_name)
    backend = create_backend(profile)

    clean_session_id = session_id or f"wiki2_session_{timestamp_id()}"
    provider_label = f"wiki2:{profile.name}:{profile.provider}"
    session = wiki_chat.load_session(
        clean_session_id,
        session_dir=session_dir,
        provider=provider_label,
        model=profile.model,
    )
    session["provider"] = provider_label
    session["model"] = profile.model
    session["model_profile"] = profile.name
    session["wiki_system"] = "wiki2"
    wiki_chat.hydrate_id_history_from_session(session)

    user_turn_id = len(session.get("messages", [])) + 1
    session.setdefault("messages", []).append(
        {
            "turn_id": user_turn_id,
            "role": "user",
            "content": user_message,
            "created_at": now_utc(),
            "image_refs": list(image_refs),
        }
    )
    wiki_chat.register_image_refs(session, image_refs, turn_id=user_turn_id)

    route = route_task(user_message, image_refs)
    resolved_pipeline_mode = resolve_pipeline_mode(
        pipeline_mode,
        user_message=user_message,
        route=route,
        image_refs=image_refs,
    )
    budgets = auto_budget_defaults(route=route, image_refs=image_refs)
    resolved_max_detailed_pages = resolve_auto_int(
        max_detailed_pages,
        default=budgets["single_max_detailed_pages"],
        minimum=1,
    )
    resolved_max_context_chars = resolve_auto_int(
        max_context_chars,
        default=budgets["single_max_context_chars"],
        minimum=1000,
    )
    resolved_max_output_tokens = resolve_auto_int(
        max_output_tokens,
        default=budgets["single_max_output_tokens"],
        minimum=400,
    )
    resolved_stage1_max_context_chars = resolve_auto_int(
        stage1_max_context_chars,
        default=budgets["stage1_max_context_chars"],
        minimum=1000,
    )
    resolved_stage1_max_output_tokens = resolve_auto_int(
        stage1_max_output_tokens,
        default=budgets["stage1_max_output_tokens"],
        minimum=400,
    )
    resolved_stage1_image_max_edge = resolve_stage1_image_max_edge(
        stage1_image_max_edge,
        image_refs=image_refs,
    )
    resolved_stage2_max_detailed_pages = resolve_auto_int(
        stage2_max_detailed_pages,
        default=budgets["stage2_max_detailed_pages"],
        minimum=4,
    )
    resolved_stage2_max_context_chars = resolve_auto_int(
        stage2_max_context_chars,
        default=budgets["stage2_max_context_chars"],
        minimum=2500,
    )
    resolved_stage3_max_output_tokens = resolve_auto_int(
        stage3_max_output_tokens,
        default=budgets["stage3_max_output_tokens"],
        minimum=800,
    )
    resolved_max_children_per_parent = resolve_auto_int(
        max_children_per_parent,
        default=4 if resolved_pipeline_mode == "staged" else 3,
        minimum=1,
    )
    resolved_recent_turns = resolve_auto_int(recent_turns, default=3, minimum=0)
    resolved_max_attached_images = resolve_max_attached_images(
        max_attached_images,
        image_refs=image_refs,
        image_context=image_context,
    )

    retrieval_decision = decide_retrieval_need(
        user_message=user_message,
        route=route,
        memory=session.get("short_term_memory", wiki_chat.default_memory()),
        image_refs=image_refs,
    )
    selection_query = "\n".join(
        part
        for part in [
            user_message,
            session.get("short_term_memory", {}).get("summary") or "",
            session.get("short_term_memory", {}).get("current_diagnosis") or "",
            " ".join(session.get("short_term_memory", {}).get("evidence_present") or []),
            " ".join(session.get("short_term_memory", {}).get("evidence_missing") or []),
        ]
        if part
    )

    if resolved_pipeline_mode == "staged":
        execution = run_staged_wiki2_turn(
            backend=backend,
            profile_name=profile.name,
            session=session,
            user_message=user_message,
            image_refs=image_refs,
            route=route,
            retrieval_decision=retrieval_decision,
            selection_query=selection_query,
            stage1_max_context_chars=resolved_stage1_max_context_chars,
            stage1_max_output_tokens=resolved_stage1_max_output_tokens,
            stage1_image_max_edge=resolved_stage1_image_max_edge,
            stage2_max_detailed_pages=resolved_stage2_max_detailed_pages,
            stage2_max_context_chars=resolved_stage2_max_context_chars,
            max_children_per_parent=resolved_max_children_per_parent,
            include_parent_pages=include_parent_pages,
            recent_turns=resolved_recent_turns,
            stage3_max_output_tokens=resolved_stage3_max_output_tokens,
            image_context=image_context,
            max_attached_images=resolved_max_attached_images,
            stage3_images=stage3_images,
            repair_envelope=repair_envelope,
            clean_session_id=clean_session_id,
            session_dir=session_dir,
            wiki2_dir=wiki2_dir,
            wiki2_catalog_dir=wiki2_catalog_dir,
        )
    else:
        execution = run_single_wiki2_turn(
            backend=backend,
            profile_name=profile.name,
            profile_model=profile.model,
            session=session,
            user_turn_id=user_turn_id,
            user_message=user_message,
            image_refs=image_refs,
            route=route,
            retrieval_decision=retrieval_decision,
            selection_query=selection_query,
            max_detailed_pages=resolved_max_detailed_pages,
            max_context_chars=resolved_max_context_chars,
            max_children_per_parent=resolved_max_children_per_parent,
            include_parent_pages=include_parent_pages,
            recent_turns=resolved_recent_turns,
            max_output_tokens=resolved_max_output_tokens,
            image_context=image_context,
            max_attached_images=resolved_max_attached_images,
            repair_envelope=repair_envelope,
            clean_session_id=clean_session_id,
            session_dir=session_dir,
            wiki2_dir=wiki2_dir,
            wiki2_catalog_dir=wiki2_catalog_dir,
        )

    envelope = execution["envelope"]
    previous_memory = session.get("short_term_memory", wiki_chat.default_memory())
    memory_update = envelope["memory_update"]
    if not envelope["envelope_valid"]:
        memory_update = wiki_chat.minimal_memory_update_after_envelope_failure(
            previous_memory,
            envelope["validation_errors"],
        )
    session["short_term_memory"] = wiki_chat.normalize_memory(
        memory_update,
        previous_memory,
        session=session,
        attached_image_manifest=execution.get("memory_mapping_image_manifest") or execution.get("attached_image_manifest") or [],
        turn_id=user_turn_id,
    )

    assistant_turn_id = len(session.get("messages", [])) + 1
    assistant_message = envelope["assistant_message"]
    session["messages"].append(
        {
            "turn_id": assistant_turn_id,
            "role": "assistant",
            "content": assistant_message,
            "created_at": now_utc(),
        }
    )

    retrieval = execution["retrieval"]
    resolved_parameters = {
        "pipeline_mode_requested": pipeline_mode,
        "pipeline_mode_resolved": resolved_pipeline_mode,
        "max_detailed_pages": resolved_max_detailed_pages,
        "max_context_chars": resolved_max_context_chars,
        "max_children_per_parent": resolved_max_children_per_parent,
        "recent_turns": resolved_recent_turns,
        "max_output_tokens": resolved_max_output_tokens,
        "stage1_max_context_chars": resolved_stage1_max_context_chars,
        "stage1_max_output_tokens": resolved_stage1_max_output_tokens,
        "stage1_image_max_edge": resolved_stage1_image_max_edge,
        "stage2_max_detailed_pages": resolved_stage2_max_detailed_pages,
        "stage2_max_context_chars": resolved_stage2_max_context_chars,
        "stage3_max_output_tokens": resolved_stage3_max_output_tokens,
        "stage3_images": stage3_images,
        "image_context": image_context,
        "max_attached_images": resolved_max_attached_images,
    }
    turn_meta = {
        "user_turn_id": user_turn_id,
        "assistant_turn_id": assistant_turn_id,
        "wiki_system": "wiki2",
        "pipeline_mode": resolved_pipeline_mode,
        "resolved_parameters": resolved_parameters,
        "provider": provider_label,
        "model": profile.model,
        "model_profile": profile.name,
        "route": route,
        "retrieval": retrieval_meta(retrieval),
        "stages": execution.get("stages") or {},
        "image_context": image_context,
        "max_attached_images": resolved_max_attached_images,
        "requested_image_records": execution.get("requested_image_records"),
        "attached_image_refs": execution.get("attached_image_refs"),
        "attached_image_manifest": execution.get("attached_image_manifest"),
        "missing_image_refs": execution.get("missing_image_refs"),
        "raw_model_output": execution.get("raw_model_output"),
        "repair_model_output": execution.get("repair_model_output"),
        "final_model_output": execution.get("final_model_output"),
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
        "usage": execution.get("usage"),
        "repair_usage": execution.get("repair_usage"),
        "backend_meta": execution.get("backend_meta"),
        "repair_backend_meta": execution.get("repair_backend_meta"),
        "prompt_metrics": execution.get("prompt_metrics"),
        "created_at": now_utc(),
    }
    session.setdefault("turns", []).append(turn_meta)
    path = wiki_chat.save_session(session, session_dir=session_dir)

    return {
        "session_path": str(path),
        "session_id": clean_session_id,
        "provider": provider_label,
        "model": profile.model,
        "model_profile": profile.name,
        "wiki_system": "wiki2",
        "pipeline_mode": resolved_pipeline_mode,
        "resolved_parameters": resolved_parameters,
        "route": route,
        "retrieval": turn_meta["retrieval"],
        "stages": turn_meta["stages"],
        "selected_pages": turn_meta["retrieval"]["selected_pages"],
        "attached_image_manifest": execution.get("attached_image_manifest"),
        "missing_image_refs": execution.get("missing_image_refs"),
        "assistant_message": assistant_message,
        "short_term_memory": session["short_term_memory"],
        "raw_model_output": execution.get("raw_model_output"),
        "final_model_output": envelope["final_raw"],
        "parsed_json": envelope["parsed_json"],
        "envelope_valid": envelope["envelope_valid"],
        "envelope_validation_errors": envelope["validation_errors"],
        "usage": execution.get("usage"),
        "repair_usage": execution.get("repair_usage"),
        "prompt_metrics": turn_meta["prompt_metrics"],
    }
