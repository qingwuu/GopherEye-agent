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
    from .frontier_agents.wiki2_pipeline import DEFAULT_WIKI2_SESSION_DIR, run_wiki2_turn
from .frontier_agents.wiki2_retrieval import DEFAULT_WIKI2_CATALOG_DIR, DEFAULT_WIKI2_DIR


def parse_auto_int(value: str) -> int | str:
    if str(value).strip().lower() == "auto":
        return "auto"
    return int(value)


def parse_auto_original_int(value: str) -> int | str:
    text = str(value).strip().lower()
    if text in {"auto", "original", "full"}:
        return text
    return int(value)


def compact_result(result: Dict[str, Any]) -> Dict[str, Any]:
    retrieval = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    stages = result.get("stages") if isinstance(result.get("stages"), dict) else {}
    stage1 = stages.get("stage1_visual_intake") if isinstance(stages.get("stage1_visual_intake"), dict) else {}
    stage2 = stages.get("stage2_terminal_retrieval") if isinstance(stages.get("stage2_terminal_retrieval"), dict) else {}
    model_image_manifest = stage1.get("model_image_manifest") if isinstance(stage1.get("model_image_manifest"), list) else []
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
        "resolved_parameters": result.get("resolved_parameters"),
        "route": result.get("route"),
        "retrieval": {
            "selected_pages": [
                page.get("path") if isinstance(page, dict) else str(page)
                for page in result.get("selected_pages", [])
            ],
            "context_chars": retrieval.get("context_chars"),
            "trace": retrieval.get("retrieval_trace"),
        },
        "stages": {
            "stage1_visual_intake": {
                "selected_pages": [
                    page.get("path") if isinstance(page, dict) else str(page)
                    for page in ((stage1.get("retrieval") or {}).get("selected_pages") or [])
                ],
                "context_chars": (stage1.get("retrieval") or {}).get("context_chars"),
                "visual_signal_vector": stage1.get("visual_signal_vector"),
                "model_images": [
                    {
                        "image_order": item.get("image_order"),
                        "original_size": item.get("original_size"),
                        "model_size": item.get("model_size"),
                        "preprocessing": item.get("model_image_preprocessing"),
                    }
                    for item in model_image_manifest
                    if isinstance(item, dict)
                ],
                "usage": stage1.get("usage"),
            },
            "stage2_terminal_retrieval": {
                "selected_pages": [
                    page.get("path") if isinstance(page, dict) else str(page)
                    for page in ((stage2.get("retrieval") or {}).get("selected_pages") or [])
                ],
                "context_chars": (stage2.get("retrieval") or {}).get("context_chars"),
                "trace": (stage2.get("retrieval") or {}).get("retrieval_trace"),
            },
        },
        "prompt_metrics": result.get("prompt_metrics"),
        "usage": result.get("usage"),
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
    parser.add_argument("--json-detail", choices=["compact", "full"], default="compact")
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
