from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Sequence

from . import session_runtime as wiki_chat


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class Wiki2DiagnosisPromptParts:
    stable_prefix: str
    dynamic_context: str

    def as_text(self) -> str:
        return f"{self.stable_prefix.rstrip()}\n\n{self.dynamic_context.lstrip()}"


def build_wiki2_diagnosis_stable_prefix() -> str:
    return """You are GopherEye's independent wiki2 Stage 3 diagnostic synthesis agent.

Return ONLY valid JSON with this top-level shape:
{
  "assistant_message": "professional English markdown diagnostic report",
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
- wiki2 is split-page knowledge. Parent pages are routing maps only.
- detailed_section_page content is the primary evidence unit for answers.
- Cite detailed wiki2 page paths in assistant_message when making knowledge claims.
- Use only selected wiki2 detailed context pages, Stage 1 visual_signal_vector,
  compact session memory, and any explicitly attached images.
- Do not invent facts from unselected sibling pages.
- Do not recommend treatment unless selected detailed treatment/source-policy
  pages are included.
- Image pixels are normally inspected in Stage 1 and not re-attached in Stage 3
  to control token cost. Do not say image pixels were unavailable merely because
  Stage 3 has no image attachments.

Required assistant_message format:
Use these headings exactly, in this order:
## Assessment
## Image Evidence
## Candidate Comparison
## Most Supported Classification
## Evidence Against Canonical Diseases
## Unresolved Boundary
## Next Best Observation
## Wiki2 Detailed Pages Used

Content requirements:
- Be concise but professional. This is not a one-sentence app blurb.
- Keep assistant_message under 750 words.
- Use bare wiki2 paths in parentheses for citations. Do not use markdown links.
- The report must explain the whole-to-local diagnostic path:
  leaf/image validity, visible surface or surface uncertainty, dominant visual
  pattern, candidate disease comparison, terminal detailed-page evidence, and
  the specific remaining uncertainty.
- If Stage 1 has stage1_parse_salvage, use the recovered signals as visual
  evidence and mention only that the Stage 1 JSON was partially recovered if
  that limitation affects confidence.
- If Stage 1 has stage1_parse_fallback, say signal extraction failed; do not
  say the original images were unavailable unless missing_image_refs says so.
- Prefer "possible", "most supported", or "unresolved" language unless selected
  evidence supports a stronger visual verdict.
- If a canonical disease is weakened, say what visible sign is absent or not
  resolved.
- If "others" is selected, explain why the pattern falls into unresolved or
  noncanonical handling.
- Request a next image only when it resolves a stated uncertainty from selected
  wiki2 context.

Output constraints:
- Write assistant_message in English only.
- Use image_observations[] only for per-image visual evidence. App code expands
  compact observations into persisted memory schema.
- evidence_present and evidence_missing must stay short, max 6 items each.
- findings max 2 sentences per image.
- candidate_labels max 3 items.
- candidate_supporting_evidence max 2 items.
- quality_notes should be [] unless there is a real quality limitation.
- allowed_follow_up_questions and open_questions should be [] unless essential.
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


def build_wiki2_diagnosis_dynamic_context(
    *,
    session: Dict[str, Any],
    user_message: str,
    image_refs: Sequence[str],
    route: Dict[str, Any],
    retrieval: Dict[str, Any],
    visual_signal_vector: Dict[str, Any],
    recent_turns: int,
    stage1_image_manifest: Sequence[Dict[str, Any]],
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
    candidate_map = retrieval_trace.get("candidate_map") if isinstance(retrieval_trace.get("candidate_map"), dict) else {}
    terminal_path_plan = (
        retrieval_trace.get("terminal_path_plan")
        if isinstance(retrieval_trace.get("terminal_path_plan"), list)
        else []
    )
    compact_trace = {
        "retrieval_stage": retrieval_trace.get("retrieval_stage"),
        "signal_driven": retrieval_trace.get("signal_driven"),
        "selected_detailed_count": retrieval_trace.get("selected_detailed_count"),
        "candidate_map": {
            disease_id: {
                "support": item.get("support"),
                "roles": item.get("roles"),
                "reasons": list(item.get("reasons") or [])[:3],
            }
            for disease_id, item in candidate_map.items()
            if isinstance(item, dict)
        },
        "terminal_paths": [
            {
                "disease_id": item.get("disease_id"),
                "support": item.get("support"),
                "paths": item.get("paths"),
            }
            for item in terminal_path_plan
            if isinstance(item, dict)
        ],
    }
    signal_for_prompt = dict(visual_signal_vector or {})
    if isinstance(signal_for_prompt.get("stage1_parse_fallback"), dict):
        fallback = dict(signal_for_prompt["stage1_parse_fallback"])
        fallback.pop("raw_preview", None)
        signal_for_prompt["stage1_parse_fallback"] = fallback
    selected_page_summary = [
        {
            "path": page.get("path"),
            "section": page.get("source_section") or page.get("section_role"),
            "disease_id": page.get("disease_id"),
            "selection_reason": page.get("selection_reason"),
        }
        for page in retrieval.get("selected_pages", [])
    ]
    return f"""Model profile:
{profile_name}

Route:
{compact_json(route)}

Current short-term memory JSON:
(compact view; code-owned IDs, timestamps, and full schema objects are omitted)
{compact_json(memory)}

Recent transcript, last {recent_turns} messages:
{wiki_chat.render_recent_messages(wiki_chat.recent_messages(session, recent_turns, exclude_last=True))}

Stage 1 visual_signal_vector JSON:
{compact_json(signal_for_prompt)}

Stage 1 image manifest used to map image_order into memory:
{compact_json(list(stage1_image_manifest))}

Image manifest whose pixels are attached to this final call:
{compact_json(list(attached_image_manifest))}

The image pixels were already inspected in Stage 1. Use the Stage 1 visual_signal_vector as the visual evidence source when Stage 3 has no image attachments.

Image refs that were requested but could not be loaded:
{compact_json(list(missing_image_refs))}

Compact Stage 2 wiki2 terminal retrieval trace JSON:
{compact_json(compact_trace)}

Selected wiki2 detailed page summary:
{compact_json(selected_page_summary)}

Selected wiki2 detailed context pages:
{retrieval.get("context_text") or "(no wiki2 detailed pages selected)"}

Current user message JSON:
{compact_json(current_turn)}

Return final JSON envelope now:"""


def build_wiki2_diagnosis_prompt_parts(
    *,
    session: Dict[str, Any],
    user_message: str,
    image_refs: Sequence[str],
    route: Dict[str, Any],
    retrieval: Dict[str, Any],
    visual_signal_vector: Dict[str, Any],
    recent_turns: int,
    stage1_image_manifest: Sequence[Dict[str, Any]],
    attached_image_manifest: Sequence[Dict[str, Any]],
    missing_image_refs: Sequence[str],
    profile_name: str,
) -> Wiki2DiagnosisPromptParts:
    return Wiki2DiagnosisPromptParts(
        stable_prefix=build_wiki2_diagnosis_stable_prefix(),
        dynamic_context=build_wiki2_diagnosis_dynamic_context(
            session=session,
            user_message=user_message,
            image_refs=image_refs,
            route=route,
            retrieval=retrieval,
            visual_signal_vector=visual_signal_vector,
            recent_turns=recent_turns,
            stage1_image_manifest=stage1_image_manifest,
            attached_image_manifest=attached_image_manifest,
            missing_image_refs=missing_image_refs,
            profile_name=profile_name,
        ),
    )
