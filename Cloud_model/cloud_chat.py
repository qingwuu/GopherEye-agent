from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence
from urllib.parse import unquote, urlparse


CLOUD_DIR = Path(__file__).resolve().parent
REPO_ROOT = CLOUD_DIR.parent
APP_DIR = REPO_ROOT

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import chat as wiki_chat  # noqa: E402

DEFAULT_CATALOG_DIR = wiki_chat.DEFAULT_CATALOG_DIR
DEFAULT_WIKI_DIR = wiki_chat.DEFAULT_WIKI_DIR
build_chat_prompt = wiki_chat.build_chat_prompt
collect_image_records_for_context = wiki_chat.collect_image_records_for_context
default_memory = wiki_chat.default_memory
list_sessions = wiki_chat.list_sessions
load_session = wiki_chat.load_session
parse_json_object = wiki_chat.parse_json_object
print_chat_result = wiki_chat.print_chat_result
register_image_refs = wiki_chat.register_image_refs
resolve_vlm_image_refs = wiki_chat.resolve_vlm_image_refs
save_session = wiki_chat.save_session
select_pages = wiki_chat.select_pages
from src.single_model_wiki.core import now_utc, safe_print, timestamp_id  # noqa: E402


DEFAULT_SESSION_DIR = CLOUD_DIR / "sessions"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def default_id_history() -> Dict[str, Any]:
    if hasattr(wiki_chat, "default_id_history"):
        return wiki_chat.default_id_history()
    return {"images": {}, "visual_intakes": {}, "counters": {}, "events": []}


def hydrate_id_history_from_session(session: Dict[str, Any]) -> None:
    if hasattr(wiki_chat, "hydrate_id_history_from_session"):
        wiki_chat.hydrate_id_history_from_session(session)


def normalize_memory_compatible(
    value: Any,
    previous: Dict[str, Any],
    *,
    session: Dict[str, Any],
    attached_image_manifest: Sequence[Dict[str, Any]],
    turn_id: int,
) -> Dict[str, Any]:
    try:
        return wiki_chat.normalize_memory(
            value,
            previous,
            session=session,
            attached_image_manifest=attached_image_manifest,
            turn_id=turn_id,
        )
    except TypeError:
        return wiki_chat.normalize_memory(value, previous)


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    load_dotenv(CLOUD_DIR / ".env")
    load_dotenv(APP_DIR / ".env")
    load_dotenv()


def file_uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"Not a file URI: {uri}")
    return Path(unquote(parsed.path))


def image_ref_to_data_url(image_ref: str) -> str:
    if image_ref.startswith(("http://", "https://", "data:")):
        return image_ref

    if image_ref.startswith("file://"):
        path = file_uri_to_path(image_ref)
    else:
        path = Path(image_ref).expanduser()

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Cannot encode missing image for OpenAI API: {image_ref}")

    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_responses_content(prompt: str, image_refs: Sequence[str]) -> List[Dict[str, Any]]:
    content: List[Dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for image_ref in image_refs:
        content.append(
            {
                "type": "input_image",
                "image_url": image_ref_to_data_url(image_ref),
            }
        )
    return content


def build_chat_content(prompt: str, image_refs: Sequence[str]) -> List[Dict[str, Any]]:
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image_ref in image_refs:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_ref_to_data_url(image_ref)},
            }
        )
    return content


def answer_openai_vision(
    prompt: str,
    *,
    model: str,
    image_refs: Sequence[str],
    max_new_tokens: int,
) -> str:
    load_dotenv_if_available()

    from openai import OpenAI

    client = OpenAI()

    # Prefer the Responses API. Fall back to Chat Completions so this comparison
    # can run on older OpenAI Python SDK/API combinations.
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": build_responses_content(prompt, image_refs),
                }
            ],
            max_output_tokens=max_new_tokens,
        )
        text = getattr(response, "output_text", None)
        if text:
            return text.strip()
    except Exception as exc:
        responses_error = exc
    else:
        responses_error = None

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": build_chat_content(prompt, image_refs),
                }
            ],
            max_tokens=max_new_tokens,
            temperature=0,
        )
    except Exception as chat_exc:
        if responses_error is not None:
            raise RuntimeError(
                f"OpenAI Responses API failed with: {responses_error}\n"
                f"Chat Completions fallback failed with: {chat_exc}"
            ) from chat_exc
        raise

    return response.choices[0].message.content.strip()


def run_cloud_chat_turn(
    user_message: str,
    *,
    session_id: str,
    model: str,
    selection_mode: str = "keyword",
    selection_model: str | None = None,
    image_refs: Sequence[str] = (),
    max_selected_files: int = 6,
    max_page_chars: int = 12000,
    recent_turns: int = 8,
    max_new_tokens: int = 900,
    image_context: str = "session",
    max_attached_images: int = 8,
    session_dir: Path = DEFAULT_SESSION_DIR,
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> Dict[str, Any]:
    provider = "openai-cloud"
    selection_model = selection_model or model
    session = load_session(session_id, session_dir=session_dir, provider=provider, model=model)
    session["provider"] = provider
    session["model"] = model
    hydrate_id_history_from_session(session)

    user_turn_id = len(session.get("messages", [])) + 1
    user_row = {
        "turn_id": user_turn_id,
        "role": "user",
        "content": user_message,
        "created_at": now_utc(),
        "image_refs": list(image_refs),
    }
    session.setdefault("messages", []).append(user_row)
    register_image_refs(session, image_refs, turn_id=user_turn_id)

    pages = select_pages(
        session=session,
        user_message=user_message,
        selection_mode=selection_mode,
        provider="openai",
        model=selection_model,
        max_selected_files=max_selected_files,
        max_page_chars=max_page_chars,
        wiki_dir=wiki_dir,
        catalog_dir=catalog_dir,
    )
    requested_image_records = collect_image_records_for_context(
        session,
        image_refs,
        image_context=image_context,
        max_attached_images=max_attached_images,
    )
    attached_image_refs, missing_image_refs, attached_image_manifest = resolve_vlm_image_refs(
        requested_image_records,
        session_dir=session_dir,
        session_id=session_id,
    )

    prompt = build_chat_prompt(
        session=session,
        user_message=user_message,
        image_refs=image_refs,
        pages=pages,
        recent_turns=recent_turns,
        attached_image_manifest=attached_image_manifest,
        missing_image_refs=missing_image_refs,
    )
    raw = answer_openai_vision(
        prompt,
        model=model,
        image_refs=attached_image_refs,
        max_new_tokens=max_new_tokens,
    )
    parsed = parse_json_object(raw)

    if parsed and isinstance(parsed.get("assistant_message"), str):
        assistant_message = parsed["assistant_message"].strip()
        memory_update = parsed.get("memory_update")
        if not isinstance(memory_update, dict):
            memory_update = parsed.get("short_term_memory")
        session["short_term_memory"] = normalize_memory_compatible(
            memory_update,
            session.get("short_term_memory", default_memory()),
            session=session,
            attached_image_manifest=attached_image_manifest,
            turn_id=user_turn_id,
        )
    else:
        assistant_message = raw.strip()
    if wiki_chat.contains_cjk(assistant_message):
        assistant_message = (
            "I could not produce an English response for this turn. "
            "Please try again, or upload a clearer image if this is a diagnosis request."
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
        "provider": provider,
        "model": model,
        "selection_model": selection_model,
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
        "parsed_json": parsed is not None,
        "created_at": now_utc(),
    }
    session.setdefault("turns", []).append(turn_meta)
    path = save_session(session, session_dir=session_dir)

    return {
        "session_path": str(path),
        "session_id": session_id,
        "provider": provider,
        "model": model,
        "assistant_message": assistant_message,
        "short_term_memory": session["short_term_memory"],
        "id_history": session.get("id_history", default_id_history()),
        "selected_pages": turn_meta["selected_pages"],
        "attached_image_refs": attached_image_refs,
        "attached_image_manifest": attached_image_manifest,
        "missing_image_refs": missing_image_refs,
        "parsed_json": parsed is not None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OpenAI cloud-model version of GopherEye wiki chat.")
    parser.add_argument("message", nargs="?", help="User message for this turn.")
    parser.add_argument("--session-id", default=None, help="Reuse this ID to continue a cloud session.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--selection-model", default=None)
    parser.add_argument("--selection-mode", choices=["model", "full", "keyword", "none"], default="keyword")
    parser.add_argument("--image-ref", action="append", default=[], help="Optional image path/URL to remember in the turn.")
    parser.add_argument("--image-context", choices=["session", "current", "none"], default="session")
    parser.add_argument("--max-attached-images", type=int, default=8)
    parser.add_argument("--max-selected-files", type=int, default=6)
    parser.add_argument("--max-page-chars", type=int, default=12000)
    parser.add_argument("--recent-turns", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=900)
    parser.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR))
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument("--catalog-dir", default=str(DEFAULT_CATALOG_DIR))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list-sessions", action="store_true")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if args.list_sessions:
        for path in list_sessions(session_dir):
            safe_print(str(path))
        return

    if not args.message:
        raise SystemExit("Provide a message, or use --list-sessions.")

    session_id = args.session_id or f"cloud_session_{timestamp_id()}"
    result = run_cloud_chat_turn(
        args.message,
        session_id=session_id,
        model=args.model,
        selection_model=args.selection_model,
        selection_mode=args.selection_mode,
        image_refs=args.image_ref,
        max_selected_files=args.max_selected_files,
        max_page_chars=args.max_page_chars,
        recent_turns=args.recent_turns,
        max_new_tokens=args.max_new_tokens,
        image_context=args.image_context,
        max_attached_images=args.max_attached_images,
        session_dir=session_dir,
        wiki_dir=Path(args.wiki_dir),
        catalog_dir=Path(args.catalog_dir),
    )
    print_chat_result(result, as_json=args.json)


if __name__ == "__main__":
    main()
