from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Sequence

from . import session_runtime as wiki_chat


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class Wiki2IntakePromptParts:
    stable_prefix: str
    dynamic_context: str

    def as_text(self) -> str:
        return f"{self.stable_prefix.rstrip()}\n\n{self.dynamic_context.lstrip()}"


def build_wiki2_intake_stable_prefix() -> str:
    return """You are GopherEye wiki2 Stage 1 visual intake.

Purpose:
- Inspect the attached grape leaf image pixels.
- Produce a compact retrieval signal vector for Stage 2.
- Do not write the final diagnosis report.
- Output must be short enough to finish. Prefer controlled signal names over
  prose. Minify the JSON if needed.

Return ONLY valid JSON with this shape:
{
  "visual_signal_vector": {
    "diagnostic_stage": "visual_intake",
    "plant_part": "grape_leaf | uncertain",
    "visible_surfaces": [
      {
        "image_order": 1,
        "surface": "adaxial | abaxial | mixed | uncertain",
        "confidence": "low | moderate | high",
        "reason": "max 10 words"
      }
    ],
    "global_visual_signals": [
      "max 8 controlled snake_case visual signals"
    ],
    "surface_observations": [
      {
        "image_order": 1,
        "signals_present": [],
        "signals_absent": [],
        "distribution": "max 8 words",
        "diagnostic_texture": "max 8 words"
      }
    ],
    "candidate_hints": [
      {
        "disease_id": "powdery_mildew | downy_mildew | healthy | others",
        "support": "supporting | possible | weakened | negative | unresolved",
        "reasons": [],
        "needed_detail_roles": []
      }
    ],
    "evidence_present": [],
    "evidence_missing": [],
    "needed_detail_pages": [
      {
        "disease_id": "downy_mildew",
        "roles": ["visual_evidence_thresholds", "feature_checklist", "differentials", "image_requests"],
        "reason": "why these terminal detailed pages are needed"
      }
    ],
    "next_retrieval_focus": []
  }
}

Controlled signal examples:
- necrotic_leaf_spots
- yellow_brown_lesions
- vein_bounded_or_angular_lesions
- oil_spot_like_yellowing
- cottony_downy_sporulation_present
- cottony_downy_sporulation_absent
- white_gray_powdery_colonies_present
- white_gray_powdery_colonies_absent
- residue_or_glare_possible
- underside_visible
- upper_surface_visible
- surface_uncertain
- insufficient_close_detail
- healthy_variation_possible
- noncanonical_leaf_spot_pattern

Rules:
- Separate observation from interpretation.
- Candidate hints are retrieval hints, not final labels.
- Maximums: 2 visible_surfaces per two input images, 8 global_visual_signals,
  2 signals_present and 2 signals_absent per image, 4 candidate_hints,
  2 reasons per candidate, and 4 needed_detail_roles per candidate.
- In signals_absent, use explicit *_absent names. For example, write
  white_gray_powdery_colonies_absent, not white_gray_powdery_colonies_present.
- Include a candidate as weakened when the canonical sign is specifically absent
  but it remains a necessary differential.
- Include "others" when lesions, necrosis, scorch, specks, insect-like damage,
  mixed signs, or noncanonical patterns are visible or unresolved.
- If output space is tight, omit surface_observations first; never omit
  global_visual_signals or candidate_hints.
- Keep this JSON compact. Do not include markdown, citations, or final diagnosis.
"""


def build_wiki2_intake_dynamic_context(
    *,
    session: Dict[str, Any],
    user_message: str,
    image_refs: Sequence[str],
    route: Dict[str, Any],
    retrieval: Dict[str, Any],
    recent_turns: int,
    attached_image_manifest: Sequence[Dict[str, Any]],
    missing_image_refs: Sequence[str],
    profile_name: str,
) -> str:
    memory = wiki_chat.compact_memory_for_prompt(
        session.get("short_term_memory", wiki_chat.default_memory())
    )
    return f"""Model profile:
{profile_name}

Route:
{compact_json(route)}

Current short-term memory JSON:
{compact_json(memory)}

Recent transcript, last {recent_turns} messages:
{wiki_chat.render_recent_messages(wiki_chat.recent_messages(session, recent_turns, exclude_last=True))}

Attached image manifest for this Stage 1 call:
{compact_json(list(attached_image_manifest))}

The actual image pixels are attached to the model in the same order as this manifest.

Image refs that were requested but could not be loaded:
{compact_json(list(missing_image_refs))}

Minimal wiki2 intake context:
{retrieval.get("context_text") or "(no wiki2 intake pages selected)"}

Current user message JSON:
{compact_json({"role": "user", "content": user_message, "image_refs": list(image_refs)})}

Return the Stage 1 visual_signal_vector JSON now:"""


def build_wiki2_intake_prompt_parts(
    *,
    session: Dict[str, Any],
    user_message: str,
    image_refs: Sequence[str],
    route: Dict[str, Any],
    retrieval: Dict[str, Any],
    recent_turns: int,
    attached_image_manifest: Sequence[Dict[str, Any]],
    missing_image_refs: Sequence[str],
    profile_name: str,
) -> Wiki2IntakePromptParts:
    return Wiki2IntakePromptParts(
        stable_prefix=build_wiki2_intake_stable_prefix(),
        dynamic_context=build_wiki2_intake_dynamic_context(
            session=session,
            user_message=user_message,
            image_refs=image_refs,
            route=route,
            retrieval=retrieval,
            recent_turns=recent_turns,
            attached_image_manifest=attached_image_manifest,
            missing_image_refs=missing_image_refs,
            profile_name=profile_name,
        ),
    )
