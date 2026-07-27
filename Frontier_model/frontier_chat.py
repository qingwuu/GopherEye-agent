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


def print_result(result: dict, *, as_json: bool) -> None:
    if as_json:
        safe_print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    safe_print(result["assistant_message"])
    safe_print("")
    safe_print(f"session_id: {result['session_id']}")
    safe_print(f"session_path: {result['session_path']}")
    safe_print(f"profile: {result['model_profile']}")
    safe_print(f"model: {result['model']}")
    safe_print(f"task_type: {result['route']['task_type']}")
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
    parser.add_argument("--max-selected-files", type=int, default=6)
    parser.add_argument("--max-page-chars", type=int, default=12000)
    parser.add_argument("--recent-turns", type=int, default=8)
    parser.add_argument("--max-output-tokens", type=int, default=2400)
    parser.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR))
    parser.add_argument("--json", action="store_true")
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
    print_result(result, as_json=args.json)


if __name__ == "__main__":
    main()
