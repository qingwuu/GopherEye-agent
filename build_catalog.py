from __future__ import annotations

import argparse
from pathlib import Path

from src.single_model_wiki.core import DEFAULT_CATALOG_DIR, DEFAULT_WIKI_DIR, ROOT_DIR, build_catalog, safe_print


def normalize_catalog_dir(raw_catalog_dir: str, wiki_dir: Path) -> Path:
    """Recover common shell-escaped catalog paths such as catalogsystem."""
    catalog_dir = Path(raw_catalog_dir)
    if catalog_dir.is_absolute():
        return catalog_dir

    normalized = raw_catalog_dir.replace("\\", "/").strip("/")
    wiki_name = wiki_dir.name.lower()
    if normalized == "catalogsystem" and wiki_name == "system":
        return ROOT_DIR / "catalog" / "system"
    if normalized == "catalogwiki" and wiki_name == "wiki":
        return ROOT_DIR / "catalog" / "wiki"
    return catalog_dir


def main():
    parser = argparse.ArgumentParser(description="Build a lightweight catalog for the single-model wiki.")
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument("--catalog-dir", default=str(DEFAULT_CATALOG_DIR))
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    catalog_dir = normalize_catalog_dir(args.catalog_dir, wiki_dir)
    catalog = build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)
    safe_print(f"Built catalog with {catalog['num_pages']} pages at {catalog_dir}")


if __name__ == "__main__":
    main()
