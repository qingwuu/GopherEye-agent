from __future__ import annotations

import argparse
from pathlib import Path

from src.single_model_wiki.core import DEFAULT_RAW_DIR, copy_source, safe_print


def main():
    parser = argparse.ArgumentParser(description="Copy a raw source into the single-model wiki raw source store.")
    parser.add_argument("source_path")
    parser.add_argument("--source-type", default="note")
    parser.add_argument("--title", default=None)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    args = parser.parse_args()

    row = copy_source(Path(args.source_path), args.source_type, args.title, raw_dir=Path(args.raw_dir))
    safe_print(f"Added source {row['source_id']}: {row['stored_path']}")


if __name__ == "__main__":
    main()

