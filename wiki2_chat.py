from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.gophereye_runtime.utils import safe_print
    from Frontier_model.frontier_agents.wiki2_pipeline import (
        DEFAULT_WIKI2_SESSION_DIR,
        run_wiki2_turn,
    )
    from Frontier_model.frontier_agents.wiki2_retrieval import (
        DEFAULT_WIKI2_CATALOG_DIR,
        DEFAULT_WIKI2_DIR,
    )
else:
    from src.gophereye_runtime.utils import safe_print
    from .Frontier_model.frontier_agents.wiki2_pipeline import DEFAULT_WIKI2_SESSION_DIR, run_wiki2_turn
    from .Frontier_model.frontier_agents.wiki2_retrieval import DEFAULT_WIKI2_CATALOG_DIR, DEFAULT_WIKI2_DIR


def parse_auto_int(value: str) -> int | str:
    if str(value).strip().lower() == "auto":
        return "auto"
    return int(value)


def parse_auto_original_int(value: str) -> int | str:
    text = str(value).strip().lower()
    if text in {"auto", "original", "full"}:
        return text
    return int(value)


def compact_page_paths(pages: Any) -> list[str]:
    if not isinstance(pages, list):
        return []
    return [
        page.get("path") if isinstance(page, dict) else str(page)
        for page in pages
    ]


def limited_strings(values: Any, *, limit: int = 10) -> list[str]:
    if not isinstance(values, list):
        return []
    strings = [str(value) for value in values if value is not None]
    if len(strings) <= limit:
        return strings
    return [*strings[:limit], f"...(+{len(strings) - limit})"]


def joined_strings(values: Any, *, limit: int = 10) -> str | None:
    strings = limited_strings(values, limit=limit)
    return ", ".join(strings) if strings else None


def drop_empty(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def compact_usage(usage: Any) -> Dict[str, Any] | None:
    if not isinstance(usage, dict):
        return None
    input_details = usage.get("input_tokens_details") if isinstance(usage.get("input_tokens_details"), dict) else {}
    output_details = usage.get("output_tokens_details") if isinstance(usage.get("output_tokens_details"), dict) else {}
    payload: Dict[str, Any] = {
        "input_tokens": usage.get("input_tokens"),
        "cached_tokens": input_details.get("cached_tokens"),
        "cache_write_tokens": input_details.get("cache_write_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_tokens": output_details.get("reasoning_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }
    stages = usage.get("stages")
    if isinstance(stages, list):
        payload["stages"] = [
            {
                "stage": item.get("stage"),
                **(compact_usage(item.get("usage")) or {}),
            }
            for item in stages
            if isinstance(item, dict)
        ]
    return drop_empty(payload)


def compact_prompt_metrics(metrics: Any) -> Dict[str, Any]:
    if not isinstance(metrics, dict):
        return {}
    keys = [
        "pipeline_mode",
        "wiki2_context_chars",
        "selected_detailed_pages",
        "attached_image_count",
        "stage1_prompt_chars",
        "stage3_prompt_chars",
        "total_text_prompt_chars",
        "stage1_wiki2_context_chars",
        "stage2_wiki2_context_chars",
        "stage1_attached_image_count",
        "stage3_attached_image_count",
        "stage1_image_max_edge",
    ]
    return {key: metrics.get(key) for key in keys if metrics.get(key) is not None}


def compact_resolved_parameters(parameters: Any) -> Dict[str, Any]:
    if not isinstance(parameters, dict):
        return {}
    keys = [
        "pipeline_mode_resolved",
        "stage1_image_max_edge",
        "stage2_max_detailed_pages",
        "stage2_max_context_chars",
        "stage3_images",
        "image_context",
        "max_attached_images",
    ]
    return {key: parameters.get(key) for key in keys if parameters.get(key) is not None}


def compact_route(route: Any) -> Dict[str, Any]:
    if not isinstance(route, dict):
        return {}
    selected_agent_path = route.get("selected_agent_path")
    return {
        "task_type": route.get("task_type"),
        "needs_vision": route.get("needs_vision"),
        "selected_agent_path": " > ".join(selected_agent_path) if isinstance(selected_agent_path, list) else selected_agent_path,
    }


def compact_visual_signal_vector(vector: Any) -> Dict[str, Any]:
    if not isinstance(vector, dict):
        return {}
    surfaces = []
    for item in vector.get("visible_surfaces") or []:
        if isinstance(item, dict):
            surfaces.append(f"{item.get('image_order')}:{item.get('surface')}/{item.get('confidence')}")
    candidate_hints = []
    for item in vector.get("candidate_hints") or []:
        if isinstance(item, dict):
            entity_id = item.get("entity_id") or item.get("disease_id")
            roles = joined_strings(item.get("needed_detail_roles"), limit=6)
            candidate_hints.append(f"{entity_id}:{item.get('support')} roles={roles}")
    return drop_empty({
        "diagnostic_stage": vector.get("diagnostic_stage"),
        "plant_part": vector.get("plant_part"),
        "visible_surfaces": surfaces,
        "positive_signals": joined_strings(vector.get("positive_signals"), limit=12),
        "negative_signals": joined_strings(vector.get("negative_signals"), limit=12),
        "pattern_signals": joined_strings(vector.get("pattern_signals"), limit=12),
        "candidate_hints": candidate_hints,
        "evidence_missing": joined_strings(vector.get("evidence_missing"), limit=8),
        "next_retrieval_focus": joined_strings(vector.get("next_retrieval_focus"), limit=8),
    })


def compact_retrieval_trace(trace: Any) -> Dict[str, Any]:
    if not isinstance(trace, dict):
        return {}
    terminal_plan = trace.get("terminal_path_plan") if isinstance(trace.get("terminal_path_plan"), list) else []
    candidates = []
    for item in terminal_plan:
        if not isinstance(item, dict):
            continue
        candidates.append(drop_empty({
            "entity_id": item.get("entity_id") or item.get("disease_id"),
            "status": item.get("status"),
            "support": item.get("support"),
            "score": item.get("score"),
            "roles": joined_strings(item.get("roles"), limit=6),
            "support_signals": joined_strings(item.get("support_signal_matches"), limit=8),
            "weaken_signals": joined_strings(item.get("weaken_signal_matches"), limit=8),
        }))

    decision = trace.get("retrieval_decision") if isinstance(trace.get("retrieval_decision"), dict) else {}
    payload: Dict[str, Any] = {
        "retrieval_stage": trace.get("retrieval_stage"),
        "signal_driven": trace.get("signal_driven"),
        "include_parent_pages": trace.get("include_parent_pages"),
        "selected_detailed_count": trace.get("selected_detailed_count"),
        "max_detailed_pages": trace.get("max_detailed_pages"),
        "max_context_chars": trace.get("max_context_chars"),
        "selected_parent_page_count": len(trace.get("selected_parent_pages") or []),
        "terminal_candidates": candidates,
        "retrieval_decision": decision.get("retrieval_decision"),
        "retrieval_reason": decision.get("retrieval_reason"),
    }
    return drop_empty(payload)


def compact_candidate_lines(trace_summary: Dict[str, Any]) -> list[str]:
    lines = []
    for item in trace_summary.get("terminal_candidates") or []:
        if not isinstance(item, dict):
            continue
        parts = [
            f"{item.get('entity_id')}:{item.get('status')}/{item.get('support')}",
            f"score={item.get('score')}",
        ]
        if item.get("roles"):
            parts.append(f"roles={item.get('roles')}")
        if item.get("support_signals"):
            parts.append(f"support={item.get('support_signals')}")
        if item.get("weaken_signals"):
            parts.append(f"weaken={item.get('weaken_signals')}")
        lines.append(" | ".join(parts))
    return lines


def compact_model_image_lines(manifest: Any) -> list[str]:
    if not isinstance(manifest, list):
        return []

    def size_text(size: Any) -> str:
        if isinstance(size, list) and len(size) == 2:
            return f"{size[0]}x{size[1]}"
        return str(size)

    lines = []
    for item in manifest:
        if not isinstance(item, dict):
            continue
        preprocessing = item.get("model_image_preprocessing") if isinstance(item.get("model_image_preprocessing"), dict) else {}
        details = [str(preprocessing.get("status"))] if preprocessing.get("status") else []
        if preprocessing.get("max_edge"):
            details.append(f"max_edge={preprocessing.get('max_edge')}")
        if preprocessing.get("jpeg_quality"):
            details.append(f"q={preprocessing.get('jpeg_quality')}")
        lines.append(
            f"{item.get('image_order')}: "
            f"{size_text(item.get('original_size'))}->{size_text(item.get('model_size'))}"
            f"{' ' + ', '.join(details) if details else ''}"
        )
    return lines


def compact_result(result: Dict[str, Any]) -> Dict[str, Any]:
    retrieval = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    stages = result.get("stages") if isinstance(result.get("stages"), dict) else {}
    stage1 = stages.get("stage1_visual_intake") if isinstance(stages.get("stage1_visual_intake"), dict) else {}
    model_image_manifest = stage1.get("model_image_manifest") if isinstance(stage1.get("model_image_manifest"), list) else []
    trace_summary = compact_retrieval_trace(retrieval.get("retrieval_trace"))
    return {
        "answer": result.get("assistant_message"),
        "session": {
            "session_id": result.get("session_id"),
            "session_path": result.get("session_path"),
            "profile": result.get("model_profile"),
            "model": result.get("model"),
            "wiki_system": result.get("wiki_system"),
        },
        "pipeline_mode": result.get("pipeline_mode"),
        "parameters": compact_resolved_parameters(result.get("resolved_parameters")),
        "route": compact_route(result.get("route")),
        "retrieval": {
            "selected_pages": compact_page_paths(result.get("selected_pages")),
            "context_chars": retrieval.get("context_chars"),
            "selected_detailed_count": trace_summary.get("selected_detailed_count"),
            "candidates": compact_candidate_lines(trace_summary),
        },
        "stage1": {
            "context_chars": (stage1.get("retrieval") or {}).get("context_chars"),
            "signals": compact_visual_signal_vector(stage1.get("visual_signal_vector")),
            "model_images": compact_model_image_lines(model_image_manifest),
            "usage": compact_usage(stage1.get("usage")),
        },
        "prompt_metrics": compact_prompt_metrics(result.get("prompt_metrics")),
        "usage": compact_usage(result.get("usage")),
        "envelope_valid": result.get("envelope_valid"),
        "envelope_validation_errors": result.get("envelope_validation_errors"),
    }


def print_result(result: Dict[str, Any], *, as_json: bool, detail: str) -> None:
    if as_json:
        payload = result if detail == "full" else compact_result(result)
        safe_print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    safe_print(result.get("assistant_message") or "")
    safe_print("")
    safe_print(f"session_id: {result['session_id']}")
    safe_print(f"session_path: {result['session_path']}")
    safe_print(f"profile: {result['model_profile']}")
    safe_print(f"model: {result['model']}")
    safe_print(f"wiki_system: {result['wiki_system']}")
    safe_print(f"pipeline_mode: {result.get('pipeline_mode')}")
    safe_print(f"task_type: {result['route']['task_type']}")
    if result.get("resolved_parameters"):
        safe_print("resolved_parameters:")
        safe_print(json.dumps(result["resolved_parameters"], ensure_ascii=False, indent=2))
    metrics = result.get("prompt_metrics") or {}
    safe_print(
        "prompt_metrics: "
        f"wiki2_context_chars={metrics.get('wiki2_context_chars')} "
        f"selected_detailed_pages={metrics.get('selected_detailed_pages')} "
        f"attached_image_count={metrics.get('attached_image_count')}"
    )
    safe_print("selected_wiki2_pages:")
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
    parser = argparse.ArgumentParser(description="Run the independent GopherEye wiki2 prompt/retrieval pipeline.")
    parser.add_argument("message", nargs="?", help="User message for this wiki2 turn.")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--profile", default=None, help="Model profile from models.example.json or a custom config.")
    parser.add_argument("--config", default=None, help="Path to a model config JSON.")
    parser.add_argument("--image-ref", action="append", default=[])
    parser.add_argument("--image-context", choices=["current", "session", "none"], default="current")
    parser.add_argument("--pipeline-mode", choices=["auto", "staged", "single"], default="auto")
    parser.add_argument("--max-attached-images", type=parse_auto_int, default="auto")
    parser.add_argument("--max-detailed-pages", type=parse_auto_int, default="auto")
    parser.add_argument("--max-context-chars", type=parse_auto_int, default="auto")
    parser.add_argument("--max-children-per-parent", type=parse_auto_int, default="auto")
    parser.add_argument("--include-parent-pages", choices=["never", "debug", "fallback"], default="never")
    parser.add_argument("--recent-turns", type=parse_auto_int, default="auto")
    parser.add_argument("--max-output-tokens", type=parse_auto_int, default="auto")
    parser.add_argument("--stage1-max-context-chars", type=parse_auto_int, default="auto")
    parser.add_argument("--stage1-max-output-tokens", type=parse_auto_int, default="auto")
    parser.add_argument("--stage1-image-max-edge", type=parse_auto_original_int, default="auto")
    parser.add_argument("--stage2-max-detailed-pages", type=parse_auto_int, default="auto")
    parser.add_argument("--stage2-max-context-chars", type=parse_auto_int, default="auto")
    parser.add_argument("--stage3-max-output-tokens", type=parse_auto_int, default="auto")
    parser.add_argument("--stage3-images", action="store_true")
    parser.add_argument("--repair-envelope", action="store_true")
    parser.add_argument("--session-dir", default=str(DEFAULT_WIKI2_SESSION_DIR))
    parser.add_argument("--wiki2-dir", default=str(DEFAULT_WIKI2_DIR))
    parser.add_argument("--wiki2-catalog-dir", default=str(DEFAULT_WIKI2_CATALOG_DIR))
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--json-detail",
        choices=["compact", "full"],
        default="compact",
        help="compact keeps terminal output short; full prints the complete debug envelope.",
    )
    args = parser.parse_args()

    if not args.message:
        raise SystemExit("Provide a message.")

    result = run_wiki2_turn(
        args.message,
        session_id=args.session_id,
        profile_name=args.profile,
        config_path=args.config,
        image_refs=args.image_ref,
        pipeline_mode=args.pipeline_mode,
        max_detailed_pages=args.max_detailed_pages,
        max_context_chars=args.max_context_chars,
        max_children_per_parent=args.max_children_per_parent,
        include_parent_pages=args.include_parent_pages,
        recent_turns=args.recent_turns,
        max_output_tokens=args.max_output_tokens,
        stage1_max_context_chars=args.stage1_max_context_chars,
        stage1_max_output_tokens=args.stage1_max_output_tokens,
        stage1_image_max_edge=args.stage1_image_max_edge,
        stage2_max_detailed_pages=args.stage2_max_detailed_pages,
        stage2_max_context_chars=args.stage2_max_context_chars,
        stage3_max_output_tokens=args.stage3_max_output_tokens,
        stage3_images=args.stage3_images,
        image_context=args.image_context,
        max_attached_images=args.max_attached_images,
        repair_envelope=args.repair_envelope,
        session_dir=Path(args.session_dir),
        wiki2_dir=Path(args.wiki2_dir),
        wiki2_catalog_dir=Path(args.wiki2_catalog_dir),
    )
    print_result(result, as_json=args.json, detail=args.json_detail)


if __name__ == "__main__":
    main()
