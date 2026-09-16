from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT_DIR / "wiki"
TARGET_DIR = ROOT_DIR / "wiki2"
CATALOG_DIR = ROOT_DIR / "catalog" / "wiki2"


@dataclass
class Section:
    heading: str
    slug: str
    body: str


@dataclass
class PagePlan:
    source_rel: Path
    target_index_rel: Path
    title: str
    intro: str
    sections: list[Section]
    meta: dict[str, Any]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip("\n")
    body = text[end + len("\n---") :].lstrip("\n")
    return parse_frontmatter(raw), body


def parse_frontmatter(raw: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    current_list_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        list_match = re.match(r"^\s*-\s+(.*)\s*$", line)
        if list_match and current_list_key:
            if isinstance(meta.get(current_list_key), list):
                meta.setdefault(current_list_key, []).append(list_match.group(1).strip())
            continue
        key_match = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if not key_match:
            continue
        key, value = key_match.group(1), key_match.group(2).strip()
        if value == "":
            current_list_key = key
            meta[key] = [] if key == "sources" else value
        else:
            current_list_key = None
            meta[key] = value
    return meta


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "section"


def title_from_body(body: str, fallback: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def strip_h1(body: str) -> tuple[str, str]:
    lines = body.splitlines()
    out: list[str] = []
    title = ""
    skipped = False
    for line in lines:
        if not skipped and line.startswith("# "):
            title = line[2:].strip()
            skipped = True
            continue
        out.append(line)
    return title, "\n".join(out).strip("\n")


def split_sections(body_without_h1: str) -> tuple[str, list[Section]]:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", body_without_h1))
    if not matches:
        return body_without_h1.strip(), []

    intro = body_without_h1[: matches[0].start()].strip()
    sections: list[Section] = []
    used_slugs: set[str] = set()
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body_without_h1)
        body = body_without_h1[start:end].strip()
        base_slug = slugify(heading)
        slug = base_slug
        suffix = 2
        while slug in used_slugs:
            slug = f"{base_slug}_{suffix}"
            suffix += 1
        used_slugs.add(slug)
        sections.append(Section(heading=heading, slug=slug, body=body))
    return intro, sections


def target_index_for_source(source_rel: Path) -> Path:
    if source_rel.name == "index.md":
        return source_rel
    return source_rel.with_suffix("") / "index.md"


def markdown_sources(source_dir: Path) -> list[Path]:
    return sorted(path for path in source_dir.rglob("*.md") if path.is_file())


def plan_pages(source_dir: Path) -> list[PagePlan]:
    plans: list[PagePlan] = []
    for source_path in markdown_sources(source_dir):
        source_rel = source_path.relative_to(source_dir)
        text = read_text(source_path)
        meta, body = split_frontmatter(text)
        body_title = title_from_body(body, source_rel.as_posix())
        title, without_h1 = strip_h1(body)
        intro, sections = split_sections(without_h1)
        plans.append(
            PagePlan(
                source_rel=source_rel,
                target_index_rel=target_index_for_source(source_rel),
                title=title or body_title,
                intro=intro,
                sections=sections,
                meta=meta,
            )
        )
    return plans


def frontmatter(fields: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


LINK_RE = re.compile(r"(!?)\[([^\]]*)\]\(([^)]+)\)")


def normalize_rel(path: Path) -> Path:
    parts: list[str] = []
    for part in path.as_posix().strip("/").split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            else:
                parts.append(part)
            continue
        parts.append(part)
    return Path(*parts) if parts else Path()


def to_posix(path: Path) -> str:
    return path.as_posix()


def relative_link(from_rel: Path, to_rel: Path) -> str:
    from_dir = (TARGET_DIR / from_rel).parent
    to_path = TARGET_DIR / to_rel
    return to_posix(Path(__import__("os").path.relpath(to_path, from_dir)))


def relative_repo_link(from_rel: Path, repo_rel: Path) -> str:
    from_dir = (TARGET_DIR / from_rel).parent
    to_path = ROOT_DIR / repo_rel
    return to_posix(Path(__import__("os").path.relpath(to_path, from_dir)))


def rewrite_links(
    text: str,
    *,
    source_rel: Path,
    target_rel: Path,
    source_to_target: dict[Path, Path],
    asset_paths: set[Path],
) -> str:
    def repl(match: re.Match[str]) -> str:
        bang, label, raw_target = match.group(1), match.group(2), match.group(3).strip()
        if raw_target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        target_path, anchor = (raw_target.split("#", 1) + [""])[:2] if "#" in raw_target else (raw_target, "")
        if not target_path:
            return match.group(0)
        resolved = normalize_rel(source_rel.parent / target_path)
        if resolved in source_to_target:
            new_target = relative_link(target_rel, source_to_target[resolved])
        elif resolved in asset_paths:
            new_target = relative_link(target_rel, resolved)
        elif resolved.parts and resolved.parts[0] == "..":
            repo_rel = Path(*resolved.parts[1:])
            if (ROOT_DIR / repo_rel).exists():
                new_target = relative_repo_link(target_rel, repo_rel)
            else:
                return match.group(0)
        else:
            return match.group(0)
        if anchor:
            new_target = f"{new_target}#{anchor}"
        return f"{bang}[{label}]({new_target})"

    return LINK_RE.sub(repl, text)


def search_cues(title: str, section: Section | None = None) -> str:
    parts = [title]
    if section:
        parts.append(section.heading)
        parts.extend(re.findall(r"[A-Za-z][A-Za-z0-9_-]+", section.body)[:24])
    return " ".join(parts)


def parent_index_text(
    plan: PagePlan,
    *,
    source_to_target: dict[Path, Path],
    asset_paths: set[Path],
) -> str:
    meta = plan.meta
    body = frontmatter(
        {
            "title": plan.title,
            "page_type": "detailed_parent_page",
            "source_wiki_path": f"wiki/{plan.source_rel.as_posix()}",
            "review_status": meta.get("review_status", "draft"),
            "last_updated": meta.get("last_updated"),
            "disease_id": meta.get("disease_id"),
            "sources": meta.get("sources") if isinstance(meta.get("sources"), list) else [],
        }
    )
    body += f"# {plan.title}\n\n"
    body += (
        "This wiki2 parent page is intentionally small. Use it for routing, then "
        "retrieve the detailed section pages below instead of loading the full "
        "source page.\n\n"
    )
    if plan.intro:
        intro = rewrite_links(
            plan.intro,
            source_rel=plan.source_rel,
            target_rel=plan.target_index_rel,
            source_to_target=source_to_target,
            asset_paths=asset_paths,
        )
        body += intro.strip() + "\n\n"
    if plan.sections:
        body += "## Detailed Pages\n\n"
        for section in plan.sections:
            body += f"- [{section.heading}]({section.slug}.md)\n"
        body += "\n"
    body += "## Retrieval Notes\n\n"
    body += "```text\n"
    body += f"source_wiki_path: wiki/{plan.source_rel.as_posix()}\n"
    body += "retrieval_unit: parent routing page\n"
    body += "load_strategy: load section pages only when their heading matches the query\n"
    body += f"search_cues: {search_cues(plan.title)}\n"
    body += "```\n"
    return body


def section_page_text(
    plan: PagePlan,
    section: Section,
    *,
    source_to_target: dict[Path, Path],
    asset_paths: set[Path],
) -> str:
    section_rel = plan.target_index_rel.parent / f"{section.slug}.md"
    meta = plan.meta
    body = frontmatter(
        {
            "title": f"{plan.title} - {section.heading}",
            "page_type": "detailed_section_page",
            "source_wiki_path": f"wiki/{plan.source_rel.as_posix()}",
            "source_section": section.heading,
            "parent_page": "index.md",
            "review_status": meta.get("review_status", "draft"),
            "last_updated": meta.get("last_updated"),
            "disease_id": meta.get("disease_id"),
            "sources": meta.get("sources") if isinstance(meta.get("sources"), list) else [],
        }
    )
    body += f"# {plan.title} - {section.heading}\n\n"
    body += f"Parent: [{plan.title}](index.md)\n\n"
    body += "```text\n"
    body += f"source_wiki_path: wiki/{plan.source_rel.as_posix()}\n"
    body += f"source_section: {section.heading}\n"
    body += "retrieval_unit: detailed section page\n"
    body += f"search_cues: {search_cues(plan.title, section)}\n"
    body += "```\n\n"
    if section.body:
        body += rewrite_links(
            section.body,
            source_rel=plan.source_rel,
            target_rel=section_rel,
            source_to_target=source_to_target,
            asset_paths=asset_paths,
        ).strip() + "\n"
    return body


def root_index_text(plans: list[PagePlan]) -> str:
    body = frontmatter(
        {
            "title": "GopherEye Wiki2 Split Index",
            "page_type": "index_page",
            "review_status": "draft",
            "last_updated": "2026-08-17",
        }
    )
    body += "# GopherEye Wiki2\n\n"
    body += (
        "Wiki2 is a split-page copy of `wiki/` for token-cost experiments. "
        "It keeps the same knowledge boundary, but breaks large pages into "
        "small detailed section pages so retrieval can select less context.\n\n"
    )
    body += "## Retrieval Pattern\n\n"
    body += "```text\n"
    body += "1. Search parent pages for routing.\n"
    body += "2. Search detailed section pages by heading and search_cues.\n"
    body += "3. Load only the smallest sufficient detailed pages.\n"
    body += "4. Do not load all sibling pages unless the question asks for comparison.\n"
    body += "```\n\n"
    grouped: dict[str, list[PagePlan]] = {}
    for plan in plans:
        top = plan.target_index_rel.parts[0] if len(plan.target_index_rel.parts) > 1 else "root"
        grouped.setdefault(top, []).append(plan)
    for group in ["disease", "procedures", "reference", "treatment", "root"]:
        items = grouped.get(group)
        if not items:
            continue
        body += f"## {group.replace('_', ' ').title()}\n\n"
        for plan in items:
            if plan.source_rel.as_posix() == "index.md":
                continue
            body += f"- [{plan.title}]({plan.target_index_rel.as_posix()})"
            if plan.sections:
                body += f" - {len(plan.sections)} detailed pages"
            body += "\n"
        body += "\n"
    return body


def copy_assets(source_dir: Path, target_dir: Path) -> set[Path]:
    asset_paths: set[Path] = set()
    for path in source_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() == ".md":
            continue
        rel = path.relative_to(source_dir)
        asset_paths.add(rel)
        out = target_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
    return asset_paths


def build_split_wiki(source_dir: Path, target_dir: Path, *, force: bool = False) -> dict[str, Any]:
    if target_dir.exists():
        if not force:
            raise SystemExit(f"{target_dir} already exists. Pass --force to replace it.")
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    plans = plan_pages(source_dir)
    source_to_target = {plan.source_rel: plan.target_index_rel for plan in plans}
    asset_paths = copy_assets(source_dir, target_dir)

    write_text(target_dir / "index.md", root_index_text(plans))

    generated_pages = 1
    source_reports: list[dict[str, Any]] = []
    for plan in plans:
        if plan.source_rel.as_posix() == "index.md":
            continue
        parent_text = parent_index_text(plan, source_to_target=source_to_target, asset_paths=asset_paths)
        write_text(target_dir / plan.target_index_rel, parent_text)
        generated_pages += 1
        for section in plan.sections:
            section_rel = plan.target_index_rel.parent / f"{section.slug}.md"
            write_text(
                target_dir / section_rel,
                section_page_text(
                    plan,
                    section,
                    source_to_target=source_to_target,
                    asset_paths=asset_paths,
                ),
            )
            generated_pages += 1
        source_reports.append(
            {
                "source_wiki_path": f"wiki/{plan.source_rel.as_posix()}",
                "target_parent_path": f"wiki2/{plan.target_index_rel.as_posix()}",
                "sections": [section.heading for section in plan.sections],
                "generated_pages": 1 + len(plan.sections),
            }
        )

    return {
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "source_pages": len(plans),
        "generated_pages": generated_pages,
        "sources": source_reports,
    }


def write_report(report: dict[str, Any], catalog_dir: Path) -> None:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    write_text(catalog_dir / "wiki2_split_report.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Build split-page wiki2 from wiki for retrieval-cost experiments.")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--target-dir", default=str(TARGET_DIR))
    parser.add_argument("--catalog-dir", default=str(CATALOG_DIR))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    target_dir = Path(args.target_dir)
    catalog_dir = Path(args.catalog_dir)
    report = build_split_wiki(source_dir, target_dir, force=args.force)

    sys.path.insert(0, str(ROOT_DIR))
    from src.single_model_wiki.core import build_catalog

    catalog = build_catalog(wiki_dir=target_dir, catalog_dir=catalog_dir)
    report["catalog_pages"] = catalog.get("num_pages")
    report["catalog_dir"] = str(catalog_dir)
    write_report(report, catalog_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
