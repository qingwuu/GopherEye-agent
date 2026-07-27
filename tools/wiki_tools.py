from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.gophereye_runtime.utils import normalize_repo_path, safe_print


WIKI_DIR = ROOT_DIR / "wiki"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_markdown_files(root: Path = WIKI_DIR) -> List[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def normalize_path(path_text: str) -> Path:
    return normalize_repo_path(ROOT_DIR, path_text)


def page_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def list_pages() -> List[Dict[str, Any]]:
    pages = []
    for path in iter_markdown_files():
        text = read_text(path)
        rel = path.relative_to(ROOT_DIR).as_posix()
        pages.append(
            {
                "path": rel,
                "title": page_title(text, rel),
                "chars": len(text),
            }
        )
    return pages


def search_pages(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    tokens = set(re.findall(r"[A-Za-z0-9_]+", query.lower()))
    results = []
    for path in iter_markdown_files():
        text = read_text(path)
        rel_path = path.relative_to(ROOT_DIR).as_posix()
        title = page_title(text, path.name)
        path_text = rel_path.lower()
        title_text = title.lower()
        body_text = text.lower()
        score = 0
        for token in tokens:
            if token in path_text:
                score += 6
            if token in title_text:
                score += 5
            score += min(body_text.count(token), 4)
        if score > 0:
            results.append(
                {
                    "path": rel_path,
                    "title": title,
                    "score": score,
                }
            )
    results.sort(key=lambda row: (-row["score"], row["path"]))
    return results[:limit]


LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
IMAGE_LINK_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def extract_markdown_links(text: str) -> List[str]:
    links = []
    for match in list(LINK_PATTERN.finditer(text)) + list(IMAGE_LINK_PATTERN.finditer(text)):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if target:
            links.append(target)
    return links


def resolve_link(source_path: Path, link: str) -> Path:
    clean = link.split("#", 1)[0]
    return (source_path.parent / clean).resolve()


def links_for_page(page_path_text: str) -> List[Dict[str, Any]]:
    page_path = normalize_path(page_path_text)
    text = read_text(page_path)
    rows = []
    for link in extract_markdown_links(text):
        target = resolve_link(page_path, link)
        rows.append(
            {
                "source": page_path.relative_to(ROOT_DIR).as_posix()
                if page_path.is_relative_to(ROOT_DIR)
                else str(page_path),
                "link": link,
                "resolved": target.as_posix(),
                "exists": target.exists(),
            }
        )
    return rows


def check_links() -> List[Dict[str, Any]]:
    problems = []
    for path in iter_markdown_files():
        for row in links_for_page(path.relative_to(ROOT_DIR).as_posix()):
            if not row["exists"]:
                problems.append(row)
    return problems


def validate_json(schema_path_text: str, json_path_text: str) -> Dict[str, Any]:
    schema_path = normalize_path(schema_path_text)
    json_path = normalize_path(json_path_text)
    schema = json.loads(read_text(schema_path))
    data = json.loads(read_text(json_path))

    try:
        import jsonschema
    except Exception:
        return {
            "schema": schema_path.relative_to(ROOT_DIR).as_posix(),
            "json": json_path.relative_to(ROOT_DIR).as_posix(),
            "valid": None,
            "note": "jsonschema is not installed; JSON parsed successfully but schema validation was skipped.",
        }

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        return {
            "schema": schema_path.relative_to(ROOT_DIR).as_posix(),
            "json": json_path.relative_to(ROOT_DIR).as_posix(),
            "valid": False,
            "error": exc.message,
        }

    return {
        "schema": schema_path.relative_to(ROOT_DIR).as_posix(),
        "json": json_path.relative_to(ROOT_DIR).as_posix(),
        "valid": True,
    }


def validate_jsonl(schema_path_text: str, jsonl_path_text: str) -> Dict[str, Any]:
    schema_path = normalize_path(schema_path_text)
    jsonl_path = normalize_path(jsonl_path_text)
    schema = json.loads(read_text(schema_path))
    rows = []
    for line_number, line in enumerate(read_text(jsonl_path).splitlines(), start=1):
        if not line.strip():
            continue
        rows.append((line_number, json.loads(line)))

    try:
        import jsonschema
    except Exception:
        return {
            "schema": schema_path.relative_to(ROOT_DIR).as_posix(),
            "jsonl": jsonl_path.relative_to(ROOT_DIR).as_posix(),
            "valid": None,
            "rows": len(rows),
            "note": "jsonschema is not installed; JSONL parsed successfully but schema validation was skipped.",
        }

    errors = []
    for line_number, row in rows:
        try:
            jsonschema.validate(instance=row, schema=schema)
        except jsonschema.ValidationError as exc:
            errors.append({"line": line_number, "error": exc.message})

    return {
        "schema": schema_path.relative_to(ROOT_DIR).as_posix(),
        "jsonl": jsonl_path.relative_to(ROOT_DIR).as_posix(),
        "valid": not errors,
        "rows": len(rows),
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic tools for the GopherEye wiki app.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-pages")

    search_parser = sub.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=10)

    read_parser = sub.add_parser("read")
    read_parser.add_argument("path")

    links_parser = sub.add_parser("links")
    links_parser.add_argument("path")

    sub.add_parser("check-links")

    validate_parser = sub.add_parser("validate-json")
    validate_parser.add_argument("schema")
    validate_parser.add_argument("json_file")

    validate_jsonl_parser = sub.add_parser("validate-jsonl")
    validate_jsonl_parser.add_argument("schema")
    validate_jsonl_parser.add_argument("jsonl_file")

    args = parser.parse_args()

    if args.command == "list-pages":
        safe_print(json.dumps(list_pages(), ensure_ascii=False, indent=2))
    elif args.command == "search":
        safe_print(json.dumps(search_pages(args.query, limit=args.limit), ensure_ascii=False, indent=2))
    elif args.command == "read":
        safe_print(read_text(normalize_path(args.path)))
    elif args.command == "links":
        safe_print(json.dumps(links_for_page(args.path), ensure_ascii=False, indent=2))
    elif args.command == "check-links":
        safe_print(json.dumps(check_links(), ensure_ascii=False, indent=2))
    elif args.command == "validate-json":
        safe_print(json.dumps(validate_json(args.schema, args.json_file), ensure_ascii=False, indent=2))
    elif args.command == "validate-jsonl":
        safe_print(json.dumps(validate_jsonl(args.schema, args.jsonl_file), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
