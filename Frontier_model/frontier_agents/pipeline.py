from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .config import DEFAULT_CONFIG_PATH, load_model_config
from .providers import create_backend
from . import session_runtime as wiki_chat


FRONTIER_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTIER_DIR.parent
DEFAULT_SYSTEM_DIR = REPO_ROOT / "system"
DEFAULT_SYSTEM_CATALOG_DIR = REPO_ROOT / "catalog" / "system"
CORE_WIKI_CONTEXT_BY_TASK = {
    "visual_intake_or_diagnosis": [
        "procedures/diagnosis_sop.md",
        "procedures/image_and_evidence_sop.md",
        "disease/powdery_mildew/index.md",
        "disease/downy_mildew/index.md",
        "disease/healthy/index.md",
        "disease/others/index.md",
    ],
    "grape_leaf_chat": [
        "procedures/diagnosis_sop.md",
        "procedures/image_and_evidence_sop.md",
        "disease/powdery_mildew/index.md",
        "disease/downy_mildew/index.md",
    ],
}
CORE_SYSTEM_CONTEXT_BY_TASK = {
    "data_management": [
        "data/dataset_memory.md",
        "agents/frontier_agent_system.md",
        "contracts/schema_layer.md",
    ],
}

AUTO_SELECTED_PAGE_CEILING = 12
AUTO_SELECTED_PAGE_BASE_BY_TASK = {
    "general_project_chat": 3,
    "data_management": 4,
    "knowledge_management": 5,
    "grape_leaf_chat": 4,
    "visual_intake_or_diagnosis": 6,
}
COMPLEXITY_CUES = [
    "compare",
    "difference",
    "differentiate",
    "diagnose",
    "diagnosis",
    "differential",
    "workflow",
    "pipeline",
    "plan",
    "strategy",
    "evaluate",
    "tradeoff",
    "trade-off",
    "treatment",
    "management",
    "source",
    "schema",
    "memory",
    "why",
    "how",
    "what should",
    "all",
    "multiple",
    "complex",
    "比较",
    "区别",
    "诊断",
    "鉴别",
    "流程",
    "方案",
    "计划",
    "评估",
    "权衡",
    "治疗",
    "管理",
    "来源",
    "证据",
    "为什么",
    "怎么",
    "如何",
    "全部",
    "多个",
    "复杂",
]
RETRIEVAL_QUERY_HINTS = [
    (["白粉病", "白粉"], "powdery mildew"),
    (["霜霉病", "霜霉"], "downy mildew"),
    (["健康", "正常"], "healthy normal variation"),
    (["其他病", "未知", "无法确定", "不确定"], "other unresolved conditions differential"),
    (["治疗", "管理", "用药", "防治"], "treatment management source policy"),
    (["诊断", "鉴别", "判断"], "diagnosis differential evidence thresholds"),
    (["图片", "照片", "图像", "叶面", "正面", "背面"], "image evidence leaf surface"),
    (["术语", "词汇"], "terminology controlled vocabulary"),
    (["结构", "解剖", "叶片"], "grape leaf anatomy"),
    (["数据", "数据集"], "data dataset memory"),
    (["标注", "标签"], "label labeling annotation"),
    (["流程", "pipeline"], "workflow pipeline"),
    (["schema", "模式"], "schema layer envelope"),
    (["wiki", "知识库"], "wiki knowledge base"),
    (["agent", "代理"], "agent system"),
]

from src.single_model_wiki.core import (
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


DEFAULT_SESSION_DIR = REPO_ROOT / "sessions" / "frontier"


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
        "数据",
        "数据集",
        "采集",
        "导入",
        "标注",
        "标签",
        "审核",
        "训练数据",
    ]
    wiki_keywords = ["wiki", "source", "知识库", "来源", "资料", "文献", "参考"]
    grape_keywords = [
        "grape",
        "leaf",
        "powdery",
        "downy",
        "disease",
        "diagnosis",
        "葡萄",
        "叶片",
        "叶子",
        "白粉",
        "霜霉",
        "病害",
        "症状",
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
        "data_management": ["router", "chat_agent"],
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


def expand_query_for_retrieval(query: str) -> str:
    lower = query.lower()
    hints: List[str] = []
    for needles, hint in RETRIEVAL_QUERY_HINTS:
        if any(needle in lower for needle in needles) and hint not in hints:
            hints.append(hint)
    if not hints:
        return query
    return f"{query}\nRetrieval hints: {', '.join(hints)}"


def query_size_units(query: str) -> int:
    english_tokens = re.findall(r"[A-Za-z0-9_]+", query)
    cjk_chars = re.findall(r"[\u3400-\u9fff]", query)
    cjk_units = max(1, len(cjk_chars) // 2) if cjk_chars else 0
    return len(english_tokens) + cjk_units


def count_complexity_cues(query: str) -> int:
    lower = query.lower()
    count = 0
    for cue in COMPLEXITY_CUES:
        if re.search(r"[A-Za-z0-9]", cue):
            pattern = rf"(?<![A-Za-z0-9_]){re.escape(cue)}(?![A-Za-z0-9_])"
            if re.search(pattern, lower):
                count += 1
        elif cue in lower:
            count += 1
    return count


def infer_auto_selected_page_limit(
    *,
    query: str,
    route: Dict[str, Any] | None,
    catalog: Dict[str, Any],
    core_ids: Sequence[str],
) -> int:
    page_count = len(catalog.get("pages", []))
    if page_count <= 0:
        return 0

    task_type = str((route or {}).get("task_type") or "")
    limit = AUTO_SELECTED_PAGE_BASE_BY_TASK.get(task_type, 4)

    size_units = query_size_units(query)
    if size_units >= 18:
        limit += 1
    if size_units >= 36:
        limit += 1
    if size_units >= 70:
        limit += 2

    cue_count = count_complexity_cues(query)
    if cue_count:
        limit += min(3, cue_count)

    if re.search(r"[?？].*[?？]", query) or re.search(r"[,;；，、]\s*\S+", query):
        limit += 1
    if re.search(r"\b(vs|versus|and|or)\b", query.lower()):
        limit += 1

    # Auto mode keeps mandatory core context from crowding out pages selected
    # specifically for the current question.
    if core_ids:
        extra_slots = 1 if cue_count or size_units >= 12 else 0
        limit = max(limit, len(core_ids) + extra_slots)

    ceiling = min(page_count, AUTO_SELECTED_PAGE_CEILING)
    return max(0, min(limit, ceiling))


def resolve_selected_page_limit(
    *,
    requested_max_selected_files: int | None,
    query: str,
    route: Dict[str, Any] | None,
    catalog: Dict[str, Any],
    core_ids: Sequence[str],
) -> tuple[int, str]:
    page_count = len(catalog.get("pages", []))
    if requested_max_selected_files is not None:
        return max(0, min(requested_max_selected_files, page_count)), "manual"
    return (
        infer_auto_selected_page_limit(
            query=query,
            route=route,
            catalog=catalog,
            core_ids=core_ids,
        ),
        "auto",
    )


def select_pages_for_backend(
    *,
    query: str,
    backend: Any,
    selection_mode: str,
    max_selected_files: int | None,
    max_page_chars: int,
    wiki_dir: Path,
    catalog_dir: Path,
    route: Dict[str, Any] | None = None,
    core_paths: Sequence[str] = (),
    selection_debug: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    catalog = load_or_build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)
    ids_by_path = {page["path"]: page["id"] for page in catalog.get("pages", [])}
    core_ids = []
    for path in core_paths:
        page_id = ids_by_path.get(path)
        if page_id and page_id not in core_ids:
            core_ids.append(page_id)

    selection_query = expand_query_for_retrieval(query)
    selected_page_limit, selected_page_limit_source = resolve_selected_page_limit(
        requested_max_selected_files=max_selected_files,
        query=query,
        route=route,
        catalog=catalog,
        core_ids=core_ids,
    )

    if selection_mode == "none":
        if selection_debug is not None:
            selection_debug.update(
                {
                    "selected_page_limit": 0,
                    "selected_page_limit_source": "none",
                    "catalog_pages": len(catalog.get("pages", [])),
                    "core_page_count": len(core_ids),
                    "retrieval_hints_added": selection_query != query,
                }
            )
        return []
    elif selection_mode == "full":
        if selection_debug is not None:
            selection_debug.update(
                {
                    "selected_page_limit": len(catalog.get("pages", [])),
                    "selected_page_limit_source": "full",
                    "catalog_pages": len(catalog.get("pages", [])),
                    "core_page_count": len(core_ids),
                    "retrieval_hints_added": selection_query != query,
                }
            )
        return read_all_pages(catalog=catalog, wiki_dir=wiki_dir, max_page_chars=max_page_chars)
    elif selection_mode == "keyword":
        selected_ids = select_pages_keyword_fallback(
            selection_query,
            catalog=catalog,
            max_selected_files=selected_page_limit,
        )
    elif selection_mode == "model":
        prompt = f"""You are selecting GopherEye context pages for an agent workflow.

Return ONLY a JSON array of page IDs.
Select the smallest sufficient set for the user request.
This turn's page budget is {selected_page_limit} IDs. Use fewer when the question is simple.

User/session query:
{selection_query}

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
                selection_query,
                catalog=catalog,
                max_selected_files=selected_page_limit,
            )
    else:
        raise ValueError(f"Unsupported selection_mode: {selection_mode}")

    selected_ids = core_ids + [page_id for page_id in selected_ids if page_id not in core_ids]
    selected_ids = selected_ids[:selected_page_limit]
    if selection_debug is not None:
        selection_debug.update(
            {
                "selected_page_limit": selected_page_limit,
                "selected_page_limit_source": selected_page_limit_source,
                "catalog_pages": len(catalog.get("pages", [])),
                "core_page_count": len(core_ids),
                "retrieval_hints_added": selection_query != query,
            }
        )
    return read_pages_by_id(
        selected_ids,
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

Return ONLY valid JSON with this compact top-level shape:
{{
  "assistant_message": "short app-ready English answer to the user",
  "memory_update": {{
    "summary": "compact memory of the session so far",
    "user_goal": null,
    "current_diagnosis": null,
    "image_observations": [
      {{
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
      }}
    ],
    "evidence_present": [],
    "evidence_missing": [],
    "diagnosis_verdict": "possible_not_confirmed",
    "next_image_need": null,
    "nonblocking_limitations": [],
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
- For data-management questions, chat_agent can explain how to collect,
  ingest, validate, store, audit, and evaluate data. It must not run or mutate
  the independent GopherEye Data Agent workspace.

Rules:
- Write assistant_message in English only.
- Stay within grape leaf diagnosis and GopherEye project behavior.
- For botanical diagnosis, follow the selected wiki procedure pages for leaf
  identity, diagnostic visibility, surface assessment, evidence sufficiency,
  front/back comparison, differential diagnosis, and next-image requests.
- Do not request the opposite leaf surface automatically. Ask for another side
  only when it resolves a specific diagnostic uncertainty.
- If one surface already shows high-signal powdery mildew or downy mildew
  features, diagnose from that surface and set recommended_next_image to null or
  none.
- Treat lighting, shadows, angle, and partial occlusion as nonblocking unless
  they prevent inspection of the relevant leaf features.
- Do not recommend treatment unless a reviewed management page is included.
- If images are attached, inspect pixels and output one image_observations item
  per inspected attached image. Use image_order from the attached image manifest.
- If no image pixels are attached, rely only on memory, transcript, selected context pages, and user text.
- Do not output known_image_updates, visual_intakes, image_quality objects,
  side_assessment objects, fine_visual_features objects, candidate_diseases
  objects, evidence_sufficiency, single_surface_assessment, recommended_next_image,
  or any ID/timestamp/source fields. App code expands compact observations into
  the persisted schema.
- Use only image_observations compact fields. Keep lists short: evidence lists
  max 5 items, findings max 3 sentences, quality_notes max 2 items,
  candidate_labels max 2 items, candidate_supporting_evidence max 2 items.
- quality_overall must be good, usable_with_caution, or unusable.
- quality_issues should use blurry, dark, overexposed, poor_angle, occluded,
  low_resolution, or duplicate.
- diagnostic_impact must be none, minor_nonblocking, or blocks_symptom_inspection.
- findings must combine structure, symptoms, locations, and fine diagnostic
  texture into readable natural-language sentences. Do not split them into
  visible_structures, visible_symptoms, symptom_locations, symptom_notes,
  structure_notes, or feature_notes; app code extracts canonical tags where useful.
- candidate_labels should be disease names as short strings. candidate_confidence
  must be low, moderate, high, very_high, or unknown.
- next_image_need must be null, close_up_same_surface, opposite_surface,
  adaxial_surface, or abaxial_surface.
- diagnosis_verdict should be confirmed, possible_not_confirmed, insufficient,
  or uncertain.
- Do not create or modify session_id, turn_id, image_id, image_path,
  image_uri, image_role, visual_intake_id, created_at, updated_at,
  first_seen_turn_id, last_seen_turn_id, or source fields.
- Do not output agent_trace. Route, selected agent path, and context metadata are
  recorded by app code outside the model JSON.
- Use canonical values when obvious, and put natural-language botanical detail in
  findings, quality_notes, evidence_present, evidence_missing, or intake_summary.

Model profile:
{profile_name}

Route:
{json.dumps(route, ensure_ascii=False, indent=2)}

Current short-term memory JSON:
(compact view; code-owned IDs, timestamps, and full schema objects are omitted)
{json.dumps(wiki_chat.compact_memory_for_prompt(session.get("short_term_memory", wiki_chat.default_memory())), ensure_ascii=False, indent=2)}

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
    max_selected_files: int | None = None,
    max_page_chars: int = 12000,
    recent_turns: int = 8,
    max_output_tokens: int = 2400,
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
    page_selection: Dict[str, Any] = {}
    pages = select_pages_for_backend(
        query=selection_query,
        backend=backend,
        selection_mode=selection_mode,
        max_selected_files=max_selected_files,
        max_page_chars=max_page_chars,
        wiki_dir=context["root_dir"],
        catalog_dir=context["catalog_dir"],
        route=route,
        core_paths=core_context_paths_for_route(route, context["label"]),
        selection_debug=page_selection,
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
            max_output_tokens=max(max_output_tokens, 2400),
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
        "page_selection": page_selection,
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
        "page_selection": page_selection,
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
