from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.gophereye_runtime.utils import safe_print
    from Frontier_model.frontier_agents.pipeline import DEFAULT_SESSION_DIR, run_frontier_turn
else:
    from src.gophereye_runtime.utils import safe_print
    from .frontier_agents.pipeline import DEFAULT_SESSION_DIR, run_frontier_turn


def _as_list(value: object) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text_list(value: object, *, max_items: int | None = None) -> list[str]:
    items: list[str] = []
    for item in _as_list(value):
        text = str(item).strip()
        if text and text not in items:
            items.append(text)
        if max_items is not None and len(items) >= max_items:
            break
    return items


def _humanize_token(value: object) -> str:
    return str(value).strip().replace("_", " ")


def _join_phrase(items: list[str]) -> str:
    clean = [_humanize_token(item) for item in items if str(item).strip()]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return ", ".join(clean[:-1]) + f", and {clean[-1]}"


def _auto_nonnegative_int(value: str) -> int | None:
    text = str(value).strip().lower()
    if text == "auto":
        return None
    try:
        parsed = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use a nonnegative integer or 'auto'") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("use a nonnegative integer or 'auto'")
    return parsed


def _compact_candidates(value: object) -> list[dict]:
    candidates = []
    for item in _as_list(value):
        if not isinstance(item, dict):
            text = str(item).strip()
            if text:
                candidates.append({"disease": text})
            continue
        disease = str(item.get("disease") or "").strip()
        if not disease:
            continue
        compact = {
            "disease": disease,
            "confidence": item.get("confidence"),
            "evidence": _text_list(item.get("supporting_evidence"), max_items=4),
        }
        candidates.append({key: value for key, value in compact.items() if value not in (None, [], "")})
    return candidates


def _compact_features(value: object) -> list[str]:
    features = []
    for item in _as_list(value):
        if isinstance(item, dict):
            parts = [
                str(item.get("feature") or "").strip(),
                str(item.get("location") or "").strip(),
                str(item.get("diagnostic_relevance") or "").strip(),
            ]
            parts = [part for part in parts if part and part.lower() not in {"uncertain", "unknown"}]
            text = " | ".join(parts)
        else:
            text = str(item).strip()
        if text and text not in features:
            features.append(text)
    return features


def _compact_single_surface(value: object) -> str | object:
    if not isinstance(value, dict):
        return value
    surface = value.get("visible_surface")
    decision = value.get("single_surface_decision")
    opposite_role = value.get("opposite_surface_role")
    rationale = str(value.get("rationale") or "").strip()
    decision_labels = {
        "nondiagnostic": "not diagnostic yet",
        "diagnostic_single_surface": "diagnostic from the visible surface",
        "needs_opposite_surface": "needs the opposite surface",
        "needs_specific_surface": "needs a specific additional surface",
    }
    opposite_labels = {
        "not_needed_yet": "not needed yet",
        "not_needed": "not needed",
        "needed_for_specific_uncertainty": "needed only for a specific unresolved uncertainty",
    }
    sentences = []
    if surface:
        sentences.append(f"The visible surface is {_humanize_token(surface)}.")
    if decision:
        decision_text = decision_labels.get(str(decision), _humanize_token(decision))
        sentences.append(f"The single-surface assessment is {decision_text}.")
    if opposite_role:
        opposite_text = opposite_labels.get(str(opposite_role), _humanize_token(opposite_role))
        sentences.append(f"The opposite surface is {opposite_text}.")
    if rationale:
        sentences.append(f"Reason: {rationale}")
    return " ".join(sentences) or value


def _compact_findings(intake: dict) -> list[str]:
    side_assessment = intake.get("side_assessment") if isinstance(intake.get("side_assessment"), dict) else {}
    findings: list[str] = []
    for value in [
        intake.get("visible_structure_notes"),
        intake.get("visible_symptom_notes"),
        _compact_features(intake.get("fine_visual_features")),
    ]:
        for text in _text_list(value):
            if text not in findings:
                findings.append(text)

    locations = _text_list(intake.get("symptom_locations"), max_items=5)
    if locations and not any("location" in item.lower() or "scattered" in item.lower() for item in findings):
        findings.append(f"Locations: {_join_phrase(locations)}.")

    if findings:
        return findings[:6]

    side = side_assessment.get("side_label")
    structures = _text_list(intake.get("visible_structures"), max_items=6)
    symptoms = _text_list(intake.get("visible_symptoms"), max_items=6)
    details = []
    if side:
        details.append(f"visible surface is {_humanize_token(side)}")
    if structures:
        details.append(f"structures include {_join_phrase(structures)}")
    if symptoms:
        details.append(f"symptoms include {_join_phrase(symptoms)}")
    if locations:
        details.append(f"locations include {_join_phrase(locations)}")
    return [f"{'; '.join(details)}."] if details else []


def _compact_images(memory: dict) -> list[dict]:
    known_by_id = {}
    for item in _as_list(memory.get("known_images")):
        if not isinstance(item, dict):
            continue
        image_id = item.get("image_id")
        if image_id:
            known_by_id[str(image_id)] = item

    images = []
    seen = set()
    for intake in _as_list(memory.get("visual_intakes")):
        if not isinstance(intake, dict):
            continue
        image_id = str(intake.get("image_id") or "")
        known = known_by_id.get(image_id, {})
        image_quality = intake.get("image_quality") if isinstance(intake.get("image_quality"), dict) else {}
        side_assessment = intake.get("side_assessment") if isinstance(intake.get("side_assessment"), dict) else {}
        path = known.get("image_path")
        key = image_id or str(path) or str(len(images))
        seen.add(key)

        image = {
            "image_path": path,
            "summary": intake.get("intake_summary"),
            "side": {
                "label": side_assessment.get("side_label") or known.get("side_label"),
                "confidence": side_assessment.get("confidence"),
            },
            "quality": {
                "overall": image_quality.get("overall") or known.get("quality_overall"),
                "issues": _text_list(image_quality.get("issues")),
                "impact": image_quality.get("diagnostic_impact"),
                "notes": _text_list(image_quality.get("quality_notes"), max_items=4),
            },
            "findings": _compact_findings(intake),
            "candidates": _compact_candidates(intake.get("candidate_diseases")),
        }
        images.append(_drop_empty(image))

    for image_id, known in known_by_id.items():
        key = image_id
        if key in seen:
            continue
        images.append(
            _drop_empty(
                {
                    "image_path": known.get("image_path"),
                    "side": {"label": known.get("side_label")},
                    "quality": {"overall": known.get("quality_overall")},
                }
            )
        )
    return images


def _drop_empty(value: object) -> object:
    if isinstance(value, dict):
        cleaned = {}
        for key, child in value.items():
            compact_child = _drop_empty(child)
            if compact_child in (None, "", [], {}):
                continue
            cleaned[key] = compact_child
        return cleaned
    if isinstance(value, list):
        return [item for item in (_drop_empty(item) for item in value) if item not in (None, "", [], {})]
    return value


def compact_json_result(result: dict) -> dict:
    memory = result.get("short_term_memory") if isinstance(result.get("short_term_memory"), dict) else {}
    selected_pages = [
        page.get("path") if isinstance(page, dict) else str(page)
        for page in _as_list(result.get("selected_pages"))
    ]
    attached_images = [
        item.get("image_path")
        for item in _as_list(result.get("attached_image_manifest"))
        if isinstance(item, dict) and item.get("image_path")
    ]
    compact = {
        "answer": result.get("assistant_message"),
        "diagnosis": {
            "current": memory.get("current_diagnosis"),
            "sufficiency": memory.get("evidence_sufficiency"),
            "single_surface": _compact_single_surface(memory.get("single_surface_assessment")),
            "next_image": memory.get("recommended_next_image"),
        },
        "evidence": {
            "present": _text_list(memory.get("evidence_present")),
            "missing": _text_list(memory.get("evidence_missing")),
            "limitations": _text_list(memory.get("nonblocking_image_limitations")),
            "follow_up_questions": _text_list(memory.get("allowed_follow_up_questions")),
            "open_questions": _text_list(memory.get("open_questions")),
        },
        "images": _compact_images(memory),
        "memory_summary": {
            "summary": memory.get("summary"),
            "user_goal": memory.get("user_goal"),
        },
        "context": {
            "selected_pages": [path for path in selected_pages if path],
            "page_selection": result.get("page_selection"),
            "attached_images": attached_images,
            "missing_images": _text_list(result.get("missing_image_refs")),
        },
        "status": {
            "parsed_json": result.get("parsed_json"),
            "envelope_valid": result.get("envelope_valid"),
            "fallback_used": result.get("envelope_fallback_used"),
            "validation_errors": _text_list(result.get("envelope_validation_errors")),
        },
        "usage": result.get("usage"),
    }
    return _drop_empty(compact)


def print_result(result: dict, *, as_json: bool, json_detail: str = "compact") -> None:
    if as_json:
        output = result if json_detail == "full" else compact_json_result(result)
        safe_print(json.dumps(output, ensure_ascii=False, indent=2))
        return
    safe_print(result["assistant_message"])
    safe_print("")
    safe_print(f"session_id: {result['session_id']}")
    safe_print(f"session_path: {result['session_path']}")
    safe_print(f"profile: {result['model_profile']}")
    safe_print(f"model: {result['model']}")
    safe_print(f"task_type: {result['route']['task_type']}")
    page_selection = result.get("page_selection") if isinstance(result.get("page_selection"), dict) else {}
    if page_selection.get("selected_page_limit") is not None:
        safe_print(
            "selected_page_limit: "
            f"{page_selection['selected_page_limit']} ({page_selection.get('selected_page_limit_source', 'unknown')})"
        )
    safe_print("selected_pages:")
    for page in result.get("selected_pages", []):
        safe_print(f"- {page['path']}")
    if result.get("attached_image_manifest"):
        safe_print("attached_image_manifest:")
        safe_print(json.dumps(result["attached_image_manifest"], ensure_ascii=False, indent=2))
    if result.get("missing_image_refs"):
        safe_print("missing_image_refs:")
        for image_ref in result["missing_image_refs"]:
            safe_print(f"- {image_ref}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the GopherEye frontier-model agent pipeline.")
    parser.add_argument("message", nargs="?", help="User message for this turn.")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--profile", default=None, help="Model profile from models.example.json or a custom config.")
    parser.add_argument("--config", default=None, help="Path to a model config JSON.")
    parser.add_argument("--selection-mode", choices=["keyword", "model", "full", "none"], default="keyword")
    parser.add_argument("--image-ref", action="append", default=[])
    parser.add_argument("--image-context", choices=["session", "current", "none"], default="session")
    parser.add_argument("--max-attached-images", type=int, default=8)
    parser.add_argument(
        "--max-selected-files",
        type=_auto_nonnegative_int,
        default=None,
        metavar="N|auto",
        help="Context page budget. Default auto sizes the budget from question complexity.",
    )
    parser.add_argument("--max-page-chars", type=int, default=12000)
    parser.add_argument("--recent-turns", type=int, default=8)
    parser.add_argument("--max-output-tokens", type=int, default=2400)
    parser.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-detail", choices=["compact", "full"], default="compact")
    args = parser.parse_args()

    if not args.message:
        raise SystemExit("Provide a message.")

    result = run_frontier_turn(
        args.message,
        session_id=args.session_id,
        profile_name=args.profile,
        config_path=args.config,
        selection_mode=args.selection_mode,
        image_refs=args.image_ref,
        max_selected_files=args.max_selected_files,
        max_page_chars=args.max_page_chars,
        recent_turns=args.recent_turns,
        max_output_tokens=args.max_output_tokens,
        image_context=args.image_context,
        max_attached_images=args.max_attached_images,
        session_dir=Path(args.session_dir),
    )
    print_result(result, as_json=args.json, json_detail=args.json_detail)


if __name__ == "__main__":
    main()
