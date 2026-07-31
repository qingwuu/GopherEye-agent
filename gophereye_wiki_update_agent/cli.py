from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict

from src.gophereye_runtime.utils import safe_print
from src.single_model_wiki.core import DEFAULT_CATALOG_DIR, DEFAULT_WIKI_DIR, build_catalog

from . import __version__
from .config import DEFAULT_CONFIG_PATH, load_model_config
from .core import DEFAULT_PRIORITY_SOURCES_PATH, DEFAULT_RUN_ROOT, load_priority_sources, run_wiki_update


def print_json(value: object) -> None:
    safe_print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def doctor() -> Dict[str, Any]:
    config = load_model_config(DEFAULT_CONFIG_PATH)
    priority_sources = load_priority_sources(DEFAULT_PRIORITY_SOURCES_PATH)
    return {
        "version": __version__,
        "modules": {
            "openai": importlib.util.find_spec("openai") is not None,
            "anthropic": importlib.util.find_spec("anthropic") is not None,
            "python-dotenv": importlib.util.find_spec("dotenv") is not None,
        },
        "env": {
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
            "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        },
        "profiles": sorted(config.profiles),
        "default_profile": config.default_profile,
        "priority_sources_path": str(DEFAULT_PRIORITY_SOURCES_PATH),
        "priority_sources_count": len(priority_sources.get("priority_sources", [])),
    }


def add_update_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("query", help="Web-search-backed wiki update request.")
    parser.add_argument("--profile", default=None, help="Model profile from models.example.json.")
    parser.add_argument("--config", default=None, help="Optional model config JSON path.")
    parser.add_argument(
        "--priority-sources",
        default=str(DEFAULT_PRIORITY_SOURCES_PATH),
        help="JSON file of manually prioritized web sources to search first.",
    )
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument("--catalog-dir", default=str(DEFAULT_CATALOG_DIR))
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--selection-mode", choices=["model", "keyword", "full"], default="model")
    parser.add_argument("--max-selected-files", type=int, default=8)
    parser.add_argument("--max-page-chars", type=int, default=12000)
    parser.add_argument("--max-output-tokens", type=int, default=1800)
    parser.add_argument("--max-web-uses", type=int, default=5)
    parser.add_argument("--allow-new-pages", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Save research/proposal but do not edit wiki files.")
    parser.add_argument("--json", action="store_true")


def main() -> None:
    parser = argparse.ArgumentParser(description="Isolated GopherEye Wiki Update Agent.")
    sub = parser.add_subparsers(dest="command")

    add_update_args(sub.add_parser("update", help="Search the web, update wiki, then rebuild catalog."))
    sub.add_parser("doctor", help="Show dependency, key, and profile status.")

    catalog_parser = sub.add_parser("build-catalog", help="Build the wiki catalog.")
    catalog_parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    catalog_parser.add_argument("--catalog-dir", default=str(DEFAULT_CATALOG_DIR))
    catalog_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "doctor":
        print_json(doctor())
        return
    if args.command == "build-catalog":
        catalog = build_catalog(wiki_dir=Path(args.wiki_dir), catalog_dir=Path(args.catalog_dir))
        if args.json:
            print_json(catalog)
        else:
            safe_print(f"Built catalog with {catalog['num_pages']} pages at {args.catalog_dir}")
        return
    if args.command == "update":
        result = run_wiki_update(
            args.query,
            profile_name=args.profile,
            config_path=args.config,
            priority_sources_path=Path(args.priority_sources) if args.priority_sources else None,
            wiki_dir=Path(args.wiki_dir),
            catalog_dir=Path(args.catalog_dir),
            run_root=Path(args.run_root),
            selection_mode=args.selection_mode,
            max_selected_files=args.max_selected_files,
            max_page_chars=args.max_page_chars,
            max_output_tokens=args.max_output_tokens,
            max_web_uses=args.max_web_uses,
            allow_new_pages=args.allow_new_pages,
            dry_run=args.dry_run,
        )
        if args.json:
            print_json(result)
            return
        safe_print(f"run_id: {result['run_id']}")
        safe_print(f"profile: {result['profile']}")
        safe_print(f"model: {result['model']}")
        safe_print(f"dry_run: {result['dry_run']}")
        safe_print(f"priority_sources_count: {result['priority_sources_count']}")
        safe_print("selected_pages:")
        for page in result.get("selected_pages", []):
            safe_print(f"- {page['path']}")
        safe_print("operations:")
        for operation in result.get("operations", []):
            safe_print(f"- {operation.get('type')} {operation.get('path')}")
        if not result["dry_run"]:
            safe_print("applied_operations:")
            for operation in result.get("applied_operations", []):
                safe_print(f"- {operation.get('status')} {operation.get('path')}")
            safe_print(f"catalog_built: {result['catalog_built']}")
        safe_print(f"run_dir: {result['run_dir']}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
