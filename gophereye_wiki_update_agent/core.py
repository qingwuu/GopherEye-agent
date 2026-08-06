from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from src.gophereye_runtime.utils import now_utc, parse_json_object, safe_component, stable_id, timestamp_id
from src.single_model_wiki.core import (
    DEFAULT_CATALOG_DIR,
    DEFAULT_WIKI_DIR,
    ROOT_DIR,
    build_catalog,
    read_pages_by_id,
    render_catalog_for_prompt,
    select_pages_keyword_fallback,
    trim_text,
    write_text,
)

from .config import DEFAULT_CONFIG_PATH, load_model_config
from .providers import ModelBackend, create_backend


DEFAULT_RUN_ROOT = ROOT_DIR / "wiki_update_agent_workspace" / "runs"
DEFAULT_PRIORITY_SOURCES_PATH = Path(__file__).resolve().parent / "priority_sources.json"


def load_priority_sources(path: Path | None = DEFAULT_PRIORITY_SOURCES_PATH) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {"version": 1, "notes": "", "priority_sources": []}
    raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(raw, dict):
        raise ValueError(f"Priority sources file must be a JSON object: {path}")
    sources = raw.get("priority_sources", [])
    if not isinstance(sources, list):
        raise ValueError(f"priority_sources must be a list: {path}")
    clean_sources = []
    for item in sources:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("url") or "").strip()
        url = str(item.get("url") or "").strip()
        domains = [str(domain).strip() for domain in item.get("domains", []) if str(domain).strip()]
        topics = [str(topic).strip() for topic in item.get("topics", []) if str(topic).strip()]
        if not name and not url and not domains:
            continue
        clean_sources.append(
            {
                "name": name,
                "url": url,
                "domains": domains,
                "topics": topics,
            }
        )
    return {
        "version": raw.get("version", 1),
        "notes": str(raw.get("notes") or ""),
        "priority_sources": clean_sources,
    }


def priority_domains(priority_sources: Dict[str, Any]) -> List[str]:
    domains: List[str] = []
    for source in priority_sources.get("priority_sources", []):
        if not isinstance(source, dict):
            continue
        for domain in source.get("domains", []):
            text = str(domain).strip()
            if text and text not in domains:
                domains.append(text)
    return domains


def render_priority_sources(priority_sources: Dict[str, Any]) -> str:
    sources = priority_sources.get("priority_sources", [])
    if not sources:
        return "(no priority sources configured)"
    lines = []
    for source in sources:
        name = source.get("name") or source.get("url") or "priority source"
        url = source.get("url") or ""
        domains = ", ".join(source.get("domains", [])) or "no domain listed"
        topics = ", ".join(source.get("topics", [])) or "general"
        lines.append(f"- {name}: {url} | domains: {domains} | topics: {topics}")
    return "\n".join(lines)


def build_priority_research_prompt(query: str, priority_sources: Dict[str, Any]) -> str:
    return f"""You are the priority-source research stage for the isolated GopherEye Wiki Update Agent.

Use web search to check the manually configured priority sources first. Search
within these sites or domains before using general results. This pass is not
the full research pass; it is only the priority-source pass.

Priority sources:
{render_priority_sources(priority_sources)}

Return ONLY valid JSON with this exact shape:
{{
  "query": "short normalized query",
  "source_summary": "one concise paragraph about priority-source findings",
  "facts": [
    {{"claim": "short fact", "source_url": "https://...", "source_title": "short title"}}
  ],
  "sources": [
    {{"title": "short title", "url": "https://...", "why_relevant": "short reason"}}
  ],
  "unclear_points": []
}}

Rules:
- facts: at most 6, one sentence each.
- sources: at most 6.
- Prefer facts from the listed priority sources.
- If priority sources do not contain reliable relevant information, return
  empty facts and explain the gap in unclear_points.
- Do not treat this priority-source list as exhaustive.

Wiki update request:
{query}
"""


def build_broad_research_prompt(query: str, priority_research: Dict[str, Any], priority_sources: Dict[str, Any]) -> str:
    return f"""You are the broad web research stage for the isolated GopherEye Wiki Update Agent.

Use web search to collect only high-value, source-backed facts relevant to this
wiki update request. Prefer authoritative agriculture extension, university,
government, peer-reviewed, or official crop-protection sources.

The priority-source pass has already run. Continue with broad web search beyond
the priority sources. You may still use a priority source if it is clearly the
best source, but do not limit the search to those sources.

Keep the output compact. Do not include treatment rates, chemical labels, or
legal-use advice unless the source is explicitly authoritative and current.

Return ONLY valid JSON with this exact shape:
{{
  "query": "short normalized query",
  "source_summary": "one concise paragraph",
  "facts": [
    {{"claim": "short fact", "source_url": "https://...", "source_title": "short title"}}
  ],
  "sources": [
    {{"title": "short title", "url": "https://...", "why_relevant": "short reason"}}
  ],
  "unclear_points": []
}}

Rules:
- facts: at most 6, one sentence each.
- sources: at most 6.
- Keep only information important enough to update a diagnostic wiki.
- If the web search finds nothing reliable, return empty facts and explain in
  unclear_points.

Priority sources checked first:
{render_priority_sources(priority_sources)}

Priority-source research JSON:
{json.dumps(priority_research, ensure_ascii=False, indent=2)}

Wiki update request:
{query}
"""


def build_research_prompt(query: str) -> str:
    return build_broad_research_prompt(
        query,
        {
            "query": query,
            "source_summary": "No priority-source pass was configured.",
            "facts": [],
            "sources": [],
            "unclear_points": [],
        },
        {"priority_sources": []},
    )


def build_selection_prompt(query: str, research: Dict[str, Any], catalog: Dict[str, Any], max_selected_files: int) -> str:
    return f"""You are selecting candidate pages for the isolated GopherEye Wiki Update Agent.

Return ONLY a JSON array of page IDs. Select at most {max_selected_files}.

Select pages whose current content should be read before deciding where the
wiki update belongs. Prefer existing disease, treatment, procedure, or
reference pages over creating new pages.

User request:
{query}

Research summary JSON:
{json.dumps(research, ensure_ascii=False, indent=2)}

Wiki catalog:
{render_catalog_for_prompt(catalog)}
"""


def build_update_prompt(
    *,
    query: str,
    research: Dict[str, Any],
    catalog: Dict[str, Any],
    pages: Sequence[Dict[str, Any]],
    allow_new_pages: bool,
) -> str:
    page_blocks = []
    for page in pages:
        page_blocks.append(
            f"""[CURRENT_WIKI_PAGE id={page['id']} path={page['path']} title={page['title']}]
{page['text']}
[/CURRENT_WIKI_PAGE]"""
        )
    return f"""You are the editing stage for the isolated GopherEye Wiki Update Agent.

You have already received web-search research. You must now read the selected
current wiki pages and decide the smallest useful wiki update.

Return ONLY valid JSON with this exact top-level shape:
{{
  "source_summary": "one concise paragraph",
  "operations": [
    {{
      "type": "append_under_heading",
      "path": "relative/wiki/page.md",
      "heading": "exact existing heading text without #",
      "content": "- One compact source-backed bullet with inline markdown source link.",
      "reason": "short reason"
    }}
  ],
  "unclear_points": []
}}

Wiki update operations:
- append_under_heading: append content inside an existing selected page section.
- append_to_file: append content at the end of an existing selected page.
- create_page: only if allow_new_pages is true and no existing page fits.

Rules:
- Prefer append_under_heading on an existing selected page.
- Content must be minimal: 1 to 4 bullets or one short paragraph, max 120 words
  per operation.
- Keep source links inline, e.g. [UC IPM](https://example.org).
- Do not duplicate facts already present in the page.
- Do not rewrite entire pages.
- Do not change frontmatter.
- Do not add treatment rates, chemical product instructions, or legal-use
  claims unless the selected treatment page is the target and the source
  explicitly supports the exact wording.
- Use only paths from selected current wiki pages unless create_page is allowed.
- create_page allowed: {str(bool(allow_new_pages)).lower()}.
- If there is no reliable new information, return operations: [].

User request:
{query}

Research summary JSON:
{json.dumps(research, ensure_ascii=False, indent=2)}

Wiki catalog:
{render_catalog_for_prompt(catalog)}

Selected current wiki pages:
{chr(10).join(page_blocks)}
"""


def parse_json_array(text: str) -> List[Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    match = re.search(r"\[[\s\S]*\]", stripped)
    if match:
        stripped = match.group(0)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def parse_model_object(text: str, *, fallback: Dict[str, Any]) -> Dict[str, Any]:
    parsed = parse_json_object(text)
    return parsed if parsed is not None else fallback


def build_json_retry_prompt(
    *,
    failed_stage: str,
    original_prompt: str,
    raw_output: str,
) -> str:
    return f"""The previous {failed_stage} response was not valid JSON.

Return ONLY one valid JSON object. Do not include markdown fences, comments, or
explanatory text.

If no wiki update is needed, return:
{{
  "source_summary": "short reason",
  "operations": [],
  "unclear_points": []
}}

Original task prompt:
{original_prompt}

Previous invalid output:
{raw_output or "(empty output)"}

Valid JSON object now:"""


def generate_json_object_with_retry(
    *,
    backend: ModelBackend,
    prompt: str,
    stage: str,
    fallback: Dict[str, Any],
    max_output_tokens: int,
) -> tuple[Dict[str, Any], Any | None]:
    response = backend.generate(
        prompt,
        max_output_tokens=max_output_tokens,
        web_search=False,
    )
    parsed = parse_json_object(response.text)
    if parsed is not None:
        return parsed, response

    retry_prompt = build_json_retry_prompt(
        failed_stage=stage,
        original_prompt=prompt,
        raw_output=response.text,
    )
    retry_response = backend.generate(
        retry_prompt,
        max_output_tokens=max(max_output_tokens, 6000),
        web_search=False,
    )
    retry_parsed = parse_json_object(retry_response.text)
    if retry_parsed is not None:
        retry_parsed["_repair_used"] = True
        return retry_parsed, retry_response

    failed = dict(fallback)
    failed["raw_model_output"] = response.text
    failed["repair_raw_model_output"] = retry_response.text
    failed["_repair_used"] = True
    return failed, retry_response


def dedupe_dicts_by_url(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("source_url") or "").strip()
        key = url.lower() or json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def dedupe_facts(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim") or "").strip()
        url = str(item.get("source_url") or "").strip()
        key = (claim.lower(), url.lower())
        if not claim or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def combine_research(
    *,
    query: str,
    priority_sources_config: Dict[str, Any],
    priority_research: Dict[str, Any] | None,
    broad_research: Dict[str, Any],
) -> Dict[str, Any]:
    priority_research = priority_research or {
        "query": query,
        "source_summary": "No priority-source pass was run.",
        "facts": [],
        "sources": [],
        "unclear_points": [],
    }
    facts = dedupe_facts(priority_research.get("facts")) + [
        item
        for item in dedupe_facts(broad_research.get("facts"))
        if item not in dedupe_facts(priority_research.get("facts"))
    ]
    sources = dedupe_dicts_by_url(priority_research.get("sources")) + [
        item
        for item in dedupe_dicts_by_url(broad_research.get("sources"))
        if item not in dedupe_dicts_by_url(priority_research.get("sources"))
    ]
    unclear_points = []
    for source in [priority_research, broad_research]:
        for item in source.get("unclear_points", []) if isinstance(source.get("unclear_points"), list) else []:
            text = str(item).strip()
            if text and text not in unclear_points:
                unclear_points.append(text)
    return {
        "query": broad_research.get("query") or priority_research.get("query") or query,
        "source_summary": " ".join(
            part
            for part in [
                str(priority_research.get("source_summary") or "").strip(),
                str(broad_research.get("source_summary") or "").strip(),
            ]
            if part
        ).strip(),
        "facts": facts[:10],
        "sources": sources[:10],
        "unclear_points": unclear_points[:10],
        "research_strategy": "priority_sources_first_then_broad_web",
        "priority_sources": priority_sources_config.get("priority_sources", []),
        "priority_research": priority_research,
        "broad_research": broad_research,
    }


def select_candidate_pages(
    *,
    query: str,
    research: Dict[str, Any],
    catalog: Dict[str, Any],
    backend: ModelBackend,
    selection_mode: str,
    max_selected_files: int,
    max_output_tokens: int,
) -> List[str]:
    if selection_mode == "full":
        return [page["id"] for page in catalog.get("pages", [])][:max_selected_files]
    selection_text = query + "\n" + json.dumps(research, ensure_ascii=False)
    if selection_mode == "keyword":
        return select_pages_keyword_fallback(
            selection_text,
            catalog=catalog,
            max_selected_files=max_selected_files,
        )
    if selection_mode != "model":
        raise ValueError(f"Unsupported selection_mode: {selection_mode}")

    prompt = build_selection_prompt(query, research, catalog, max_selected_files)
    raw = backend.generate(prompt, max_output_tokens=min(max_output_tokens, 512), web_search=False).text
    selected = parse_json_array(raw)
    valid_ids = {page["id"] for page in catalog.get("pages", [])}
    selected_ids = []
    for item in selected:
        if isinstance(item, str) and item in valid_ids and item not in selected_ids:
            selected_ids.append(item)
    if selected_ids:
        return selected_ids[:max_selected_files]
    return select_pages_keyword_fallback(
        selection_text,
        catalog=catalog,
        max_selected_files=max_selected_files,
    )


def normalize_heading(value: str) -> str:
    text = value.strip().lstrip("#").strip().lower()
    return re.sub(r"\s+", " ", text)


def heading_level(line: str) -> int | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    return len(match.group(1)) if match else None


def append_under_heading(text: str, heading: str, content: str) -> tuple[str, str]:
    clean_content = content.strip()
    if not clean_content:
        return text, "skipped_empty"
    if not heading.strip():
        return text, "skipped_heading_not_found"
    if clean_content in text:
        return text, "skipped_duplicate"

    wanted = normalize_heading(heading)
    lines = text.splitlines()
    insert_at = len(lines)
    found_heading = False
    for idx, line in enumerate(lines):
        level = heading_level(line)
        if level is None or normalize_heading(line) != wanted:
            continue
        found_heading = True
        insert_at = len(lines)
        for probe in range(idx + 1, len(lines)):
            next_level = heading_level(lines[probe])
            if next_level is not None and next_level <= level:
                insert_at = probe
                break
        break

    if not found_heading:
        return text, "skipped_heading_not_found"

    block = clean_content.splitlines()
    if insert_at > 0 and lines[insert_at - 1].strip():
        block = [""] + block
    if insert_at < len(lines) and lines[insert_at].strip():
        block = block + [""]
    lines[insert_at:insert_at] = block
    return "\n".join(lines).rstrip() + "\n", "applied"


def append_to_file(text: str, content: str) -> tuple[str, str]:
    clean_content = content.strip()
    if not clean_content:
        return text, "skipped_empty"
    if clean_content in text:
        return text, "skipped_duplicate"
    return text.rstrip() + "\n\n" + clean_content + "\n", "applied"


def normalize_wiki_path_text(path_text: str) -> str:
    normalized = path_text.replace("\\", "/").strip("/")
    if normalized.startswith("wiki/"):
        normalized = normalized[len("wiki/") :]
    return normalized


def resolve_wiki_page(wiki_dir: Path, path_text: str) -> Path:
    normalized = normalize_wiki_path_text(path_text)
    if not normalized or normalized.startswith("../") or "/../" in f"/{normalized}/":
        raise ValueError(f"Unsafe wiki path: {path_text}")
    path = (wiki_dir / normalized).resolve(strict=False)
    wiki_root = wiki_dir.resolve(strict=False)
    try:
        path.relative_to(wiki_root)
    except ValueError as exc:
        raise ValueError(f"Wiki path escapes wiki dir: {path_text}") from exc
    if path.suffix.lower() != ".md":
        raise ValueError(f"Wiki update target must be a markdown file: {path_text}")
    return path


def apply_operations(
    operations: Sequence[Dict[str, Any]],
    *,
    wiki_dir: Path,
    selected_paths: Sequence[str],
    allow_new_pages: bool,
) -> List[Dict[str, Any]]:
    selected_set = {normalize_wiki_path_text(path) for path in selected_paths}
    results: List[Dict[str, Any]] = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            results.append({"index": index, "status": "skipped_invalid", "operation": operation})
            continue
        op_type = str(operation.get("type") or "").strip()
        path_text = str(operation.get("path") or "").strip()
        content = str(operation.get("content") or "").strip()
        result: Dict[str, Any] = {
            "index": index,
            "type": op_type,
            "path": path_text,
            "reason": operation.get("reason"),
        }
        try:
            target = resolve_wiki_page(wiki_dir, path_text)
            rel_path = target.relative_to(wiki_dir.resolve(strict=False)).as_posix()
            if op_type != "create_page" and rel_path not in selected_set:
                raise ValueError("operation path was not among selected pages read by the model")
            if op_type == "create_page":
                if not allow_new_pages:
                    result["status"] = "skipped_new_pages_disabled"
                elif target.exists():
                    result["status"] = "skipped_page_exists"
                else:
                    if not content.startswith("#"):
                        raise ValueError("create_page content must start with a markdown heading")
                    write_text(target, content.rstrip() + "\n")
                    result["status"] = "applied"
            elif op_type == "append_under_heading":
                if not target.exists():
                    raise FileNotFoundError(target)
                updated, status = append_under_heading(
                    target.read_text(encoding="utf-8", errors="replace"),
                    str(operation.get("heading") or ""),
                    content,
                )
                if status == "applied":
                    write_text(target, updated)
                result["status"] = status
            elif op_type == "append_to_file":
                if not target.exists():
                    raise FileNotFoundError(target)
                updated, status = append_to_file(
                    target.read_text(encoding="utf-8", errors="replace"),
                    content,
                )
                if status == "applied":
                    write_text(target, updated)
                result["status"] = status
            else:
                result["status"] = "skipped_unknown_operation"
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)
        results.append(result)
    return results


def save_run_artifacts(
    *,
    run_dir: Path,
    research: Dict[str, Any],
    proposal: Dict[str, Any],
    result: Dict[str, Any],
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    write_text(run_dir / "research.json", json.dumps(research, ensure_ascii=False, indent=2) + "\n")
    write_text(run_dir / "proposal.json", json.dumps(proposal, ensure_ascii=False, indent=2) + "\n")
    write_text(run_dir / "run_summary.json", json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n")


def run_wiki_update(
    query: str,
    *,
    profile_name: str | None = None,
    config_path: str | Path | None = None,
    priority_sources_path: Path | None = DEFAULT_PRIORITY_SOURCES_PATH,
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
    run_root: Path = DEFAULT_RUN_ROOT,
    selection_mode: str = "model",
    max_selected_files: int = 8,
    max_page_chars: int = 12000,
    max_output_tokens: int = 6000,
    max_web_uses: int = 5,
    allow_new_pages: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    config = load_model_config(config_path or DEFAULT_CONFIG_PATH)
    profile = config.get_profile(profile_name)
    backend = create_backend(profile)
    run_id = stable_id("wikiupd", query, timestamp_id())
    run_dir = run_root / f"{timestamp_id()}_{safe_component(run_id)}"

    catalog = build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)
    priority_sources_config = load_priority_sources(priority_sources_path)
    priority_response = None
    priority_research = None
    domains = priority_domains(priority_sources_config)
    if priority_sources_config.get("priority_sources"):
        priority_prompt = build_priority_research_prompt(query, priority_sources_config)
        priority_response = backend.generate(
            priority_prompt,
            max_output_tokens=max_output_tokens,
            web_search=True,
            max_web_uses=max_web_uses,
            allowed_domains=domains,
        )
        priority_research = parse_model_object(
            priority_response.text,
            fallback={
                "query": query,
                "source_summary": "Priority-source model output was not valid JSON.",
                "facts": [],
                "sources": [],
                "unclear_points": ["Priority-source research response could not be parsed."],
                "raw_model_output": priority_response.text,
            },
        )

    broad_prompt = build_broad_research_prompt(
        query,
        priority_research
        or {
            "query": query,
            "source_summary": "No priority-source pass was configured.",
            "facts": [],
            "sources": [],
            "unclear_points": [],
        },
        priority_sources_config,
    )
    broad_response = backend.generate(
        broad_prompt,
        max_output_tokens=max_output_tokens,
        web_search=True,
        max_web_uses=max_web_uses,
    )
    broad_research = parse_model_object(
        broad_response.text,
        fallback={
            "query": query,
            "source_summary": "Broad-search model output was not valid JSON.",
            "facts": [],
            "sources": [],
            "unclear_points": ["Broad-search research response could not be parsed."],
            "raw_model_output": broad_response.text,
        },
    )
    research = combine_research(
        query=query,
        priority_sources_config=priority_sources_config,
        priority_research=priority_research,
        broad_research=broad_research,
    )
    selected_ids = select_candidate_pages(
        query=query,
        research=research,
        catalog=catalog,
        backend=backend,
        selection_mode=selection_mode,
        max_selected_files=max_selected_files,
        max_output_tokens=max_output_tokens,
    )
    pages = read_pages_by_id(
        selected_ids,
        catalog=catalog,
        wiki_dir=wiki_dir,
        max_page_chars=max_page_chars,
    )
    selected_paths = [page["path"] for page in pages]

    update_prompt = build_update_prompt(
        query=query,
        research=research,
        catalog=catalog,
        pages=pages,
        allow_new_pages=allow_new_pages,
    )
    proposal, proposal_response = generate_json_object_with_retry(
        backend=backend,
        prompt=update_prompt,
        stage="wiki update proposal",
        max_output_tokens=max_output_tokens,
        fallback={
            "source_summary": "Model output was not valid JSON.",
            "operations": [],
            "unclear_points": ["Update proposal response could not be parsed."],
        },
    )
    operations = proposal.get("operations") if isinstance(proposal.get("operations"), list) else []

    applied_operations: List[Dict[str, Any]] = []
    catalog_after: Dict[str, Any] | None = None
    if not dry_run:
        applied_operations = apply_operations(
            operations,
            wiki_dir=wiki_dir,
            selected_paths=selected_paths,
            allow_new_pages=allow_new_pages,
        )
        catalog_after = build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)

    result: Dict[str, Any] = {
        "run_id": run_id,
        "created_at": now_utc(),
        "query": query,
        "profile": profile.name,
        "provider": profile.provider,
        "model": profile.model,
        "dry_run": dry_run,
        "allow_new_pages": allow_new_pages,
        "wiki_dir": str(wiki_dir),
        "catalog_dir": str(catalog_dir),
        "priority_sources_path": str(priority_sources_path) if priority_sources_path else None,
        "priority_sources_count": len(priority_sources_config.get("priority_sources", [])),
        "run_dir": str(run_dir),
        "selected_pages": [
            {"id": page["id"], "path": page["path"], "title": page["title"]}
            for page in pages
        ],
        "source_summary": proposal.get("source_summary") or research.get("source_summary"),
        "operations": operations,
        "applied_operations": applied_operations,
        "catalog_built": bool(catalog_after is not None),
        "catalog_pages": catalog_after.get("num_pages") if catalog_after else catalog.get("num_pages"),
        "unclear_points": proposal.get("unclear_points") or research.get("unclear_points") or [],
        "usage": {
            "priority_research": priority_response.usage if priority_response else None,
            "broad_research": broad_response.usage,
            "proposal": proposal_response.usage,
        },
        "backend_meta": {
            "priority_research": priority_response.backend_meta if priority_response else None,
            "broad_research": broad_response.backend_meta,
            "proposal": proposal_response.backend_meta,
        },
    }
    save_run_artifacts(run_dir=run_dir, research=research, proposal=proposal, result=result)
    return result
