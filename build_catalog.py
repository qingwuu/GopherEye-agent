from __future__ import annotations

import argparse
from pathlib import Path

from src.single_model_wiki.core import DEFAULT_CATALOG_DIR, DEFAULT_WIKI_DIR, build_catalog, safe_print


def main():
    parser = argparse.ArgumentParser(description="Build a lightweight catalog for the single-model wiki.")
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument("--catalog-dir", default=str(DEFAULT_CATALOG_DIR))
    args = parser.parse_args()

    catalog = build_catalog(wiki_dir=Path(args.wiki_dir), catalog_dir=Path(args.catalog_dir))
    safe_print(f"Built catalog with {catalog['num_pages']} pages at {args.catalog_dir}")


if __name__ == "__main__":
    main()

