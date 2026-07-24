from __future__ import annotations

import argparse
import os

from src.single_model_wiki.core import ask, print_result


def main():
    parser = argparse.ArgumentParser(description="Ask the single-model GopherEye wiki.")
    parser.add_argument("question")
    parser.add_argument("--provider", choices=["transformers", "openai", "echo"], default="transformers")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "Qwen/Qwen2.5-7B-Instruct"))
    parser.add_argument("--selection-mode", choices=["model", "full", "keyword"], default="model")
    parser.add_argument("--max-selected-files", type=int, default=6)
    parser.add_argument("--max-page-chars", type=int, default=12000)
    parser.add_argument("--max-new-tokens", type=int, default=768)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = ask(
        args.question,
        provider=args.provider,
        model=args.model,
        selection_mode=args.selection_mode,
        max_selected_files=args.max_selected_files,
        max_page_chars=args.max_page_chars,
        max_new_tokens=args.max_new_tokens,
    )
    print_result(result, as_json=args.json)


if __name__ == "__main__":
    main()

