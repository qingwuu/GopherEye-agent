from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .config import DEFAULT_CONFIG_PATH, load_model_config
from .providers import create_backend


FRONTIER_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTIER_DIR.parent
APP_DIR = REPO_ROOT
DEFAULT_SYSTEM_DIR = REPO_ROOT / "system"
DEFAULT_SYSTEM_CATALOG_DIR = FRONTIER_DIR / "catalog" / "system"
CORE_WIKI_CONTEXT_BY_TASK = {
    "visual_intake_or_diagnosis": [
        "procedures/whole_diagnosis_process.md",
        "procedures/visual_observation_sequence.md",
        "procedures/symptom_localization_procedure.md",
        "workflows/evidence_sufficiency.md",
        "workflows/front_back_leaf_process.md",
    ],
    "grape_leaf_chat": [
        "procedures/whole_diagnosis_process.md",
        "procedures/visual_observation_sequence.md",
        "workflows/evidence_sufficiency.md",
    ],
}
CORE_SYSTEM_CONTEXT_BY_TASK = {
    "data_management": [
        "data/data_agent_workflow.md",
        "data/dataset_memory.md",
        "agents/frontier_agent_system.md",
        "contracts/schema_layer.md",
    ],
}

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import chat as wiki_chat  # noqa: E402
from src.single_model_wiki.core import (  # noqa: E402
    DEFAULT_CATALOG_DIR,
    DEFAULT_WIKI_DIR,
    load_or_build_catalog,
    now_utc,
    read_all_pages,
    read_pages_by_id,
    render_catalog_for_prompt,
    select_pages_keyword_fallback,
    timestamp_id,
)


DEFAULT_SESSION_DIR = FRONTIER_DIR / "sessions"


def parse_json_array(text: str) -> List[Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    match = re.search(r"\[[\s\S]*\]", stripped)
    if match:
        stripped = match.group(0)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def route_task(user_message: str, image_refs: Sequence[str]) -> Dict[str, Any]:
    text = user_message.lower()
    data_keywords = [
        "data",
        "dataset",
        "ingestion",
        "ingest",
        "pipeline",
        "label",
        "labeling",
        "annotation",
        "annotate",
        "human review",
        "reviewed dataset",
        "unreviewed",
        "ground truth",
        "capture-turn",
        "import-review",
        "data agent",
        "data collection",
        "collection",
        "upload",
        "metadata",
        "index",
        "review queue",
    ]
    wiki_keywords = ["wiki", "source"]
    grape_keywords = [
        "grape",
        "leaf",
        "powdery",
        "downy",
        "disease",
        "diagnosis",
    ]

    wiki_keywords.extend(
        [
            "sources",
            "paper",
            "literature",
            "knowledge",
            "knowledge base",
            "curated",
            "update",
        ]
    )
    grape_keywords.extend(
        [
            "mildew",
            "symptom",
        ]
    )

    if any(token in text for token in data_keywords):
        task_type = "data_management"
    elif image_refs:
        task_type = "visual_intake_or_diagnosis"
    elif any(token in text for token in wiki_keywords):
        task_type = "knowledge_management"
    elif any(token in text for token in grape_keywords):
        task_type = "grape_leaf_chat"
    else:
        task_type = "general_project_chat"

    path_by_task = {
        "data_management": ["router", "data_agent", "chat_agent"],
        "visual_intake_or_diagnosis": ["router", "vision_agent", "retrieval_agent", "diagnosis_agent"],
        "knowledge_management": ["router", "retrieval_agent", "wiki_agent"],
        "grape_leaf_chat": ["router", "retrieval_agent", "chat_agent"],
        "general_project_chat": ["router", "chat_agent"],
    }
    return {
        "task_type": task_type,
        "selected_agent_path": path_by_task[task_type],
        "needs_vision": bool(image_refs),
    }


def context_for_route(
    route: Dict[str, Any],
    *,
    wiki_dir: Path,
    catalog_dir: Path,
) -> Dict[str, Any]:
    if route["task_type"] in {"data_management", "knowledge_management", "general_project_chat"}:
        return {
            "label": "system",
            "root_dir": DEFAULT_SYSTEM_DIR,
            "catalog_dir": DEFAULT_SYSTEM_CATALOG_DIR,
        }
    return {
        "label": "wiki",
        "root_dir": wiki_dir,
        "catalog_dir": catalog_dir,
    }


def core_context_paths_for_route(route: Dict[str, Any], context_label: str) -> List[str]:
    if context_label == "wiki":
        return list(CORE_WIKI_CONTEXT_BY_TASK.get(route["task_type"], []))
    if context_label == "system":
        return list(CORE_SYSTEM_CONTEXT_BY_TASK.get(route["task_type"], []))
    return []


def select_pages_for_backend(
    *,
    query: str,
    backend: Any,
    selection_mode: str,
    max_selected_files: int,
    max_page_chars: int,
    wiki_dir: Path,
    catalog_dir: Path,
    core_paths: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    catalog = load_or_build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)
    ids_by_path = {page["path"]: page["id"] for page in catalog.get("pages", [])}
    core_ids = []
    for path in core_paths:
        page_id = ids_by_path.get(path)
        if page_id and page_id not in core_ids:
            core_ids.append(page_id)

    if selection_mode == "none":
        return []
    elif selection_mode == "full":
        return read_all_pages(catalog=catalog, wiki_dir=wiki_dir, max_page_chars=max_page_chars)
    elif selection_mode == "keyword":
        selected_ids = select_pages_keyword_fallback(
            query,
            catalog=catalog,
            max_selected_files=max_selected_files,
        )
    elif selection_mode == "model":
        prompt = f"""You are selecting GopherEye context pages for an agent workflow.

Return ONLY a JSON array of page IDs.
Select at most {max_selected_files} IDs.

User/session query:
{query}

Context catalog:
{render_catalog_for_prompt(catalog)}
"""
        raw = backend.generate(prompt, max_output_tokens=512).text
        selected = parse_json_array(raw)
        valid_ids = {page["id"] for page in catalog.get("pages", [])}
        selected_ids = []
        for item in selected:
            if isinstance(item, str) and item in valid_ids and item not in selected_ids:
                selected_ids.append(item)
        if not selected_ids:
            selected_ids = select_pages_keyword_fallback(
                query,
                catalog=catalog,
                max_selected_files=max_selected_files,
            )
    else:
        raise ValueError(f"Unsupported selection_mode: {selection_mode}")

    selected_ids = core_ids + [page_id for page_id in selected_ids if page_id not in core_ids]
    return read_pages_by_id(
        selected_ids[:max_selected_files],
        catalog=catalog,
        wiki_dir=wiki_dir,
        max_page_chars=max_page_chars,
    )


def build_frontier_prompt(
    *,
    session: Dict[str, Any],
    user_message: str,
    image_refs: Sequence[str],
    route: Dict[str, Any],
    pages: Sequence[Dict[str, Any]],
    recent_turns: int,
    attached_image_manifest: Sequence[Dict[str, Any]],
    missing_image_refs: Sequence[str],
    profile_name: str,
    context_label: str,
) -> str:
    current_turn = {
        "role": "user",
        "content": user_message,
        "image_refs": list(image_refs),
    }
    return f"""You are GopherEye's frontier multi-agent diagnostic app.

Return ONLY valid JSON with this exact top-level shape:
{{
  "assistant_message": "short app-ready English answer to the user",
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

Agent responsibilities:
- Router decides whether this is visual diagnosis, grape-leaf chat, knowledge management,
  data management, or general project chat.
- Vision agent inspects attached image pixels when they are present.
- Retrieval agent uses selected context pages only; do not invent facts outside them.
- For visual diagnosis, detailed botanical procedure must come from selected wiki pages,
  not from hidden assumptions in this prompt.
- Diagnosis agent keeps uncertainty visible according to selected wiki procedure pages.
- Data agent can explain how to collect, ingest, validate, store, audit, and evaluate data.

Rules:
- Write assistant_message in English only.
- Stay within grape leaf diagnosis and GopherEye project behavior.
- For botanical diagnosis, follow the selected wiki procedure pages for leaf
  identity, image quality, surface assessment, evidence sufficiency, front/back
  comparison, differential diagnosis, and next-image requests.
- Do not recommend treatment unless a reviewed management page is included.
- If images are attached, inspect pixels and update known_image_updates and visual_intakes.
- If no image pixels are attached, rely only on memory, transcript, selected context pages, and user text.
- Do not create or modify session_id, turn_id, image_id, image_path,
  visual_intake_id, created_at, or updated_at fields.
- For image-specific updates, use only image_order from the attached image manifest.
- Do not output agent_trace. Route, selected agent path, and context metadata are
  recorded by app code outside the model JSON.
- Use canonical values when obvious, and put natural-language botanical detail in
  quality_notes, visible_symptom_notes, visible_structure_notes, evidence_present,
  evidence_missing, or intake_summary.

Model profile:
{profile_name}

Route:
{json.dumps(route, ensure_ascii=False, indent=2)}

Current short-term memory JSON:
{json.dumps(session.get("short_term_memory", wiki_chat.default_memory()), ensure_ascii=False, indent=2)}

Recent transcript, last {recent_turns} messages:
{wiki_chat.render_recent_messages(wiki_chat.recent_messages(session, recent_turns, exclude_last=True))}

Attached image manifest for this model call:
{json.dumps(list(attached_image_manifest), ensure_ascii=False, indent=2)}

The actual image pixels are attached to the model in the same order as this manifest.

Image refs that were requested but could not be loaded:
{json.dumps(list(missing_image_refs), ensure_ascii=False, indent=2)}

Selected {context_label} context pages:
{wiki_chat.render_pages(pages)}

Current user message JSON:
{json.dumps(current_turn, ensure_ascii=False, indent=2)}

Return JSON now:"""


def run_frontier_turn(
    user_message: str,
    *,
    session_id: str | None = None,
    profile_name: str | None = None,
    config_path: str | Path | None = None,
    selection_mode: str = "keyword",
    image_refs: Sequence[str] = (),
    max_selected_files: int = 6,
    max_page_chars: int = 12000,
    recent_turns: int = 8,
    max_output_tokens: int = 900,
    image_context: str = "session",
    max_attached_images: int = 8,
    session_dir: Path = DEFAULT_SESSION_DIR,
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> Dict[str, Any]:
    config = load_model_config(config_path or DEFAULT_CONFIG_PATH)
    profile = config.get_profile(profile_name)
    backend = create_backend(profile)

    clean_session_id = session_id or f"frontier_session_{timestamp_id()}"
    provider_label = f"frontier:{profile.name}:{profile.provider}"
    session = wiki_chat.load_session(
        clean_session_id,
        session_dir=session_dir,
        provider=provider_label,
        model=profile.model,
    )
    session["provider"] = provider_label
    session["model"] = profile.model
    session["model_profile"] = profile.name
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
    context = context_for_route(route, wiki_dir=wiki_dir, catalog_dir=catalog_dir)
    selection_query = wiki_chat.build_selection_query(session, user_message)
    pages = select_pages_for_backend(
        query=selection_query,
        backend=backend,
        selection_mode=selection_mode,
        max_selected_files=max_selected_files,
        max_page_chars=max_page_chars,
        wiki_dir=context["root_dir"],
        catalog_dir=context["catalog_dir"],
        core_paths=core_context_paths_for_route(route, context["label"]),
    )
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

    prompt = build_frontier_prompt(
        session=session,
        user_message=user_message,
        image_refs=image_refs,
        route=route,
        pages=pages,
        recent_turns=recent_turns,
        attached_image_manifest=attached_image_manifest,
        missing_image_refs=missing_image_refs,
        profile_name=profile.name,
        context_label=context["label"],
    )
    model_response = backend.generate(
        prompt,
        image_refs=attached_image_refs,
        max_output_tokens=max_output_tokens,
    )
    raw = model_response.text
    repair_responses = []

    def repair_frontier_envelope(repair_prompt: str) -> str:
        repair_response = backend.generate(
            repair_prompt,
            image_refs=attached_image_refs,
            max_output_tokens=max_output_tokens,
        )
        repair_responses.append(repair_response)
        return repair_response.text

    envelope = wiki_chat.resolve_assistant_envelope(
        raw,
        role=wiki_chat.frontier_envelope_role(route["task_type"]),
        expected_task_type=route["task_type"],
        original_prompt=prompt,
        repair_callback=repair_frontier_envelope,
    )
    assistant_message = envelope["assistant_message"]
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
        attached_image_manifest=attached_image_manifest,
        turn_id=user_turn_id,
    )

    assistant_turn_id = len(session.get("messages", [])) + 1
    session["messages"].append(
        {
            "turn_id": assistant_turn_id,
            "role": "assistant",
            "content": assistant_message,
            "created_at": now_utc(),
        }
    )
    turn_meta = {
        "user_turn_id": user_turn_id,
        "assistant_turn_id": assistant_turn_id,
        "provider": provider_label,
        "model": profile.model,
        "model_profile": profile.name,
        "route": route,
        "context_label": context["label"],
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
        "usage": model_response.usage,
        "repair_usage": repair_responses[0].usage if repair_responses else None,
        "backend_meta": model_response.backend_meta,
        "repair_backend_meta": repair_responses[0].backend_meta if repair_responses else None,
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
        "route": route,
        "context_label": context["label"],
        "assistant_message": assistant_message,
        "short_term_memory": session["short_term_memory"],
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
        "usage": model_response.usage,
    }
