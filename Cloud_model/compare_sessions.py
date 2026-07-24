from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def brief_turns(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    messages = session.get("messages", [])
    turns = session.get("turns", [])
    assistant_by_turn = {
        msg.get("turn_id"): msg.get("content", "")
        for msg in messages
        if msg.get("role") == "assistant"
    }
    for turn in turns:
        assistant_turn_id = turn.get("assistant_turn_id")
        rows.append(
            {
                "user_turn_id": turn.get("user_turn_id"),
                "assistant_turn_id": assistant_turn_id,
                "assistant_message": assistant_by_turn.get(assistant_turn_id, ""),
                "attached_images": turn.get("attached_image_refs", []),
                "missing_images": turn.get("missing_image_refs", []),
                "selected_pages": [page.get("path") for page in turn.get("selected_pages", [])],
                "parsed_json": turn.get("parsed_json"),
            }
        )
    return rows


def memory_brief(session: Dict[str, Any]) -> Dict[str, Any]:
    memory = session.get("short_term_memory", {})
    return {
        "summary": memory.get("summary"),
        "current_diagnosis": memory.get("current_diagnosis"),
        "evidence_present": memory.get("evidence_present", []),
        "evidence_missing": memory.get("evidence_missing", []),
        "recommended_next_image": memory.get("recommended_next_image"),
        "known_image_count": len(memory.get("known_images", [])),
        "visual_intake_count": len(memory.get("visual_intakes", [])),
        "allowed_follow_up_questions": memory.get("allowed_follow_up_questions", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare a local Wiki2 session with a Cloud_model session.")
    parser.add_argument("--local-session", required=True)
    parser.add_argument("--cloud-session", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    local = load_json(Path(args.local_session))
    cloud = load_json(Path(args.cloud_session))

    result = {
        "local": {
            "session_id": local.get("session_id"),
            "provider": local.get("provider"),
            "model": local.get("model"),
            "memory": memory_brief(local),
            "turns": brief_turns(local),
        },
        "cloud": {
            "session_id": cloud.get("session_id"),
            "provider": cloud.get("provider"),
            "model": cloud.get("model"),
            "memory": memory_brief(cloud),
            "turns": brief_turns(cloud),
        },
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    for label in ["local", "cloud"]:
        item = result[label]
        print(f"## {label.upper()}")
        print(f"session_id: {item['session_id']}")
        print(f"provider: {item['provider']}")
        print(f"model: {item['model']}")
        print("memory:")
        print(json.dumps(item["memory"], ensure_ascii=False, indent=2))
        print("turns:")
        for turn in item["turns"]:
            print(f"- user_turn_id={turn['user_turn_id']} assistant_turn_id={turn['assistant_turn_id']}")
            print(f"  assistant_message: {turn['assistant_message']}")
            print(f"  attached_images: {len(turn['attached_images'])}")
            for image in turn["attached_images"]:
                print(f"    - {image}")
            if turn["missing_images"]:
                print("  missing_images:")
                for image in turn["missing_images"]:
                    print(f"    - {image}")
            print(f"  parsed_json: {turn['parsed_json']}")
            print(f"  selected_pages: {turn['selected_pages']}")
        print("")


if __name__ == "__main__":
    main()

