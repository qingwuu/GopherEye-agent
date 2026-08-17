from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Sequence

from . import session_runtime as wiki_chat


@dataclass(frozen=True)
class Wiki2PromptParts:
    stable_prefix: str
    dynamic_context: str

    def as_text(self) -> str:
        return f"{self.stable_prefix.rstrip()}\n\n{self.dynamic_context.lstrip()}"


def build_wiki2_stable_prefix() -> str:
    return """You are GopherEye's independent wiki2 diagnostic app.

Return ONLY valid JSON with this compact top-level shape:
{
  "assistant_message": "concise but professional English answer to the user",
  "memory_update": {
    "summary": "compact memory of the session so far",
    "user_goal": null,
    "current_diagnosis": null,
    "image_observations": [
      {
        "image_order": 1,
        "is_leaf_image": true,
        "side_label": "uncertain",
        "side_confidence": 0.0,
        "quality_overall": "good",
        "quality_issues": [],
        "diagnostic_impact": "none",
        "quality_notes": [],
        "findings": [
          "Surface/structure: short sentence covering visible surface and structures.",
          "Symptoms/location: short sentence covering symptoms and where they occur.",
          "Diagnostic texture: short sentence covering fungal texture and uncertainty."
        ],
        "candidate_labels": [],
        "candidate_confidence": "unknown",
        "candidate_supporting_evidence": [],
        "intake_summary": "short visual evidence summary"
      }
    ],
    "evidence_present": [],
    "evidence_missing": [],
    "diagnosis_verdict": "possible_not_confirmed",
    "next_image_need": null,
    "nonblocking_limitations": [],
    "allowed_follow_up_questions": [],
    "open_questions": []
  }
}

Wiki2 knowledge contract:
- wiki2 is split-page knowledge. Parent pages are routing maps.
- detailed_section_page content is the primary evidence unit for answers.
- Do not treat parent pages as sufficient evidence unless the selected context
  explicitly says no detailed page exists.
- If selected context is too general, say which detailed evidence is missing.
- Cite detailed wiki2 page paths in assistant_message when making knowledge claims.
- Use only selected wiki2 context pages, image evidence, and compact session memory.
- Do not invent facts from unselected sibling pages.
- Use the smallest sufficient detailed evidence set. Do not assume all siblings
  were loaded.

Diagnosis behavior:
- For visual diagnosis, observe image evidence before naming a disease.
- Keep uncertainty visible. Image-only diagnosis can be possible or provisional;
  do not imply lab confirmation.
- Do not request the opposite leaf surface automatically. Request it only when
  it resolves a specific uncertainty stated in selected context.
- Do not recommend treatment unless selected detailed treatment/source-policy
  pages are included.
- If treatment or source context is missing, say reviewed management resources
  are missing instead of improvising.

Output constraints:
- Write assistant_message in English only.
- Keep assistant_message concise but clinically structured enough for the task.
- Use image_observations[] only for per-image visual evidence. App code expands
  compact observations into persisted memory schema.
- evidence_present and evidence_missing must stay short, max 5 items each.
- findings max 3 sentences per image.
- candidate_labels max 2 items.
- candidate_confidence must be low, moderate, high, very_high, or unknown.
- quality_overall must be good, usable_with_caution, or unusable.
- quality_issues should use blurry, dark, overexposed, poor_angle, occluded,
  low_resolution, or duplicate.
- diagnostic_impact must be none, minor_nonblocking, or blocks_symptom_inspection.
- next_image_need must be null, close_up_same_surface, opposite_surface,
  adaxial_surface, or abaxial_surface.
- diagnosis_verdict should be confirmed, possible_not_confirmed, insufficient,
  or uncertain.
- Do not create or modify session_id, turn_id, image_id, image_path, image_uri,
  image_role, visual_intake_id, created_at, updated_at, first_seen_turn_id,
  last_seen_turn_id, source, or agent_trace fields.
"""


def build_wiki2_dynamic_context(
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
    current_turn = {
        "role": "user",
        "content": user_message,
        "image_refs": list(image_refs),
    }
    memory = wiki_chat.compact_memory_for_prompt(
        session.get("short_term_memory", wiki_chat.default_memory())
    )
    retrieval_trace = retrieval.get("retrieval_trace", {})
    selected_page_summary = [
        {
            "path": page.get("path"),
            "page_type": page.get("page_type"),
            "parent": page.get("parent_path"),
            "section": page.get("source_section") or page.get("section_role"),
            "disease_id": page.get("disease_id"),
            "selection_reason": page.get("selection_reason"),
            "included_chars": page.get("included_chars"),
        }
        for page in retrieval.get("selected_pages", [])
    ]
    return f"""Model profile:
{profile_name}

Route:
{json.dumps(route, ensure_ascii=False, indent=2)}

Current short-term memory JSON:
(compact view; code-owned IDs, timestamps, and full schema objects are omitted)
{json.dumps(memory, ensure_ascii=False, indent=2)}

Recent transcript, last {recent_turns} messages:
{wiki_chat.render_recent_messages(wiki_chat.recent_messages(session, recent_turns, exclude_last=True))}

Attached image manifest for this model call:
{json.dumps(list(attached_image_manifest), ensure_ascii=False, indent=2)}

The actual image pixels are attached to the model in the same order as this manifest.

Image refs that were requested but could not be loaded:
{json.dumps(list(missing_image_refs), ensure_ascii=False, indent=2)}

Wiki2 retrieval trace JSON:
{json.dumps(retrieval_trace, ensure_ascii=False, indent=2)}

Selected wiki2 detailed page summary:
{json.dumps(selected_page_summary, ensure_ascii=False, indent=2)}

Selected wiki2 detailed context pages:
{retrieval.get("context_text") or "(no wiki2 detailed pages selected)"}

Current user message JSON:
{json.dumps(current_turn, ensure_ascii=False, indent=2)}

Return JSON now:"""


def build_wiki2_prompt_parts(
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
) -> Wiki2PromptParts:
    return Wiki2PromptParts(
        stable_prefix=build_wiki2_stable_prefix(),
        dynamic_context=build_wiki2_dynamic_context(
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
