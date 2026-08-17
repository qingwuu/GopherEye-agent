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

SUPPORTED_DISEASE_ROLES = [
    "visual_evidence_thresholds",
    "feature_checklist",
    "differentials",
    "image_requests",
]

POSSIBLE_DISEASE_ROLES = [
    "visual_evidence_thresholds",
    "feature_checklist",
    "differentials",
]

WEAKENED_DISEASE_ROLES = [
    "visual_evidence_thresholds",
    "differentials",
]

OTHERS_DISEASE_ROLES = [
    "visual_patterns",
    "required_handling",
    "differentials",
    "promotion_rule",
]

HEALTHY_DISEASE_ROLES = [
    "minimum_evidence",
    "differentials",
    "image_requests",
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

SIGNAL_KEYWORDS = {
    "powdery_mildew_support": [
        "white_gray_powdery_colonies_present",
        "powdery_colonies_present",
        "dusty_surface_growth",
        "webby_mycelium",
        "white_gray_surface_colonies",
    ],
    "powdery_mildew_weaken": [
        "white_gray_powdery_colonies_absent",
        "powdery_colonies_absent",
        "no_powdery_colonies",
    ],
    "downy_mildew_support": [
        "oil_spot_like_yellowing",
        "oil_spots",
        "oily_yellow_spots",
        "vein_bounded_or_angular_lesions",
        "angular_vein_limited_lesions",
        "cottony_downy_sporulation_present",
        "downy_sporulation_present",
    ],
    "downy_mildew_weaken": [
        "cottony_downy_sporulation_absent",
        "downy_sporulation_absent",
        "no_cottony_sporulation",
    ],
    "others_support": [
        "necrotic_leaf_spots",
        "necrotic_spots",
        "yellow_brown_lesions",
        "brown_spots",
        "marginal_scorch",
        "dark_specks",
        "insect_like_damage",
        "mite_like_damage",
        "mixed_signs",
        "noncanonical_leaf_spot_pattern",
        "unresolved_leaf_spot_pattern",
        "residue_or_glare_possible",
    ],
    "healthy_support": [
        "healthy_variation_possible",
        "no_visible_symptoms",
        "normal_leaf_variation",
    ],
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


def build_catalog(
    *,
    wiki2_dir: Path = DEFAULT_WIKI2_DIR,
    catalog_dir: Path = DEFAULT_WIKI2_CATALOG_DIR,
) -> Dict[str, Any]:
    pages = [build_page_record(path, wiki2_dir) for path in iter_markdown_files(wiki2_dir)]
    pages.sort(key=lambda page: page["path"])

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
            return json.loads(read_text(catalog_path))
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


ABSENT_SIGNAL_ALIASES = {
    "white_gray_powdery_colonies_present": "white_gray_powdery_colonies_absent",
    "powdery_colonies_present": "powdery_colonies_absent",
    "powdery_surface_growth_present": "powdery_colonies_absent",
    "cottony_downy_sporulation_present": "cottony_downy_sporulation_absent",
    "downy_sporulation_present": "downy_sporulation_absent",
}


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


def candidate_map_from_visual_signals(
    *,
    query: str,
    visual_signal_vector: Dict[str, Any],
    route: Dict[str, Any] | None,
    memory: Dict[str, Any] | None,
    image_refs: Sequence[str],
) -> Dict[str, Dict[str, Any]]:
    candidates: Dict[str, Dict[str, Any]] = {}
    memory_text = json.dumps(memory or {}, ensure_ascii=False, default=str)
    visual_text = json.dumps(visual_signal_vector or {}, ensure_ascii=False, default=str)

    for disease_id in infer_disease_candidates(query, memory_text):
        _merge_candidate(
            candidates,
            disease_id,
            support="possible",
            roles=POSSIBLE_DISEASE_ROLES,
            reason="explicit_user_or_memory_disease_hint",
        )

    if isinstance(visual_signal_vector.get("candidate_hints"), list):
        for hint in visual_signal_vector.get("candidate_hints", []):
            if not isinstance(hint, dict):
                continue
            disease_id = canonical_disease_id(hint.get("disease_id") or hint.get("disease"))
            if not disease_id:
                continue
            roles = hint.get("needed_detail_roles") if isinstance(hint.get("needed_detail_roles"), list) else []
            support = normalize_support(hint.get("support"))
            default_roles = (
                SUPPORTED_DISEASE_ROLES
                if support == "supporting"
                else WEAKENED_DISEASE_ROLES
                if support in {"weakened", "negative"}
                else POSSIBLE_DISEASE_ROLES
            )
            _merge_candidate(
                candidates,
                disease_id,
                support=support,
                roles=list(roles) or default_roles,
                reason="stage1_candidate_hint",
            )

    if isinstance(visual_signal_vector.get("needed_detail_pages"), list):
        for request in visual_signal_vector.get("needed_detail_pages", []):
            if not isinstance(request, dict):
                continue
            disease_id = canonical_disease_id(request.get("disease_id") or request.get("disease"))
            if not disease_id:
                continue
            roles = request.get("roles") if isinstance(request.get("roles"), list) else []
            existing_support = str(candidates.get(disease_id, {}).get("support") or "possible")
            _merge_candidate(
                candidates,
                disease_id,
                support=existing_support,
                roles=list(roles) or POSSIBLE_DISEASE_ROLES,
                reason="stage1_requested_terminal_roles",
            )

    positive_signals, negative_signals = visual_signal_sets(visual_signal_vector)
    if _has_any_signal(positive_signals, SIGNAL_KEYWORDS["powdery_mildew_support"]):
        _merge_candidate(
            candidates,
            "powdery_mildew",
            support="supporting",
            roles=SUPPORTED_DISEASE_ROLES,
            reason="powdery_surface_growth_signal",
        )
    if _has_any_signal(negative_signals, SIGNAL_KEYWORDS["powdery_mildew_weaken"]):
        _merge_candidate(
            candidates,
            "powdery_mildew",
            support="weakened",
            roles=WEAKENED_DISEASE_ROLES,
            reason="powdery_colonies_absent_signal",
        )
    if _has_any_signal(positive_signals, SIGNAL_KEYWORDS["downy_mildew_support"]):
        _merge_candidate(
            candidates,
            "downy_mildew",
            support="supporting",
            roles=SUPPORTED_DISEASE_ROLES,
            reason="downy_oil_spot_or_sporulation_signal",
        )
    if _has_any_signal(negative_signals, SIGNAL_KEYWORDS["downy_mildew_weaken"]):
        support = str(candidates.get("downy_mildew", {}).get("support") or "weakened")
        _merge_candidate(
            candidates,
            "downy_mildew",
            support=support,
            roles=["visual_evidence_thresholds", "differentials", "image_requests"],
            reason="downy_sporulation_missing_or_absent_signal",
        )
    if _has_any_signal(positive_signals, SIGNAL_KEYWORDS["others_support"]):
        _merge_candidate(
            candidates,
            "others",
            support="possible",
            roles=OTHERS_DISEASE_ROLES,
            reason="noncanonical_or_unresolved_leaf_spot_signal",
        )
    if _has_any_signal(positive_signals, SIGNAL_KEYWORDS["healthy_support"]):
        _merge_candidate(
            candidates,
            "healthy",
            support="possible",
            roles=HEALTHY_DISEASE_ROLES,
            reason="healthy_or_low_symptom_signal",
        )

    canonical_comparison = any(
        token in f"{query}\n{visual_text}".lower()
        for token in ["compare", "differential", "versus", " vs ", "powdery", "downy", "\u9274\u522b", "\u6bd4\u8f83"]
    )
    if canonical_comparison or (is_visual_query(query, route, image_refs) and not candidates):
        for disease_id in ["powdery_mildew", "downy_mildew"]:
            _merge_candidate(
                candidates,
                disease_id,
                support="possible" if disease_id not in candidates else str(candidates[disease_id]["support"]),
                roles=WEAKENED_DISEASE_ROLES if disease_id in candidates else POSSIBLE_DISEASE_ROLES,
                reason="canonical_visual_differential_safety_net",
            )

    if is_visual_query(query, route, image_refs) and "others" not in candidates:
        uncertain_tokens = [
            "uncertain",
            "unresolved",
            "insufficient",
            "necrotic",
            "lesion",
            "spot",
            "brown",
            "yellow",
            "missing",
            "absent",
        ]
        if any(token in f"{query}\n{visual_text}".lower() for token in uncertain_tokens):
            _merge_candidate(
                candidates,
                "others",
                support="possible",
                roles=OTHERS_DISEASE_ROLES[:3],
                reason="uncertainty_or_noncanonical_text_signal",
            )

    return candidates


def roles_for_candidate(disease_id: str, support: str, explicit_roles: Sequence[str]) -> List[str]:
    roles = [role for role in (normalize_detail_role(item) for item in explicit_roles) if role]
    if roles:
        return list(dict.fromkeys(roles))
    support = normalize_support(support)
    if disease_id == "others":
        return OTHERS_DISEASE_ROLES
    if disease_id == "healthy":
        return HEALTHY_DISEASE_ROLES
    if support == "supporting":
        return SUPPORTED_DISEASE_ROLES
    if support in {"weakened", "negative"}:
        return WEAKENED_DISEASE_ROLES
    return POSSIBLE_DISEASE_ROLES


def ordered_candidates(candidate_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    def disease_priority(item: Dict[str, Any]) -> int:
        disease_id = str(item.get("disease_id") or "")
        if disease_id in {"downy_mildew", "powdery_mildew"}:
            return 1
        if disease_id == "others":
            return 0
        if disease_id == "healthy":
            return 2
        return 3

    return sorted(
        candidate_map.values(),
        key=lambda item: (
            -SUPPORT_RANK.get(str(item.get("support")), 0),
            disease_priority(item),
            str(item.get("disease_id")),
        ),
    )


def terminal_role_limit(disease_id: str, support: str, candidate_count: int) -> int:
    support = normalize_support(support)
    if disease_id == "others":
        return 3 if candidate_count > 1 else 4
    if disease_id == "healthy":
        return 1 if candidate_count > 1 else 3
    if support == "supporting":
        return 4 if candidate_count <= 2 else 3
    if support in {"weakened", "negative"}:
        return 3 if disease_id == "downy_mildew" else 2
    return 3


def limited_terminal_roles(disease_id: str, support: str, roles: Sequence[str], candidate_count: int) -> List[str]:
    support = normalize_support(support)
    limit = terminal_role_limit(disease_id, support, candidate_count)
    if disease_id == "downy_mildew" and support in {"weakened", "negative"}:
        preferred = ["visual_evidence_thresholds", "differentials", "image_requests", "feature_checklist"]
    elif disease_id == "powdery_mildew" and support in {"weakened", "negative"}:
        preferred = ["visual_evidence_thresholds", "differentials", "image_requests", "feature_checklist"]
    else:
        preferred = {
            "others": ["visual_patterns", "required_handling", "differentials", "promotion_rule"],
            "healthy": ["minimum_evidence", "differentials", "image_requests"],
            "downy_mildew": ["visual_evidence_thresholds", "feature_checklist", "differentials", "image_requests"],
            "powdery_mildew": ["visual_evidence_thresholds", "feature_checklist", "differentials", "image_requests"],
        }.get(disease_id, list(roles))
    normalized_roles = [role for role in (normalize_detail_role(item) for item in roles) if role]
    ordered = [role for role in preferred if role in normalized_roles or not normalized_roles]
    for role in normalized_roles:
        if role not in ordered:
            ordered.append(role)
    return ordered[:limit]


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
        disease_id = str(candidate["disease_id"])
        support = str(candidate.get("support") or "possible")
        roles = limited_terminal_roles(
            disease_id,
            support,
            roles_for_candidate(disease_id, support, candidate.get("roles") or []),
            len(ordered),
        )
        paths = disease_paths_for_roles(catalog, disease_id, roles)
        terminal_path_plan.append(
            {
                "disease_id": disease_id,
                "support": support,
                "roles": roles,
                "paths": paths,
                "reasons": candidate.get("reasons") or [],
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
