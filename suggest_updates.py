from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.single_model_wiki.core import DEFAULT_DRAFT_DIR, suggest_updates, safe_print


def main():
    parser = argparse.ArgumentParser(description="Generate a single-model wiki update draft from a raw source.")
    parser.add_argument("source_path")
    parser.add_argument("--provider", choices=["transformers", "openai"], default="transformers")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "Qwen/Qwen2.5-7B-Instruct"))
    parser.add_argument("--max-selected-files", type=int, default=6)
    parser.add_argument("--max-source-chars", type=int, default=24000)
    parser.add_argument("--max-page-chars", type=int, default=12000)
    parser.add_argument("--max-new-tokens", type=int, default=1200)
    parser.add_argument("--output-dir", default=str(DEFAULT_DRAFT_DIR))
    args = parser.parse_args()

    out_path = suggest_updates(
        Path(args.source_path),
        provider=args.provider,
        model=args.model,
        max_selected_files=args.max_selected_files,
        max_source_chars=args.max_source_chars,
        max_page_chars=args.max_page_chars,
        max_new_tokens=args.max_new_tokens,
        output_dir=Path(args.output_dir),
    )
    safe_print(f"Wrote draft update: {out_path}")


if __name__ == "__main__":
    main()

