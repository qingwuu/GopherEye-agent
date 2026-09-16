from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object.")
    return value


def latest_turn(session: Dict[str, Any]) -> Dict[str, Any]:
    turns = session.get("turns")
    if not isinstance(turns, list) or not turns:
        raise SystemExit("Session JSON does not contain turns[].")
    turn = turns[-1]
    if not isinstance(turn, dict):
        raise SystemExit("Latest turn is not an object.")
    return turn


def images_from_result(value: Dict[str, Any]) -> List[Dict[str, Any]]:
    images = value.get("images")
    return images if isinstance(images, list) else []


def images_from_session(value: Dict[str, Any]) -> List[Dict[str, Any]]:
    images: List[Dict[str, Any]] = []
    memory = value.get("short_term_memory") if isinstance(value.get("short_term_memory"), dict) else {}
    for intake in memory.get("visual_intakes", []) if isinstance(memory.get("visual_intakes"), list) else []:
        if not isinstance(intake, dict):
            continue
        image_path = ""
        image_id = intake.get("image_id")
        for known in memory.get("known_images", []) if isinstance(memory.get("known_images"), list) else []:
            if isinstance(known, dict) and known.get("image_id") == image_id:
                image_path = str(known.get("image_path") or "")
                break
        side = intake.get("side_assessment") if isinstance(intake.get("side_assessment"), dict) else {}
        quality = intake.get("image_quality") if isinstance(intake.get("image_quality"), dict) else {}
        images.append(
            {
                "image_path": image_path,
                "side": {"label": side.get("side_label"), "confidence": side.get("confidence")},
                "quality": quality,
                "candidates": [
                    {
                        "disease": candidate.get("disease"),
                        "confidence": candidate.get("confidence"),
                        "evidence": candidate.get("supporting_evidence"),
                    }
                    for candidate in intake.get("candidate_diseases", [])
                    if isinstance(candidate, dict)
                ],
                "visible_structures": intake.get("visible_structures"),
            }
        )
    return images


def result_view(value: Dict[str, Any]) -> Dict[str, Any]:
    if "turns" in value and "short_term_memory" in value:
        turn = latest_turn(value)
        return {
            "status": {
                "final_refinement_used": turn.get("final_refinement_used"),
                "claim_gate_fallback_used": turn.get("claim_gate_fallback_used"),
                "parsed_json": turn.get("parsed_json"),
                "envelope_valid": turn.get("envelope_valid"),
            },
            "reflection": turn.get("reflection") if isinstance(turn.get("reflection"), dict) else {},
            "images": images_from_session(value),
            "evidence": {
                "present": (value.get("short_term_memory") or {}).get("evidence_present", []),
            },
        }
    return value


def check(value: Dict[str, Any]) -> List[str]:
    result = result_view(value)
    errors: List[str] = []
    status = result.get("status") if isinstance(result.get("status"), dict) else {}
    reflection = result.get("reflection") if isinstance(result.get("reflection"), dict) else {}

    if status.get("final_refinement_used") is not False:
        errors.append("final_refinement_used should be false.")
    if status.get("claim_gate_fallback_used") is not False:
        errors.append("claim_gate_fallback_used should be false.")
    if reflection.get("needs_human_review") is not False:
        errors.append("reflection.needs_human_review should be false.")
    if reflection.get("overall_support_status") not in {"fully_supported", "partially_supported"}:
        errors.append("reflection.overall_support_status should be fully_supported or partially_supported.")

    images = images_from_result(result)
    for index, image in enumerate(images, start=1):
        for candidate in image.get("candidates", []) if isinstance(image.get("candidates"), list) else []:
            if not isinstance(candidate, dict):
                continue
            if str(candidate.get("disease") or "").lower() == "downy mildew":
                confidence = str(candidate.get("confidence") or "")
                if confidence != "low":
                    errors.append(f"image {index} Downy mildew confidence should be low, got {confidence!r}.")
        side = ((image.get("side") or {}).get("label") or "").lower() if isinstance(image.get("side"), dict) else ""
        structures = image.get("visible_structures")
        if isinstance(structures, list):
            if side == "abaxial" and "adaxial_surface" in structures:
                errors.append(f"image {index} is abaxial but includes adaxial_surface.")
            if side == "adaxial" and "abaxial_surface" in structures:
                errors.append(f"image {index} is adaxial but includes abaxial_surface.")

    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    present = evidence.get("present") if isinstance(evidence.get("present"), list) else []
    if len(present) != len({str(item).strip().lower() for item in present}):
        errors.append("evidence.present contains exact duplicate entries.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Check a GopherEye Chat Agent run JSON/session JSON.")
    parser.add_argument("path", type=Path, help="Path to compact result JSON or sessions/frontier/*.json.")
    args = parser.parse_args()

    errors = check(load_json(args.path))
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        raise SystemExit(1)
    print("PASS: chat run checks passed.")


if __name__ == "__main__":
    main()
