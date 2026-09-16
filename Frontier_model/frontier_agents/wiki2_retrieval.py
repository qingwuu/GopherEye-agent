from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from src.gophereye_runtime.utils import now_utc, safe_print, write_json, write_jsonl


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WIKI2_DIR = REPO_ROOT / "wiki2"
DEFAULT_WIKI2_CATALOG_DIR = REPO_ROOT / "catalog" / "wiki2"
DEFAULT_RETRIEVAL_PROFILE_NAME = "retrieval_profiles.json"

PARENT_PAGE_TYPE = "detailed_parent_page"
DETAIL_PAGE_TYPE = "detailed_section_page"

VISUAL_REQUIRED_PATHS = [
    "procedures/diagnosis_sop/diagnostic_order.md",
    "procedures/diagnosis_sop/observation_before_interpretation.md",
    "procedures/diagnosis_sop/differential_frame.md",
    "procedures/image_and_evidence_sop/minimum_useful_image.md",
    "procedures/image_and_evidence_sop/single_surface_sufficiency.md",
]

VISUAL_COMPARISON_REQUIRED_PATHS = [
    "procedures/diagnosis_sop/diagnostic_order.md",
    "procedures/diagnosis_sop/differential_frame.md",
    "procedures/image_and_evidence_sop/minimum_useful_image.md",
    "procedures/image_and_evidence_sop/single_surface_sufficiency.md",
]

VISUAL_GENERAL_DETAIL_PATHS = [
    "disease/powdery_mildew/visual_evidence_thresholds.md",
    "disease/downy_mildew/visual_evidence_thresholds.md",
    "disease/healthy/minimum_evidence_for_healthy_label.md",
    "disease/others/visual_patterns_to_route_here.md",
]

DISEASE_DETAIL_ROLES = [
    "visual_evidence_thresholds",
    "feature_checklist",
    "differentials",
    "image_requests",
]

STAGE1_INTAKE_PATHS = [
    "procedures/diagnosis_sop/diagnostic_order.md",
    "procedures/diagnosis_sop/observation_before_interpretation.md",
    "procedures/image_and_evidence_sop/minimum_useful_image.md",
]

STAGE2_TERMINAL_PROCEDURE_PATHS = [
    "procedures/diagnosis_sop/differential_frame.md",
    "procedures/image_and_evidence_sop/single_surface_sufficiency.md",
]

TREATMENT_POLICY_PATHS = [
    "reference/source_policy/treatment_hard_rules.md",
    "reference/source_policy/resource_review_requirements.md",
]

DISEASE_HINTS = {
    "powdery_mildew": [
        "powdery",
        "white-gray",
        "white grey",
        "dusty",
        "conidia",
        "mycelium",
        "\u767d\u7c89",
        "\u767d\u7c89\u75c5",
    ],
    "downy_mildew": [
        "downy",
        "oil spot",
        "oily",
        "angular",
        "cottony",
        "sporulation",
        "\u971c\u9709",
        "\u971c\u9709\u75c5",
    ],
    "healthy": [
        "healthy",
        "normal",
        "artifact",
        "variation",
        "\u5065\u5eb7",
        "\u6b63\u5e38",
    ],
    "others": [
        "other",
        "unresolved",
        "noncanonical",
        "unknown",
        "\u5176\u4ed6",
        "\u672a\u77e5",
        "\u4e0d\u786e\u5b9a",
    ],
}

QUERY_HINTS = [
    (["treatment", "management", "spray", "fungicide", "rate", "\u6cbb\u7597", "\u7ba1\u7406", "\u7528\u836f", "\u9632\u6cbb"], "treatment management source policy reviewed resource"),
    (["diagnosis", "diagnose", "differential", "compare", "\u8bca\u65ad", "\u9274\u522b", "\u533a\u522b", "\u6bd4\u8f83"], "diagnosis differential evidence threshold feature checklist"),
    (["surface", "upper", "lower", "adaxial", "abaxial", "underside", "\u6b63\u9762", "\u80cc\u9762", "\u8868\u9762"], "leaf surface single surface opposite surface image evidence"),
    (["source", "citation", "paper", "literature", "\u6765\u6e90", "\u6587\u732e", "\u8bc1\u636e"], "source policy citation reviewed resource"),
    (["terminology", "term", "vocabulary", "\u672f\u8bed", "\u8bcd\u6c47"], "terminology controlled vocabulary"),
]

SECTION_ROLE_ALIASES = {
    "differentials_to_check": "differentials",
    "visual_patterns_to_route_here": "visual_patterns",
    "minimum_evidence_for_healthy_label": "minimum_evidence",
    "app_facing_rule": "treatment_rule",
    "required_links": "treatment_links",
    "treatment_hard_rules": "treatment_policy",
    "resource_review_requirements": "treatment_policy",
}

ROLE_MATCH_ALIASES = {
    "visual_evidence_thresholds": ["visual_evidence_thresholds", "minimum_evidence", "visual_patterns"],
    "feature_checklist": ["feature_checklist", "required_handling"],
    "differentials": ["differentials"],
    "image_requests": ["image_requests"],
    "visual_patterns": ["visual_patterns", "visual_evidence_thresholds"],
    "required_handling": ["required_handling", "feature_checklist"],
    "promotion_rule": ["promotion_rule"],
    "minimum_evidence": ["minimum_evidence", "visual_evidence_thresholds"],
}

SUPPORT_RANK = {
    "negative": 0,
    "weakened": 1,
    "unresolved": 2,
    "possible": 3,
    "supporting": 4,
}

DEFAULT_TERMINAL_ROLE_POLICY = {
    "primary": ["visual_evidence_thresholds", "feature_checklist", "differentials", "image_requests"],
    "differential": ["visual_evidence_thresholds", "differentials", "image_requests"],
    "weakened": ["visual_evidence_thresholds", "differentials", "image_requests"],
    "negative": ["visual_evidence_thresholds", "differentials"],
    "unresolved": ["visual_evidence_thresholds", "differentials"],
}

DEFAULT_ROLE_LIMITS = {
    "primary": 4,
    "differential": 3,
    "weakened": 3,
    "negative": 2,
    "unresolved": 3,
}

STATUS_RANK = {
    "primary": 5,
    "differential": 4,
    "unresolved": 3,
    "weakened": 2,
    "negative": 2,
    "irrelevant": 0,
}

STATUS_SUPPORT_LABEL = {
    "primary": "supporting",
    "differential": "possible",
    "unresolved": "unresolved",
    "weakened": "weakened",
    "negative": "negative",
    "irrelevant": "negative",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def iter_markdown_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def strip_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n([\s\S]*?)\n---\s*\n?", text)
    if not match:
        return {}, text
    return parse_frontmatter(match.group(1)), text[match.end():]


def parse_frontmatter(raw: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    current_list_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        list_match = re.match(r"^\s*-\s*(.+?)\s*$", line)
        if list_match and current_list_key:
            data.setdefault(current_list_key, []).append(list_match.group(1).strip())
            continue
        key_match = re.match(r"^([A-Za-z0-9_ -]+):\s*(.*?)\s*$", line)
        if not key_match:
            continue
        key = key_match.group(1).strip().replace("-", "_")
        value = key_match.group(2).strip()
        if value:
            data[key] = value
            current_list_key = None
        else:
            data[key] = []
            current_list_key = key
    return data


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def compact_preview(text: str, max_chars: int = 500) -> str:
    body = remove_search_cue_block(strip_frontmatter(text)[1])
    lines = []
    in_code = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not stripped:
            continue
        lines.append(stripped)
    preview = re.sub(r"\s+", " ", " ".join(lines)).strip()
    if len(preview) > max_chars:
        return preview[:max_chars].rstrip() + "..."
    return preview


def page_id_for(path: Path, wiki2_dir: Path) -> str:
    rel = path.relative_to(wiki2_dir).as_posix()
    return re.sub(r"[^A-Za-z0-9]+", "_", rel).strip("_")


def extract_search_cues(text: str) -> str:
    cues = re.findall(r"(?im)^\s*search_cues:\s*(.+?)\s*$", text)
    return " ".join(cue.strip() for cue in cues if cue.strip())


def extract_markdown_links(text: str) -> List[str]:
    links = []
    for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)|!\[[^\]]*\]\(([^)]+)\)", text):
        target = (match.group(1) or match.group(2) or "").strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        links.append(target)
    return links


def resolve_wiki2_relative(wiki2_dir: Path, source_path: Path, target: str | None) -> str | None:
    if not target:
        return None
    clean = str(target).split("#", 1)[0].strip()
    if not clean:
        return None
    candidate = (source_path.parent / clean).resolve(strict=False)
    try:
        return candidate.relative_to(wiki2_dir.resolve(strict=False)).as_posix()
    except ValueError:
        return None


def domain_for(rel_path: str) -> str:
    return rel_path.split("/", 1)[0] if "/" in rel_path else "root"


def group_for(rel_path: str) -> str:
    parts = rel_path.split("/")
    if len(parts) >= 3:
        return "/".join(parts[:2])
    if len(parts) >= 2:
        return parts[0]
    return "root"


def section_role_for(rel_path: str, source_section: str | None) -> str:
    stem = Path(rel_path).stem
    if stem == "index" and source_section:
        stem = re.sub(r"[^A-Za-z0-9]+", "_", source_section.lower()).strip("_")
    return SECTION_ROLE_ALIASES.get(stem, stem)


def build_page_record(path: Path, wiki2_dir: Path) -> Dict[str, Any]:
    text = read_text(path)
    frontmatter, body = strip_frontmatter(text)
    rel_path = path.relative_to(wiki2_dir).as_posix()
    title = str(frontmatter.get("title") or first_heading(body, rel_path))
    parent_path = resolve_wiki2_relative(wiki2_dir, path, frontmatter.get("parent_page"))
    page_type = str(frontmatter.get("page_type") or "page")
    source_section = str(frontmatter.get("source_section") or "").strip() or None
    search_cues = extract_search_cues(body)
    links = [
        resolved
        for resolved in (resolve_wiki2_relative(wiki2_dir, path, link) for link in extract_markdown_links(body))
        if resolved
    ]
    disease_id = str(frontmatter.get("disease_id") or "").strip() or None
    section_role = section_role_for(rel_path, source_section)
    preview = compact_preview(text)
    routing_text = " ".join(
        item
        for item in [
            rel_path,
            title,
            page_type,
            source_section or "",
            disease_id or "",
            section_role,
            search_cues,
            preview,
        ]
        if item
    )
    return {
        "id": page_id_for(path, wiki2_dir),
        "path": rel_path,
        "page_type": page_type,
        "title": title,
        "parent_path": parent_path,
        "source_wiki_path": frontmatter.get("source_wiki_path"),
        "source_section": source_section,
        "review_status": frontmatter.get("review_status"),
        "last_updated": frontmatter.get("last_updated"),
        "disease_id": disease_id,
        "domain": domain_for(rel_path),
        "group": group_for(rel_path),
        "section_role": section_role,
        "search_cues": search_cues,
        "links": links,
        "preview": preview,
        "chars": len(text),
        "routing_text": routing_text,
    }


def _normalized_string_list(value: Any) -> List[str]:
    items = value if isinstance(value, list) else [value] if value else []
    out: List[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _normalized_signal_list(value: Any) -> List[str]:
    out: List[str] = []
    for item in _normalized_string_list(value):
        normalized = normalize_signal_name(item)
        if normalized and normalized not in out:
            out.append(normalized)
    return out


def _normalized_role_list(value: Any) -> List[str]:
    out: List[str] = []
    for item in _normalized_string_list(value):
        role = normalize_detail_role(item)
        if role and role not in out:
            out.append(role)
    return out


def normalize_terminal_roles(value: Any, default_policy: Dict[str, List[str]]) -> Dict[str, List[str]]:
    role_map = value if isinstance(value, dict) else {}
    normalized: Dict[str, List[str]] = {}
    for status, default_roles in default_policy.items():
        normalized[status] = _normalized_role_list(role_map.get(status) or default_roles)
    return normalized


def normalize_role_limits(value: Any) -> Dict[str, int]:
    limits = dict(DEFAULT_ROLE_LIMITS)
    if not isinstance(value, dict):
        return limits
    for status, raw_limit in value.items():
        if status not in limits:
            continue
        try:
            limits[status] = max(1, int(raw_limit))
        except (TypeError, ValueError):
            continue
    return limits


def normalize_entity_profile(raw: Dict[str, Any], default_policy: Dict[str, List[str]]) -> Dict[str, Any] | None:
    entity_id = str(raw.get("entity_id") or raw.get("disease_id") or "").strip()
    if not entity_id:
        return None
    entity_type = str(raw.get("entity_type") or "disease").strip() or "disease"
    try:
        priority = int(raw.get("priority", 50))
    except (TypeError, ValueError):
        priority = 50
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "aliases": _normalized_string_list(raw.get("aliases")),
        "support_signals": _normalized_signal_list(raw.get("support_signals")),
        "weaken_signals": _normalized_signal_list(raw.get("weaken_signals")),
        "route_when_uncertain": bool(raw.get("route_when_uncertain")),
        "priority": priority,
        "terminal_roles": normalize_terminal_roles(raw.get("terminal_roles"), default_policy),
        "role_limits": normalize_role_limits(raw.get("role_limits")),
    }


def load_retrieval_profiles(wiki2_dir: Path = DEFAULT_WIKI2_DIR) -> Dict[str, Any]:
    profile_path = wiki2_dir / DEFAULT_RETRIEVAL_PROFILE_NAME
    if not profile_path.exists():
        return {
            "schema_version": 0,
            "profile_path": str(profile_path),
            "default_role_policy": DEFAULT_TERMINAL_ROLE_POLICY,
            "entities": [],
            "load_status": "missing",
        }
    try:
        raw = json.loads(read_text(profile_path))
    except json.JSONDecodeError as exc:
        return {
            "schema_version": 0,
            "profile_path": str(profile_path),
            "default_role_policy": DEFAULT_TERMINAL_ROLE_POLICY,
            "entities": [],
            "load_status": f"invalid_json:{exc}",
        }
    default_policy = normalize_terminal_roles(raw.get("default_role_policy"), DEFAULT_TERMINAL_ROLE_POLICY)
    entities = []
    for item in raw.get("entities", []) if isinstance(raw.get("entities"), list) else []:
        if not isinstance(item, dict):
            continue
        normalized = normalize_entity_profile(item, default_policy)
        if normalized:
            entities.append(normalized)
    return {
        "schema_version": raw.get("schema_version", 1),
        "profile_path": str(profile_path),
        "default_role_policy": default_policy,
        "entities": entities,
        "load_status": "ok",
    }


def build_catalog(
    *,
    wiki2_dir: Path = DEFAULT_WIKI2_DIR,
    catalog_dir: Path = DEFAULT_WIKI2_CATALOG_DIR,
) -> Dict[str, Any]:
    pages = [build_page_record(path, wiki2_dir) for path in iter_markdown_files(wiki2_dir)]
    pages.sort(key=lambda page: page["path"])
    retrieval_profiles = load_retrieval_profiles(wiki2_dir)

    children_by_parent: Dict[str, List[str]] = {}
    for page in pages:
        parent = page.get("parent_path")
        if parent:
            children_by_parent.setdefault(str(parent), []).append(page["path"])
    for children in children_by_parent.values():
        children.sort()

    catalog = {
        "created_at": now_utc(),
        "wiki2_dir": str(wiki2_dir),
        "num_pages": len(pages),
        "num_detailed_pages": sum(1 for page in pages if page.get("page_type") == DETAIL_PAGE_TYPE),
        "num_parent_pages": sum(1 for page in pages if page.get("page_type") == PARENT_PAGE_TYPE),
        "children_by_parent": children_by_parent,
        "entity_profiles": retrieval_profiles.get("entities", []),
        "retrieval_profile_meta": {
            "schema_version": retrieval_profiles.get("schema_version"),
            "profile_path": retrieval_profiles.get("profile_path"),
            "load_status": retrieval_profiles.get("load_status"),
            "default_role_policy": retrieval_profiles.get("default_role_policy"),
        },
        "pages": pages,
    }
    write_json(catalog_dir / "catalog.json", catalog)
    write_jsonl(
        catalog_dir / "sections.jsonl",
        [page for page in pages if page.get("page_type") == DETAIL_PAGE_TYPE],
    )
    return catalog


def load_or_build_catalog(
    *,
    wiki2_dir: Path = DEFAULT_WIKI2_DIR,
    catalog_dir: Path = DEFAULT_WIKI2_CATALOG_DIR,
) -> Dict[str, Any]:
    catalog_path = catalog_dir / "catalog.json"
    if catalog_path.exists():
        try:
            catalog = json.loads(read_text(catalog_path))
            if isinstance(catalog, dict) and "entity_profiles" in catalog:
                return catalog
        except json.JSONDecodeError:
            pass
    return build_catalog(wiki2_dir=wiki2_dir, catalog_dir=catalog_dir)


def expand_query(query: str) -> str:
    lower = query.lower()
    hints: List[str] = []
    for disease_id, needles in DISEASE_HINTS.items():
        if any(needle in lower for needle in needles):
            hints.append(disease_id.replace("_", " "))
    for needles, hint in QUERY_HINTS:
        if any(needle in lower for needle in needles):
            hints.append(hint)
    return f"{query}\nRetrieval hints: {', '.join(dict.fromkeys(hints))}" if hints else query


def tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def infer_disease_candidates(*texts: str) -> List[str]:
    blob = " ".join(texts).lower()
    candidates = []
    for disease_id, needles in DISEASE_HINTS.items():
        if disease_id in blob or disease_id.replace("_", " ") in blob or any(needle in blob for needle in needles):
            candidates.append(disease_id)
    return candidates


def is_treatment_query(query: str, route: Dict[str, Any] | None = None) -> bool:
    task_type = str((route or {}).get("task_type") or "")
    lower = query.lower()
    return task_type == "treatment" or any(
        token in lower
        for token in ["treatment", "management", "spray", "fungicide", "rate", "\u6cbb\u7597", "\u7ba1\u7406", "\u7528\u836f"]
    )


def is_visual_query(query: str, route: Dict[str, Any] | None = None, image_refs: Sequence[str] = ()) -> bool:
    task_type = str((route or {}).get("task_type") or "")
    lower = query.lower()
    return bool(image_refs) or task_type == "visual_intake_or_diagnosis" or any(
        token in lower for token in ["diagnosis", "diagnose", "image", "leaf", "surface", "symptom"]
    )


def score_page(page: Dict[str, Any], query: str, route: Dict[str, Any] | None = None) -> int:
    tokens = tokenize(query)
    if not tokens:
        return 0
    fields = [
        ("path", 7),
        ("title", 6),
        ("source_section", 6),
        ("disease_id", 8),
        ("section_role", 8),
        ("search_cues", 4),
        ("preview", 2),
    ]
    score = 0
    for field, weight in fields:
        text = str(page.get(field) or "").lower()
        for token in tokens:
            if token and token in text:
                score += weight
    if page.get("page_type") == PARENT_PAGE_TYPE:
        score -= 50
    task_type = str((route or {}).get("task_type") or "")
    if task_type == "visual_intake_or_diagnosis" and page.get("domain") in {"disease", "procedures", "reference"}:
        score += 4
    return score


def page_by_path(catalog: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(page["path"]): page for page in catalog.get("pages", [])}


def parent_paths_for(pages: Sequence[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for page in pages:
        parent = page.get("parent_path")
        if parent and parent not in out:
            out.append(str(parent))
    return out


def disease_detail_paths(disease_id: str) -> List[str]:
    base = f"disease/{disease_id}"
    return [f"{base}/{role}.md" for role in DISEASE_DETAIL_ROLES]


def canonical_disease_id(value: Any) -> str | None:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in DISEASE_HINTS:
        return text
    for disease_id, needles in DISEASE_HINTS.items():
        if disease_id in text or any(str(needle).lower().replace(" ", "_") in text for needle in needles):
            return disease_id
    return None


def normalize_support(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in SUPPORT_RANK:
        return text
    if text in {"supported", "present", "likely"}:
        return "supporting"
    if text in {"weak", "less_likely", "not_supported"}:
        return "weakened"
    if text in {"unknown", "uncertain", "ambiguous"}:
        return "unresolved"
    return "possible"


def normalize_detail_role(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    role_aliases = {
        "visual_thresholds": "visual_evidence_thresholds",
        "evidence_thresholds": "visual_evidence_thresholds",
        "thresholds": "visual_evidence_thresholds",
        "checklist": "feature_checklist",
        "feature_checks": "feature_checklist",
        "differential": "differentials",
        "differentials_to_check": "differentials",
        "image_request": "image_requests",
        "visual_patterns_to_route_here": "visual_patterns",
        "required_links": "treatment_links",
    }
    text = role_aliases.get(text, text)
    allowed = {
        "visual_evidence_thresholds",
        "feature_checklist",
        "differentials",
        "image_requests",
        "visual_patterns",
        "required_handling",
        "promotion_rule",
        "minimum_evidence",
        "localization",
        "treatment_link",
        "treatment_rule",
        "treatment_links",
    }
    return text if text in allowed else None


def disease_paths_for_roles(catalog: Dict[str, Any], disease_id: str, roles: Sequence[str]) -> List[str]:
    pages = [
        page
        for page in catalog.get("pages", [])
        if page.get("page_type") == DETAIL_PAGE_TYPE and page.get("disease_id") == disease_id
    ]
    paths: List[str] = []
    by_path = page_by_path(catalog)
    for raw_role in roles:
        role = normalize_detail_role(raw_role)
        if not role:
            continue
        direct = f"disease/{disease_id}/{role}.md"
        if direct in by_path and direct not in paths:
            paths.append(direct)
            continue
        aliases = ROLE_MATCH_ALIASES.get(role, [role])
        for alias in aliases:
            match = next((page for page in pages if page.get("section_role") == alias), None)
            if match and match["path"] not in paths:
                paths.append(match["path"])
                break
    return paths


def treatment_detail_paths(disease_id: str) -> List[str]:
    return [
        f"disease/{disease_id}/treatment_link.md",
        f"treatment/{disease_id}/app_facing_rule.md",
        f"treatment/{disease_id}/required_links.md",
    ]


def add_selected(
    selected: List[Dict[str, Any]],
    page: Dict[str, Any] | None,
    *,
    reason: str,
    max_pages: int,
    per_parent_counts: Dict[str, int],
    max_children_per_parent: int,
    required: bool = False,
) -> None:
    if not page or page.get("page_type") != DETAIL_PAGE_TYPE:
        return
    if any(item["path"] == page["path"] for item in selected):
        return
    parent = str(page.get("parent_path") or page.get("group") or "")
    count = per_parent_counts.get(parent, 0)
    if not required and parent and count >= max_children_per_parent:
        return
    if len(selected) >= max_pages:
        return
    enriched = dict(page)
    enriched["selection_reason"] = reason
    selected.append(enriched)
    if parent:
        per_parent_counts[parent] = count + 1


def required_paths_for_query(
    *,
    query: str,
    route: Dict[str, Any] | None,
    image_refs: Sequence[str],
    disease_candidates: Sequence[str],
) -> List[str]:
    paths: List[str] = []
    if is_visual_query(query, route, image_refs):
        paths.extend(VISUAL_COMPARISON_REQUIRED_PATHS if len(disease_candidates) > 1 else VISUAL_REQUIRED_PATHS)
        if disease_candidates:
            for disease_id in disease_candidates:
                detail_count = 2 if len(disease_candidates) > 1 else 3
                paths.extend(disease_detail_paths(disease_id)[:detail_count])
        else:
            paths.extend(VISUAL_GENERAL_DETAIL_PATHS)
    if is_treatment_query(query, route):
        diseases = list(disease_candidates) or ["powdery_mildew", "downy_mildew", "healthy", "others"]
        for disease_id in diseases:
            paths.extend(treatment_detail_paths(disease_id))
        paths.extend(TREATMENT_POLICY_PATHS)
    if any(token in query.lower() for token in ["terminology", "vocabulary", "term"]):
        paths.append("reference/terminology/index.md")
    return list(dict.fromkeys(paths))


def top_parent_candidates(catalog: Dict[str, Any], query: str, route: Dict[str, Any] | None, limit: int = 6) -> List[Dict[str, Any]]:
    parents = [page for page in catalog.get("pages", []) if page.get("page_type") == PARENT_PAGE_TYPE]
    scored = [(score_page(page, query, route), page) for page in parents]
    scored.sort(key=lambda item: (-item[0], item[1]["path"]))
    return [
        {
            "path": page["path"],
            "title": page["title"],
            "score": score,
        }
        for score, page in scored[:limit]
        if score > -40
    ]


ABSENT_SIGNAL_ALIASES: Dict[str, str] = {}


def normalize_signal_name(value: Any) -> str | None:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or None


def normalize_absent_signal_name(value: Any) -> str | None:
    text = normalize_signal_name(value)
    if not text:
        return None
    if text in ABSENT_SIGNAL_ALIASES:
        return ABSENT_SIGNAL_ALIASES[text]
    if text.endswith("_present"):
        return text[: -len("_present")] + "_absent"
    return text


def visual_signal_sets(visual_signal_vector: Dict[str, Any]) -> tuple[set[str], set[str]]:
    """Return positive and negative visual signals without mixing absent fields."""
    positive: set[str] = set()
    negative: set[str] = set()

    for raw_signal in visual_signal_vector.get("positive_signals", []) if isinstance(visual_signal_vector, dict) else []:
        signal = normalize_signal_name(raw_signal)
        if signal:
            positive.add(signal)
    for raw_signal in visual_signal_vector.get("pattern_signals", []) if isinstance(visual_signal_vector, dict) else []:
        signal = normalize_signal_name(raw_signal)
        if signal:
            positive.add(signal)
    for raw_signal in visual_signal_vector.get("negative_signals", []) if isinstance(visual_signal_vector, dict) else []:
        signal = normalize_absent_signal_name(raw_signal)
        if signal:
            negative.add(signal)

    for raw_signal in visual_signal_vector.get("global_visual_signals", []) if isinstance(visual_signal_vector, dict) else []:
        signal = normalize_signal_name(raw_signal)
        if not signal:
            continue
        if signal.endswith("_absent") or signal in {
            "white_gray_powdery_colonies_absent",
            "cottony_downy_sporulation_absent",
            "downy_sporulation_absent",
            "powdery_colonies_absent",
        }:
            negative.add(signal)
        else:
            positive.add(signal)

    observations = visual_signal_vector.get("surface_observations") if isinstance(visual_signal_vector, dict) else []
    for observation in observations if isinstance(observations, list) else []:
        if not isinstance(observation, dict):
            continue
        for raw_signal in observation.get("signals_present", []) if isinstance(observation.get("signals_present"), list) else []:
            signal = normalize_signal_name(raw_signal)
            if signal and not signal.endswith("_absent"):
                positive.add(signal)
            elif signal:
                negative.add(signal)
        for raw_signal in observation.get("signals_absent", []) if isinstance(observation.get("signals_absent"), list) else []:
            signal = normalize_absent_signal_name(raw_signal)
            if signal:
                negative.add(signal)

    return positive, negative


def _has_any_signal(tokens: set[str], names: Sequence[str]) -> bool:
    return any(name in tokens for name in names)


def _merge_candidate(
    candidates: Dict[str, Dict[str, Any]],
    disease_id: str,
    *,
    support: str,
    roles: Sequence[str],
    reason: str,
) -> None:
    support = normalize_support(support)
    current = candidates.setdefault(
        disease_id,
        {
            "disease_id": disease_id,
            "support": support,
            "reasons": [],
            "roles": [],
        },
    )
    if SUPPORT_RANK[support] > SUPPORT_RANK.get(str(current.get("support")), -1):
        current["support"] = support
    if reason and reason not in current["reasons"]:
        current["reasons"].append(reason)
    for raw_role in roles:
        role = normalize_detail_role(raw_role)
        if role and role not in current["roles"]:
            current["roles"].append(role)


def entity_profiles_for_catalog(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    profiles = catalog.get("entity_profiles")
    return [profile for profile in profiles if isinstance(profile, dict)] if isinstance(profiles, list) else []


def canonical_entity_id(value: Any, profiles: Sequence[Dict[str, Any]]) -> str | None:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not text:
        return None
    for profile in profiles:
        entity_id = str(profile.get("entity_id") or "")
        if text == entity_id.lower().replace("-", "_").replace(" ", "_"):
            return entity_id
        for alias in profile.get("aliases", []) if isinstance(profile.get("aliases"), list) else []:
            alias_text = str(alias or "").strip().lower().replace("-", "_").replace(" ", "_")
            if text == alias_text:
                return entity_id
    return None


def visual_query_blob(*texts: Any) -> str:
    return " ".join(str(text or "") for text in texts).lower()


def text_matches_profile_alias(text: str, profile: Dict[str, Any]) -> List[str]:
    lower = text.lower()
    matches: List[str] = []
    entity_id = str(profile.get("entity_id") or "")
    needles = [entity_id.replace("_", " "), entity_id]
    needles.extend(str(alias or "") for alias in profile.get("aliases", []) if alias)
    for needle in needles:
        normalized = str(needle or "").strip().lower()
        if normalized and normalized in lower and normalized not in matches:
            matches.append(normalized)
    return matches


def candidate_hints_by_entity(
    visual_signal_vector: Dict[str, Any],
    profiles: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    hints: Dict[str, Dict[str, Any]] = {}
    hint_items = visual_signal_vector.get("candidate_hints") if isinstance(visual_signal_vector, dict) else []
    for hint in hint_items if isinstance(hint_items, list) else []:
        if not isinstance(hint, dict):
            continue
        entity_id = canonical_entity_id(hint.get("entity_id") or hint.get("disease_id") or hint.get("entity"), profiles)
        if not entity_id:
            continue
        current = hints.setdefault(entity_id, {"supports": [], "roles": [], "reasons": []})
        support = normalize_support(hint.get("support"))
        if support not in current["supports"]:
            current["supports"].append(support)
        for role in _normalized_role_list(hint.get("needed_detail_roles")):
            if role not in current["roles"]:
                current["roles"].append(role)
        for reason in _normalized_string_list(hint.get("reasons"))[:3]:
            if reason not in current["reasons"]:
                current["reasons"].append(reason)
    return hints


def requested_roles_by_entity(
    visual_signal_vector: Dict[str, Any],
    profiles: Sequence[Dict[str, Any]],
) -> Dict[str, List[str]]:
    requests: Dict[str, List[str]] = {}
    request_items = visual_signal_vector.get("needed_detail_pages") if isinstance(visual_signal_vector, dict) else []
    for request in request_items if isinstance(request_items, list) else []:
        if not isinstance(request, dict):
            continue
        entity_id = canonical_entity_id(request.get("entity_id") or request.get("disease_id") or request.get("entity"), profiles)
        if not entity_id:
            continue
        requests.setdefault(entity_id, [])
        for role in _normalized_role_list(request.get("roles")):
            if role not in requests[entity_id]:
                requests[entity_id].append(role)
    return requests


def strongest_hint_support(hints: Sequence[str]) -> str | None:
    if not hints:
        return None
    return max(hints, key=lambda support: SUPPORT_RANK.get(support, 0))


def uncertainty_signal_present(positive_signals: set[str], negative_signals: set[str]) -> bool:
    uncertainty_markers = ["uncertain", "unresolved", "noncanonical", "insufficient", "ambiguous"]
    all_signals = positive_signals | negative_signals
    return any(any(marker in signal for marker in uncertainty_markers) for signal in all_signals)


def score_entity_profile(
    profile: Dict[str, Any],
    *,
    positive_signals: set[str],
    negative_signals: set[str],
    text_blob: str,
    hint: Dict[str, Any] | None,
    requested_roles: Sequence[str],
) -> Dict[str, Any]:
    support_signals = set(_normalized_signal_list(profile.get("support_signals")))
    weaken_signals = set(_normalized_signal_list(profile.get("weaken_signals")))
    support_matches = sorted(support_signals & positive_signals)
    weaken_matches = sorted(weaken_signals & (positive_signals | negative_signals))
    alias_matches = text_matches_profile_alias(text_blob, profile)
    hint_support = strongest_hint_support((hint or {}).get("supports", []))
    hint_roles = _normalized_role_list((hint or {}).get("roles", []))
    hint_reasons = _normalized_string_list((hint or {}).get("reasons", []))[:3]
    uncertain_bonus = 0.75 if profile.get("route_when_uncertain") and uncertainty_signal_present(positive_signals, negative_signals) else 0.0
    hint_bonus = {
        "supporting": 1.5,
        "possible": 0.75,
        "unresolved": 0.5,
        "weakened": 0.25,
        "negative": 0.0,
    }.get(str(hint_support or ""), 0.0)
    score = (
        len(support_matches) * 3.0
        - len(weaken_matches) * 2.0
        + len(alias_matches) * 1.0
        + hint_bonus
        + uncertain_bonus
    )

    status = "irrelevant"
    if support_matches:
        if weaken_matches:
            status = "differential" if score >= 1.0 else "weakened"
        elif score >= 5.0 or hint_support == "supporting" or len(support_matches) >= 2:
            status = "primary"
        else:
            status = "differential"
    elif weaken_matches:
        status = "negative" if hint_support == "negative" else "weakened"
    elif hint_support in {"supporting", "possible"}:
        status = "primary" if hint_support == "supporting" else "differential"
    elif hint_support in {"unresolved", "weakened", "negative"}:
        status = hint_support
    elif alias_matches:
        status = "differential"
    elif requested_roles and profile.get("route_when_uncertain"):
        status = "unresolved"
    elif profile.get("route_when_uncertain") and uncertainty_signal_present(positive_signals, negative_signals):
        status = "unresolved"

    if status == "negative" and (support_matches or alias_matches):
        status = "weakened"

    roles = []
    for role in hint_roles + _normalized_role_list(requested_roles):
        if role not in roles:
            roles.append(role)

    return {
        "entity_id": profile.get("entity_id"),
        "disease_id": profile.get("entity_id") if profile.get("entity_type") == "disease" else None,
        "entity_type": profile.get("entity_type"),
        "status": status,
        "support": STATUS_SUPPORT_LABEL.get(status, "possible"),
        "score": round(score, 3),
        "support_signal_matches": support_matches,
        "weaken_signal_matches": weaken_matches,
        "alias_matches": alias_matches,
        "hint_support": hint_support,
        "hint_reasons": hint_reasons,
        "roles": roles,
        "terminal_roles": profile.get("terminal_roles") or DEFAULT_TERMINAL_ROLE_POLICY,
        "role_limits": profile.get("role_limits") or DEFAULT_ROLE_LIMITS,
        "priority": profile.get("priority", 50),
        "reasons": [
            reason
            for reason in [
                "profile_support_signal_match" if support_matches else "",
                "profile_weaken_signal_match" if weaken_matches else "",
                "profile_alias_match" if alias_matches else "",
                "stage1_candidate_hint" if hint_support else "",
                "stage1_requested_terminal_roles" if requested_roles else "",
                "route_when_uncertain" if uncertain_bonus else "",
            ]
            if reason
        ],
    }


def candidate_map_from_visual_signals(
    *,
    catalog: Dict[str, Any],
    query: str,
    visual_signal_vector: Dict[str, Any],
    route: Dict[str, Any] | None,
    memory: Dict[str, Any] | None,
    image_refs: Sequence[str],
) -> Dict[str, Dict[str, Any]]:
    candidates: Dict[str, Dict[str, Any]] = {}
    profiles = entity_profiles_for_catalog(catalog)
    memory_text = json.dumps(memory or {}, ensure_ascii=False, default=str)
    positive_signals, negative_signals = visual_signal_sets(visual_signal_vector)
    hints = candidate_hints_by_entity(visual_signal_vector, profiles)
    requests = requested_roles_by_entity(visual_signal_vector, profiles)
    text_blob = visual_query_blob(query, memory_text)

    for profile in profiles:
        entity_id = str(profile.get("entity_id") or "")
        scored = score_entity_profile(
            profile,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
            text_blob=text_blob,
            hint=hints.get(entity_id),
            requested_roles=requests.get(entity_id, []),
        )
        if scored.get("status") == "irrelevant":
            continue
        candidates[entity_id] = scored

    return candidates


def roles_for_candidate(candidate: Dict[str, Any]) -> List[str]:
    explicit_roles = _normalized_role_list(candidate.get("roles"))
    terminal_roles = candidate.get("terminal_roles") if isinstance(candidate.get("terminal_roles"), dict) else {}
    status = str(candidate.get("status") or "differential")
    default_roles = terminal_roles.get(status) or DEFAULT_TERMINAL_ROLE_POLICY.get(status) or DEFAULT_TERMINAL_ROLE_POLICY["differential"]
    roles: List[str] = []
    for role in _normalized_role_list(default_roles) + list(explicit_roles):
        if role not in roles:
            roles.append(role)
    return roles


def ordered_candidates(candidate_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        candidate_map.values(),
        key=lambda item: (
            -STATUS_RANK.get(str(item.get("status") or ""), 0),
            -float(item.get("score") or 0.0),
            -int(item.get("priority") or 0),
            str(item.get("disease_id")),
        ),
    )


def terminal_role_limit(candidate: Dict[str, Any], candidate_count: int) -> int:
    status = str(candidate.get("status") or "differential")
    limits = candidate.get("role_limits") if isinstance(candidate.get("role_limits"), dict) else DEFAULT_ROLE_LIMITS
    try:
        limit = int(limits.get(status, DEFAULT_ROLE_LIMITS.get(status, 3)))
    except (TypeError, ValueError):
        limit = DEFAULT_ROLE_LIMITS.get(status, 3)
    if candidate_count >= 4 and status in {"differential", "weakened", "unresolved"}:
        limit = min(limit, 3)
    if candidate_count >= 5:
        limit = min(limit, 2)
    return max(1, limit)


def limited_terminal_roles(candidate: Dict[str, Any], candidate_count: int) -> List[str]:
    return roles_for_candidate(candidate)[: terminal_role_limit(candidate, candidate_count)]


def remove_search_cue_block(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        block = match.group(0)
        if "search_cues:" in block or "retrieval_unit:" in block or "source_wiki_path:" in block:
            return ""
        return block

    return re.sub(r"```text\s*\n[\s\S]*?\n```", replace, text, flags=re.IGNORECASE)


def clean_page_text(path: Path) -> str:
    _, body = strip_frontmatter(read_text(path))
    body = remove_search_cue_block(body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


def render_context_items(
    selected_pages: Sequence[Dict[str, Any]],
    *,
    wiki2_dir: Path,
    max_context_chars: int,
) -> tuple[str, List[Dict[str, Any]]]:
    blocks: List[str] = []
    packed: List[Dict[str, Any]] = []
    page_count = max(1, len(selected_pages))
    base_body_budget = max(360, min(1100, max_context_chars // page_count - 260))
    remaining = max_context_chars
    for page in selected_pages:
        if remaining <= 200:
            break
        body = clean_page_text(wiki2_dir / page["path"])
        header = (
            f"[WIKI2_CONTEXT_ITEM]\n"
            f"path: {page['path']}\n"
            f"page_type: {page.get('page_type')}\n"
            f"parent: {page.get('parent_path')}\n"
            f"disease_id: {page.get('disease_id')}\n"
            f"section: {page.get('source_section') or page.get('section_role')}\n"
            f"selection_reason: {page.get('selection_reason')}\n"
            f"content:\n"
        )
        footer = "\n[/WIKI2_CONTEXT_ITEM]"
        remaining_pages = max(1, len(selected_pages) - len(packed))
        fair_budget = max(260, remaining // remaining_pages - len(header) - len(footer) - 2)
        budget = min(base_body_budget, fair_budget, remaining - len(header) - len(footer) - 2)
        if budget <= 200:
            break
        included = body[:budget].rstrip()
        if len(body) > budget:
            included += "\n\n[TRUNCATED]"
        block = header + included + footer
        blocks.append(block)
        remaining -= len(block) + 2
        packed_page = {key: value for key, value in page.items() if key != "routing_text"}
        packed_page["included_chars"] = len(included)
        packed.append(packed_page)
    return "\n\n".join(blocks) if blocks else "(no wiki2 detailed pages selected)", packed


def select_wiki2_intake_context(
    *,
    max_context_chars: int = 3000,
    wiki2_dir: Path = DEFAULT_WIKI2_DIR,
    catalog_dir: Path = DEFAULT_WIKI2_CATALOG_DIR,
) -> Dict[str, Any]:
    catalog = load_or_build_catalog(wiki2_dir=wiki2_dir, catalog_dir=catalog_dir)
    by_path = page_by_path(catalog)
    selected: List[Dict[str, Any]] = []
    per_parent_counts: Dict[str, int] = {}
    for path in STAGE1_INTAKE_PATHS:
        add_selected(
            selected,
            by_path.get(path),
            reason="stage1_minimal_visual_intake_sop",
            max_pages=len(STAGE1_INTAKE_PATHS),
            per_parent_counts=per_parent_counts,
            max_children_per_parent=len(STAGE1_INTAKE_PATHS),
            required=True,
        )
    context_text, packed_pages = render_context_items(
        selected,
        wiki2_dir=wiki2_dir,
        max_context_chars=max_context_chars,
    )
    selected_parent_paths = parent_paths_for(selected)
    return {
        "catalog_stats": {
            "num_pages": catalog.get("num_pages"),
            "num_detailed_pages": catalog.get("num_detailed_pages"),
            "num_parent_pages": catalog.get("num_parent_pages"),
        },
        "retrieval_trace": {
            "retrieval_system": "wiki2",
            "retrieval_stage": "stage1_visual_intake",
            "parent_policy": "parents are routing metadata only; detailed_section_page content is used for answers",
            "selected_parent_pages": selected_parent_paths,
            "selected_detailed_count": len(packed_pages),
            "max_context_chars": max_context_chars,
        },
        "selected_parent_pages": selected_parent_paths,
        "selected_pages": packed_pages,
        "context_text": context_text,
        "context_chars": len(context_text),
    }


def select_wiki2_context_from_signals(
    *,
    query: str,
    visual_signal_vector: Dict[str, Any],
    route: Dict[str, Any] | None = None,
    memory: Dict[str, Any] | None = None,
    image_refs: Sequence[str] = (),
    max_detailed_pages: int = 10,
    max_context_chars: int = 9000,
    max_children_per_parent: int = 4,
    include_parent_pages: str = "never",
    wiki2_dir: Path = DEFAULT_WIKI2_DIR,
    catalog_dir: Path = DEFAULT_WIKI2_CATALOG_DIR,
) -> Dict[str, Any]:
    catalog = load_or_build_catalog(wiki2_dir=wiki2_dir, catalog_dir=catalog_dir)
    by_path = page_by_path(catalog)
    candidate_map = candidate_map_from_visual_signals(
        catalog=catalog,
        query=query,
        visual_signal_vector=visual_signal_vector,
        route=route,
        memory=memory,
        image_refs=image_refs,
    )

    selected: List[Dict[str, Any]] = []
    per_parent_counts: Dict[str, int] = {}
    for path in STAGE2_TERMINAL_PROCEDURE_PATHS:
        add_selected(
            selected,
            by_path.get(path),
            reason="stage2_terminal_diagnosis_procedure",
            max_pages=max_detailed_pages,
            per_parent_counts=per_parent_counts,
            max_children_per_parent=max_children_per_parent,
            required=True,
        )

    terminal_path_plan: List[Dict[str, Any]] = []
    ordered = ordered_candidates(candidate_map)
    for candidate in ordered:
        disease_id = str(candidate.get("entity_id") or candidate.get("disease_id") or "")
        support = str(candidate.get("support") or "possible")
        status = str(candidate.get("status") or "differential")
        roles = limited_terminal_roles(candidate, len(ordered))
        paths = disease_paths_for_roles(catalog, disease_id, roles)
        terminal_path_plan.append(
            {
                "entity_id": disease_id,
                "disease_id": disease_id,
                "status": status,
                "support": support,
                "score": candidate.get("score"),
                "roles": roles,
                "paths": paths,
                "reasons": candidate.get("reasons") or [],
                "support_signal_matches": candidate.get("support_signal_matches") or [],
                "weaken_signal_matches": candidate.get("weaken_signal_matches") or [],
            }
        )
        for path in paths:
            add_selected(
                selected,
                by_path.get(path),
                reason=f"stage2_terminal_{disease_id}_{support}",
                max_pages=max_detailed_pages,
                per_parent_counts=per_parent_counts,
                max_children_per_parent=max_children_per_parent,
                required=True,
            )

    expanded_query = expand_query(
        "\n".join(
            part
            for part in [
                query,
                json.dumps(visual_signal_vector or {}, ensure_ascii=False, default=str),
                json.dumps(memory or {}, ensure_ascii=False, default=str)[:1000],
            ]
            if part
        )
    )
    detailed_pages = [
        page
        for page in catalog.get("pages", [])
        if page.get("page_type") == DETAIL_PAGE_TYPE
        and page.get("path") not in {item["path"] for item in selected}
    ]
    scored = [(score_page(page, expanded_query, route), page) for page in detailed_pages]
    scored.sort(key=lambda item: (-item[0], item[1]["path"]))
    allowed_diseases = set(candidate_map) or {"powdery_mildew", "downy_mildew", "others", "healthy"}
    for score, page in scored:
        if len(selected) >= max_detailed_pages:
            break
        if score <= 0:
            continue
        page_disease = page.get("disease_id")
        if page_disease and page_disease not in allowed_diseases:
            continue
        add_selected(
            selected,
            page,
            reason=f"stage2_scored_terminal_detail:{score}",
            max_pages=max_detailed_pages,
            per_parent_counts=per_parent_counts,
            max_children_per_parent=max_children_per_parent,
        )

    context_text, packed_pages = render_context_items(
        selected,
        wiki2_dir=wiki2_dir,
        max_context_chars=max_context_chars,
    )
    selected_parent_paths = parent_paths_for(selected)
    trace = {
        "retrieval_system": "wiki2",
        "retrieval_stage": "stage2_signal_terminal_expansion",
        "include_parent_pages": include_parent_pages,
        "parent_policy": "parents are routing metadata only; detailed_section_page content is used for answers",
        "signal_driven": True,
        "candidate_map": candidate_map,
        "terminal_path_plan": terminal_path_plan,
        "selected_parent_pages": selected_parent_paths,
        "selected_detailed_count": len(packed_pages),
        "max_detailed_pages": max_detailed_pages,
        "max_context_chars": max_context_chars,
        "max_children_per_parent": max_children_per_parent,
    }
    return {
        "catalog_stats": {
            "num_pages": catalog.get("num_pages"),
            "num_detailed_pages": catalog.get("num_detailed_pages"),
            "num_parent_pages": catalog.get("num_parent_pages"),
        },
        "retrieval_trace": trace,
        "selected_parent_pages": selected_parent_paths,
        "selected_pages": packed_pages,
        "context_text": context_text,
        "context_chars": len(context_text),
    }


def select_wiki2_context(
    query: str,
    *,
    route: Dict[str, Any] | None = None,
    memory: Dict[str, Any] | None = None,
    image_refs: Sequence[str] = (),
    max_detailed_pages: int = 8,
    max_context_chars: int = 6500,
    max_children_per_parent: int = 3,
    include_parent_pages: str = "never",
    wiki2_dir: Path = DEFAULT_WIKI2_DIR,
    catalog_dir: Path = DEFAULT_WIKI2_CATALOG_DIR,
) -> Dict[str, Any]:
    catalog = load_or_build_catalog(wiki2_dir=wiki2_dir, catalog_dir=catalog_dir)
    by_path = page_by_path(catalog)
    memory_text = json.dumps(memory or {}, ensure_ascii=False, default=str)
    expanded_query = expand_query(f"{query}\n{memory_text[:1200]}")
    disease_candidates = infer_disease_candidates(expanded_query, memory_text)

    selected: List[Dict[str, Any]] = []
    per_parent_counts: Dict[str, int] = {}
    required_paths = required_paths_for_query(
        query=expanded_query,
        route=route,
        image_refs=image_refs,
        disease_candidates=disease_candidates,
    )
    for path in required_paths:
        add_selected(
            selected,
            by_path.get(path),
            reason="required_by_task_or_disease_hint",
            max_pages=max_detailed_pages,
            per_parent_counts=per_parent_counts,
            max_children_per_parent=max_children_per_parent,
            required=True,
        )

    detailed_pages = [page for page in catalog.get("pages", []) if page.get("page_type") == DETAIL_PAGE_TYPE]
    scored = [(score_page(page, expanded_query, route), page) for page in detailed_pages]
    scored.sort(key=lambda item: (-item[0], item[1]["path"]))
    for score, page in scored:
        if len(selected) >= max_detailed_pages:
            break
        if score <= 0 and selected:
            continue
        if (
            is_treatment_query(expanded_query, route)
            and disease_candidates
            and page.get("disease_id")
            and page.get("disease_id") not in disease_candidates
        ):
            continue
        add_selected(
            selected,
            page,
            reason=f"scored_detail_page:{score}",
            max_pages=max_detailed_pages,
            per_parent_counts=per_parent_counts,
            max_children_per_parent=max_children_per_parent,
        )

    context_text, packed_pages = render_context_items(
        selected,
        wiki2_dir=wiki2_dir,
        max_context_chars=max_context_chars,
    )
    selected_parent_paths = parent_paths_for(selected)
    parent_candidates = top_parent_candidates(catalog, expanded_query, route)
    trace = {
        "retrieval_system": "wiki2",
        "query_expanded": expanded_query != query,
        "include_parent_pages": include_parent_pages,
        "parent_policy": "parents are routing metadata only; detailed_section_page content is used for answers",
        "disease_candidates": disease_candidates,
        "candidate_parent_pages": parent_candidates,
        "selected_parent_pages": selected_parent_paths,
        "selected_detailed_count": len(packed_pages),
        "max_detailed_pages": max_detailed_pages,
        "max_context_chars": max_context_chars,
    }
    return {
        "catalog_stats": {
            "num_pages": catalog.get("num_pages"),
            "num_detailed_pages": catalog.get("num_detailed_pages"),
            "num_parent_pages": catalog.get("num_parent_pages"),
        },
        "retrieval_trace": trace,
        "selected_parent_pages": selected_parent_paths,
        "selected_pages": packed_pages,
        "context_text": context_text,
        "context_chars": len(context_text),
    }


def print_search(rows: Sequence[Dict[str, Any]]) -> None:
    for row in rows:
        safe_print(f"{row['score']:>4}  {row['path']}  {row.get('title')}")


def search_wiki2(
    query: str,
    *,
    wiki2_dir: Path = DEFAULT_WIKI2_DIR,
    catalog_dir: Path = DEFAULT_WIKI2_CATALOG_DIR,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    catalog = load_or_build_catalog(wiki2_dir=wiki2_dir, catalog_dir=catalog_dir)
    expanded_query = expand_query(query)
    pages = [page for page in catalog.get("pages", []) if page.get("page_type") == DETAIL_PAGE_TYPE]
    scored = [(score_page(page, expanded_query), page) for page in pages]
    scored.sort(key=lambda item: (-item[0], item[1]["path"]))
    return [
        {
            "score": score,
            "path": page["path"],
            "title": page.get("title"),
            "page_type": page.get("page_type"),
            "section_role": page.get("section_role"),
        }
        for score, page in scored[:limit]
        if score > 0
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and query the independent wiki2 retrieval catalog.")
    parser.add_argument("--wiki2-dir", default=str(DEFAULT_WIKI2_DIR))
    parser.add_argument("--catalog-dir", default=str(DEFAULT_WIKI2_CATALOG_DIR))
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--search", default=None)
    parser.add_argument("--select", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    wiki2_dir = Path(args.wiki2_dir)
    catalog_dir = Path(args.catalog_dir)
    if args.build:
        catalog = build_catalog(wiki2_dir=wiki2_dir, catalog_dir=catalog_dir)
        safe_print(
            f"Built wiki2 catalog with {catalog['num_pages']} pages "
            f"({catalog['num_detailed_pages']} detailed) at {catalog_dir}"
        )
    if args.search:
        rows = search_wiki2(args.search, wiki2_dir=wiki2_dir, catalog_dir=catalog_dir, limit=args.limit)
        if args.json:
            safe_print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            print_search(rows)
    if args.select:
        result = select_wiki2_context(args.select, wiki2_dir=wiki2_dir, catalog_dir=catalog_dir)
        safe_print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["context_text"])
    if not (args.build or args.search or args.select):
        parser.print_help()


if __name__ == "__main__":
    main()
