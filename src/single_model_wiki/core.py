from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_WIKI_DIR = ROOT_DIR / "wiki"
DEFAULT_RAW_DIR = ROOT_DIR / "raw"
DEFAULT_CATALOG_DIR = ROOT_DIR / "catalog"
DEFAULT_DRAFT_DIR = ROOT_DIR / "draft_updates"

QWEN_VL_PROVIDERS = {"qwen-vl", "transformers-vl"}
_QWEN_VL_CACHE: Dict[str, Any] = {}


def safe_print(text: str) -> None:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    else:
        print(text)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "source"


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def iter_markdown_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def collect_headings(text: str, limit: int = 12) -> List[str]:
    headings: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped)
        if len(headings) >= limit:
            break
    return headings


def compact_preview(text: str, max_chars: int = 700) -> str:
    lines = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped:
            lines.append(stripped)
    preview = " ".join(lines)
    preview = re.sub(r"\s+", " ", preview).strip()
    if len(preview) > max_chars:
        preview = preview[:max_chars].rstrip() + "..."
    return preview


def page_id_for(path: Path, wiki_dir: Path) -> str:
    rel = path.relative_to(wiki_dir).as_posix()
    return re.sub(r"[^A-Za-z0-9]+", "_", rel).strip("_")


def build_catalog(
    *,
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> Dict[str, Any]:
    pages = []
    for path in iter_markdown_files(wiki_dir):
        text = read_text(path)
        rel = path.relative_to(wiki_dir).as_posix()
        pages.append(
            {
                "id": page_id_for(path, wiki_dir),
                "path": rel,
                "title": first_heading(text, rel),
                "headings": collect_headings(text),
                "preview": compact_preview(text),
                "chars": len(text),
            }
        )

    catalog = {
        "created_at": now_utc(),
        "wiki_dir": str(wiki_dir),
        "num_pages": len(pages),
        "pages": pages,
    }
    catalog_dir.mkdir(parents=True, exist_ok=True)
    write_text(catalog_dir / "catalog.json", json.dumps(catalog, ensure_ascii=False, indent=2))
    write_text(catalog_dir / "catalog.md", catalog_to_markdown(catalog))
    return catalog


def load_or_build_catalog(
    *,
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> Dict[str, Any]:
    path = catalog_dir / "catalog.json"
    if path.exists():
        try:
            return json.loads(read_text(path))
        except json.JSONDecodeError:
            return build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)
    return build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)


def catalog_to_markdown(catalog: Dict[str, Any]) -> str:
    lines = ["# GopherEye Wiki Catalog", ""]
    lines.append(f"Generated: {catalog.get('created_at')}")
    lines.append(f"Pages: {catalog.get('num_pages')}")
    lines.append("")
    for page in catalog.get("pages", []):
        lines.append(f"## {page['id']}")
        lines.append(f"- path: {page['path']}")
        lines.append(f"- title: {page['title']}")
        if page.get("headings"):
            lines.append("- headings:")
            for heading in page["headings"]:
                lines.append(f"  - {heading}")
        if page.get("preview"):
            lines.append(f"- preview: {page['preview']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def trim_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[TRUNCATED]\n"


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


def render_catalog_for_prompt(catalog: Dict[str, Any]) -> str:
    lines = []
    for page in catalog.get("pages", []):
        lines.append(f"ID: {page['id']}")
        lines.append(f"PATH: {page['path']}")
        lines.append(f"TITLE: {page['title']}")
        if page.get("headings"):
            lines.append("HEADINGS: " + " | ".join(page["headings"]))
        if page.get("preview"):
            lines.append("PREVIEW: " + page["preview"])
        lines.append("")
    return "\n".join(lines).strip()


def answer_openai(prompt: str, model: str) -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    from openai import OpenAI

    client = OpenAI()
    try:
        response = client.responses.create(
            model=model,
            input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        )
        text = getattr(response, "output_text", None)
        if text:
            return text.strip()
    except Exception:
        pass

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()


def answer_transformers(prompt: str, model_name: str, max_new_tokens: int = 768) -> str:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )

    messages = [{"role": "user", "content": prompt}]
    if hasattr(tokenizer, "apply_chat_template"):
        input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        input_text = prompt
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = output[0, inputs["input_ids"].shape[1] :]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def answer_qwen_vl(
    prompt: str,
    model_name: str,
    *,
    image_refs: Sequence[str] = (),
    max_new_tokens: int = 768,
) -> str:
    """Run Qwen2.5-VL with optional image inputs.

    `image_refs` should contain values that Qwen-VL utils can read, such as
    `file:///...`, `https://...`, or data URLs. Path resolution happens in the
    caller so this function stays model-focused.
    """
    import torch
    from qwen_vl_utils import process_vision_info
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    if model_name not in _QWEN_VL_CACHE:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True,
        )
        processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
        _QWEN_VL_CACHE[model_name] = (model, processor)
    else:
        model, processor = _QWEN_VL_CACHE[model_name]

    content: List[Dict[str, Any]] = []
    for image_ref in image_refs:
        content.append({"type": "image", "image": image_ref})
    content.append({"type": "text", "text": prompt})

    messages = [{"role": "user", "content": content}]
    text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )
    return (output_text[0] if output_text else "").strip()


def run_model(
    prompt: str,
    *,
    provider: str,
    model: str,
    max_new_tokens: int = 768,
) -> str:
    if provider == "openai":
        return answer_openai(prompt, model)
    if provider == "transformers":
        return answer_transformers(prompt, model, max_new_tokens=max_new_tokens)
    if provider in QWEN_VL_PROVIDERS:
        return answer_qwen_vl(prompt, model, max_new_tokens=max_new_tokens)
    if provider == "echo":
        return prompt
    raise ValueError(f"Unsupported provider: {provider}")


def run_model_with_images(
    prompt: str,
    *,
    provider: str,
    model: str,
    image_refs: Sequence[str] = (),
    max_new_tokens: int = 768,
) -> str:
    if image_refs and provider not in QWEN_VL_PROVIDERS:
        raise ValueError(
            f"Provider '{provider}' cannot receive image inputs in this prototype. "
            "Use --provider qwen-vl with a Qwen2.5-VL model."
        )
    if provider in QWEN_VL_PROVIDERS:
        return answer_qwen_vl(
            prompt,
            model,
            image_refs=image_refs,
            max_new_tokens=max_new_tokens,
        )
    return run_model(prompt, provider=provider, model=model, max_new_tokens=max_new_tokens)


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


def select_pages_with_model(
    question: str,
    *,
    catalog: Dict[str, Any],
    provider: str,
    model: str,
    max_selected_files: int = 6,
    max_new_tokens: int = 512,
) -> List[str]:
    prompt = f"""You are maintaining the GopherEye single-model wiki.

Task: choose the wiki pages that are most useful for answering the user's question.

Return ONLY a JSON array of page IDs. Do not explain.
Select at most {max_selected_files} page IDs.

Question:
{question}

Wiki catalog:
{render_catalog_for_prompt(catalog)}
"""
    raw = run_model(prompt, provider=provider, model=model, max_new_tokens=max_new_tokens)
    selected = parse_json_array(raw)
    valid_ids = {page["id"] for page in catalog.get("pages", [])}
    clean = []
    for item in selected:
        if isinstance(item, str) and item in valid_ids and item not in clean:
            clean.append(item)
    return clean[:max_selected_files]


def select_pages_keyword_fallback(
    question: str,
    *,
    catalog: Dict[str, Any],
    max_selected_files: int = 6,
) -> List[str]:
    tokens = set(re.findall(r"[A-Za-z0-9_]+", question.lower()))
    scored = []
    for page in catalog.get("pages", []):
        page_id = page.get("id", "").lower()
        path_text = page.get("path", "").lower()
        title_text = page.get("title", "").lower()
        headings_text = " ".join(page.get("headings", [])).lower()
        preview_text = page.get("preview", "").lower()
        score = 0
        for token in tokens:
            if token in page_id:
                score += 6
            if token in path_text:
                score += 6
            if token in title_text:
                score += 5
            if token in headings_text:
                score += 3
            score += min(preview_text.count(token), 4)
        scored.append((score, page["id"]))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [page_id for score, page_id in scored[:max_selected_files] if score > 0]


def read_pages_by_id(
    page_ids: Sequence[str],
    *,
    catalog: Dict[str, Any],
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    max_page_chars: int = 12000,
) -> List[Dict[str, Any]]:
    by_id = {page["id"]: page for page in catalog.get("pages", [])}
    pages = []
    for page_id in page_ids:
        meta = by_id.get(page_id)
        if not meta:
            continue
        path = wiki_dir / meta["path"]
        if not path.exists():
            continue
        text = trim_text(read_text(path), max_page_chars)
        pages.append({**meta, "text": text})
    return pages


def read_all_pages(
    *,
    catalog: Dict[str, Any],
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    max_page_chars: int = 12000,
) -> List[Dict[str, Any]]:
    ids = [page["id"] for page in catalog.get("pages", [])]
    return read_pages_by_id(ids, catalog=catalog, wiki_dir=wiki_dir, max_page_chars=max_page_chars)


def build_answer_prompt(question: str, pages: Sequence[Dict[str, Any]]) -> str:
    blocks = []
    for page in pages:
        blocks.append(
            f"""[PAGE id={page['id']} path={page['path']} title={page['title']}]
{page['text']}
[/PAGE]"""
        )
    context = "\n\n".join(blocks)
    return f"""You are the GopherEye single-model wiki assistant.

Use only the wiki pages provided below. If the wiki does not contain enough
evidence, say what is missing. Cite page paths in the answer.
Write the answer in English only.

Question:
{question}

Wiki pages:
{context}

Answer:"""


def ask(
    question: str,
    *,
    provider: str = "transformers",
    model: str = "Qwen/Qwen2.5-7B-Instruct",
    selection_mode: str = "model",
    max_selected_files: int = 6,
    max_page_chars: int = 12000,
    max_new_tokens: int = 768,
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> Dict[str, Any]:
    catalog = load_or_build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)

    if selection_mode == "full":
        selected_ids = [page["id"] for page in catalog.get("pages", [])]
    elif selection_mode == "keyword":
        selected_ids = select_pages_keyword_fallback(
            question,
            catalog=catalog,
            max_selected_files=max_selected_files,
        )
    elif selection_mode == "model":
        selected_ids = select_pages_with_model(
            question,
            catalog=catalog,
            provider=provider,
            model=model,
            max_selected_files=max_selected_files,
        )
        if not selected_ids:
            selected_ids = select_pages_keyword_fallback(
                question,
                catalog=catalog,
                max_selected_files=max_selected_files,
            )
    else:
        raise ValueError(f"Unsupported selection_mode: {selection_mode}")

    pages = read_pages_by_id(
        selected_ids,
        catalog=catalog,
        wiki_dir=wiki_dir,
        max_page_chars=max_page_chars,
    )
    prompt = build_answer_prompt(question, pages)
    answer = run_model(prompt, provider=provider, model=model, max_new_tokens=max_new_tokens)
    if contains_cjk(answer):
        answer = "The model did not produce an English answer. Please retry the request in English."

    return {
        "question": question,
        "provider": provider,
        "model": model,
        "selection_mode": selection_mode,
        "selected_pages": [
            {
                "id": page["id"],
                "path": page["path"],
                "title": page["title"],
            }
            for page in pages
        ],
        "answer": answer,
    }


def copy_source(
    source_path: Path,
    source_type: str,
    title: str | None,
    *,
    raw_dir: Path = DEFAULT_RAW_DIR,
) -> Dict[str, Any]:
    source_path = source_path.expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    source_type = slugify(source_type)
    digest = sha1_file(source_path)
    short = digest[:12]
    source_id = f"{timestamp_id()}_{slugify(source_path.stem)}_{short}"
    target_dir = raw_dir / "sources" / source_type
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{source_id}{source_path.suffix}"
    shutil.copy2(source_path, target_path)

    row = {
        "source_id": source_id,
        "source_type": source_type,
        "title": title or source_path.stem,
        "original_path": str(source_path),
        "stored_path": str(target_path.relative_to(raw_dir.parent)),
        "sha1": digest,
        "created_at": now_utc(),
    }

    manifest_path = raw_dir / "source_manifest.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def build_update_prompt(source_text: str, catalog: Dict[str, Any], selected_pages: Sequence[Dict[str, Any]]) -> str:
    page_blocks = []
    for page in selected_pages:
        page_blocks.append(
            f"""[CURRENT_WIKI_PAGE path={page['path']}]
{page['text']}
[/CURRENT_WIKI_PAGE]"""
        )
    return f"""You are maintaining the GopherEye single-model wiki.

Read the new raw source and the related current wiki pages. Write a markdown
draft that a human can review before editing the curated wiki.
Write the draft in English only.

The draft must include:
- short source summary
- concrete wiki pages that should be updated
- exact facts or decisions to add
- contradictions or unclear points
- suggested new pages, if any

Wiki catalog:
{render_catalog_for_prompt(catalog)}

Related current wiki pages:
{chr(10).join(page_blocks)}

New raw source:
{source_text}

Draft update:"""


def suggest_updates(
    source_path: Path,
    *,
    provider: str = "transformers",
    model: str = "Qwen/Qwen2.5-7B-Instruct",
    max_selected_files: int = 6,
    max_source_chars: int = 24000,
    max_page_chars: int = 12000,
    max_new_tokens: int = 1200,
    wiki_dir: Path = DEFAULT_WIKI_DIR,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
    output_dir: Path = DEFAULT_DRAFT_DIR,
) -> Path:
    source_path = source_path.expanduser()
    source_text = trim_text(read_text(source_path), max_source_chars)
    catalog = load_or_build_catalog(wiki_dir=wiki_dir, catalog_dir=catalog_dir)

    selection_question = (
        "Which wiki pages should be updated after reading this source? "
        + compact_preview(source_text, max_chars=1200)
    )
    selected_ids = select_pages_with_model(
        selection_question,
        catalog=catalog,
        provider=provider,
        model=model,
        max_selected_files=max_selected_files,
    )
    if not selected_ids:
        selected_ids = select_pages_keyword_fallback(
            selection_question,
            catalog=catalog,
            max_selected_files=max_selected_files,
        )
    pages = read_pages_by_id(
        selected_ids,
        catalog=catalog,
        wiki_dir=wiki_dir,
        max_page_chars=max_page_chars,
    )
    prompt = build_update_prompt(source_text, catalog, pages)
    draft = run_model(prompt, provider=provider, model=model, max_new_tokens=max_new_tokens)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{timestamp_id()}_{slugify(source_path.stem)}_draft.md"
    out_path = output_dir / out_name
    header = f"""# Wiki Update Draft

- source: `{source_path}`
- provider: `{provider}`
- model: `{model}`
- created_at: `{now_utc()}`
- selected_pages: {json.dumps([page['path'] for page in pages], ensure_ascii=False)}

---

"""
    write_text(out_path, header + draft.strip() + "\n")
    return out_path


def print_result(result: Dict[str, Any], *, as_json: bool = False) -> None:
    if as_json:
        safe_print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    safe_print("# Answer\n")
    safe_print(result["answer"])
    safe_print("\n# Selected Pages\n")
    for page in result.get("selected_pages", []):
        safe_print(f"- {page['path']} ({page['id']})")
