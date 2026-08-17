from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Sequence, Tuple

from src.gophereye_runtime.utils import parse_json_object, stable_id


SUPPORT_STATUSES = {"fully_supported", "partially_supported", "no_support", "not_checked"}
RECOMMENDED_ACTIONS = {"keep", "hedge", "remove", "ask_followup", "human_review"}
RISK_LEVELS = {"low", "medium", "high"}
CLAIM_TYPES = {
    "visual_observation",
    "diagnosis",
    "treatment",
    "source_fact",
    "system_behavior",
    "data",
    "other",
}


def trim_text(text: Any, max_chars: int) -> str:
    value = str(text or "")
    if max_chars <= 0 or len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "\n\n[TRUNCATED]\n"


def compact_json(value: Any, max_chars: int = 8000) -> str:
    return trim_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), max_chars)


def parse_json_array(text: Any) -> List[Any]:
    if not isinstance(text, str) or not text.strip():
        return []
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


def backend_provider(backend: Any) -> str:
    profile = getattr(backend, "profile", None)
    return str(getattr(profile, "provider", "") or "")


def is_echo_backend(backend: Any) -> bool:
    return backend_provider(backend) == "echo"


def _string_list(value: Any, *, max_items: int = 8) -> List[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    out: List[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def _normalize_claim_type(value: Any) -> str:
    text = str(value or "other").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in CLAIM_TYPES else "other"


def _normalize_support_status(value: Any) -> str:
    text = str(value or "not_checked").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in SUPPORT_STATUSES else "not_checked"


def _normalize_risk_level(value: Any, *, claim: str = "", claim_type: str = "other") -> str:
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if text in RISK_LEVELS:
        return text
    lowered = claim.lower()
    if claim_type in {"diagnosis", "treatment"} or any(
        token in lowered
        for token in [
            "confirmed",
            "diagnosis",
            "treatment",
            "chemical",
            "rate",
            "legal",
            "ground truth",
            "opposite side",
            "single surface",
        ]
    ):
        return "high"
    return "medium" if claim_type in {"source_fact", "system_behavior", "data"} else "low"


def _normalize_recommended_action(value: Any, *, support_status: str, risk_level: str) -> str:
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if text in RECOMMENDED_ACTIONS:
        return text
    if support_status == "fully_supported":
        return "keep"
    if support_status == "partially_supported":
        return "hedge" if risk_level != "high" else "human_review"
    if support_status == "no_support":
        return "remove" if risk_level == "high" else "hedge"
    return "human_review" if risk_level == "high" else "keep"


def normalize_claim(item: Any, *, index: int = 1, prefix: str = "claim") -> Dict[str, Any] | None:
    if isinstance(item, str):
        claim = item.strip()
        raw: Dict[str, Any] = {"claim": claim}
    elif isinstance(item, dict):
        raw = dict(item)
        claim = str(raw.get("claim") or raw.get("text") or raw.get("statement") or "").strip()
    else:
        return None
    if not claim:
        return None

    claim_type = _normalize_claim_type(raw.get("claim_type") or raw.get("type"))
    risk_level = _normalize_risk_level(raw.get("risk_level"), claim=claim, claim_type=claim_type)
    claim_id = str(raw.get("claim_id") or raw.get("source_claim_id") or raw.get("id") or stable_id(prefix, index, claim))
    return {
        "claim_id": claim_id,
        "claim": claim,
        "claim_type": claim_type,
        "risk_level": risk_level,
        "source_url": str(raw.get("source_url") or "").strip(),
        "source_title": str(raw.get("source_title") or "").strip(),
        "target_entities": _string_list(raw.get("target_entities"), max_items=12),
    }


def normalize_claim_support(
    item: Any,
    *,
    index: int = 1,
    known_claims: Sequence[Dict[str, Any]] = (),
) -> Dict[str, Any] | None:
    claim_by_id = {str(claim.get("claim_id")): claim for claim in known_claims if claim.get("claim_id")}
    claim_by_text = {str(claim.get("claim")): claim for claim in known_claims if claim.get("claim")}

    if isinstance(item, str):
        raw: Dict[str, Any] = {"claim": item}
    elif isinstance(item, dict):
        raw = dict(item)
    else:
        return None

    base = claim_by_id.get(str(raw.get("claim_id") or "")) or claim_by_text.get(str(raw.get("claim") or ""))
    claim = str(raw.get("claim") or (base or {}).get("claim") or "").strip()
    if not claim:
        return None

    claim_type = _normalize_claim_type(raw.get("claim_type") or (base or {}).get("claim_type"))
    risk_level = _normalize_risk_level(
        raw.get("risk_level") or (base or {}).get("risk_level"),
        claim=claim,
        claim_type=claim_type,
    )
    support_status = _normalize_support_status(raw.get("support_status") or raw.get("status"))
    recommended_action = _normalize_recommended_action(
        raw.get("recommended_action") or raw.get("action"),
        support_status=support_status,
        risk_level=risk_level,
    )
    claim_id = str(raw.get("claim_id") or (base or {}).get("claim_id") or stable_id("claim", index, claim))
    source_url = str(raw.get("source_url") or (base or {}).get("source_url") or "").strip()
    source_title = str(raw.get("source_title") or (base or {}).get("source_title") or "").strip()

    return {
        "claim_id": claim_id,
        "claim": claim,
        "claim_type": claim_type,
        "support_status": support_status,
        "evidence_refs": _string_list(raw.get("evidence_refs") or raw.get("source_refs"), max_items=12),
        "missing_evidence": _string_list(raw.get("missing_evidence"), max_items=12),
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "source_url": source_url,
        "source_title": source_title,
        "source_quality": str(raw.get("source_quality") or "").strip(),
        "already_in_wiki": bool(raw.get("already_in_wiki", False)),
        "conflicts_with_wiki": bool(raw.get("conflicts_with_wiki", False)),
    }


def _extract_claims_payload(value: Any) -> List[Any]:
    if isinstance(value, dict):
        for key in ["claims", "source_claims", "atomic_claims"]:
            if isinstance(value.get(key), list):
                return value[key]
    if isinstance(value, list):
        return value
    return []


def _extract_support_payload(value: Any) -> List[Any]:
    if isinstance(value, dict):
        for key in ["claim_support", "verified_claims", "claims"]:
            if isinstance(value.get(key), list):
                return value[key]
    if isinstance(value, list):
        return value
    return []


def call_json_object(
    backend: Any,
    prompt: str,
    *,
    fallback: Dict[str, Any],
    max_output_tokens: int,
) -> Tuple[Dict[str, Any], Any | None]:
    try:
        response = backend.generate(prompt, max_output_tokens=max_output_tokens)
    except Exception as exc:
        failed = dict(fallback)
        failed["reflection_error"] = f"{type(exc).__name__}: {exc}"
        return failed, None
    parsed = parse_json_object(response.text)
    if parsed is not None:
        return parsed, response
    array = parse_json_array(response.text)
    if array:
        return {"items": array}, response
    failed = dict(fallback)
    failed["raw_model_output"] = response.text
    return failed, response


def support_evidence_blob(
    memory: Dict[str, Any] | None,
    assistant_message: str,
    draft_memory_update: Dict[str, Any] | None = None,
) -> str:
    parts = [assistant_message]
    if isinstance(draft_memory_update, dict):
        parts.append("DRAFT_MEMORY_UPDATE\n" + compact_json(draft_memory_update, 8000))
    if isinstance(memory, dict):
        parts.append("SESSION_MEMORY\n" + compact_json(memory, 6000))
    return "\n".join(parts).lower()


def visual_evidence_blob(
    memory: Dict[str, Any] | None,
    draft_memory_update: Dict[str, Any] | None,
) -> str:
    parts: List[str] = []
    if isinstance(draft_memory_update, dict):
        parts.append(compact_json(draft_memory_update, 10000))
    if isinstance(memory, dict):
        parts.append(compact_json(memory, 6000))
    return "\n".join(parts).lower()


def visual_evidence_refs(
    memory: Dict[str, Any] | None,
    draft_memory_update: Dict[str, Any] | None,
) -> List[str]:
    refs: List[str] = []
    if isinstance(draft_memory_update, dict):
        if isinstance(draft_memory_update.get("visual_intakes"), list) and draft_memory_update.get("visual_intakes"):
            refs.append("draft_memory.visual_intakes")
        if isinstance(draft_memory_update.get("evidence_present"), list) and draft_memory_update.get("evidence_present"):
            refs.append("draft_memory.evidence_present")
    if isinstance(memory, dict):
        if isinstance(memory.get("visual_intakes"), list) and memory.get("visual_intakes"):
            refs.append("session_memory.visual_intakes")
        if isinstance(memory.get("evidence_present"), list) and memory.get("evidence_present"):
            refs.append("session_memory.evidence_present")
    return refs or ["draft_memory"]


def selected_page_paths(selected_pages: Sequence[Dict[str, Any]]) -> List[str]:
    return [str(page.get("path") or "").lower() for page in selected_pages]


def matching_page_refs(selected_pages: Sequence[Dict[str, Any]], *needles: str) -> List[str]:
    refs: List[str] = []
    for page in selected_pages:
        path = str(page.get("path") or "")
        haystack = " ".join(
            [
                path,
                str(page.get("title") or ""),
                str(page.get("id") or ""),
            ]
        ).lower()
        if any(needle.lower() in haystack for needle in needles):
            refs.append(path)
    return refs


def has_any(text: str, tokens: Sequence[str]) -> bool:
    return any(token in text for token in tokens)


def is_visual_absence_claim(text: str) -> bool:
    lower = text.lower()
    return has_any(
        lower,
        [
            "no ",
            "not visible",
            "not evident",
            "without ",
            "absent",
            "absence",
            "cannot see",
        ],
    )


def is_confirmed_diagnosis_assertion(text: str) -> bool:
    lower = text.lower()
    if is_unconfirmed_diagnosis_statement(lower):
        return False
    return any(
        token in lower
        for token in [
            "confirmed diagnosis",
            "is confirmed",
            "are confirmed",
            "confirmed as",
            "diagnosis is confirmed",
        ]
    )


def is_unconfirmed_diagnosis_statement(text: str) -> bool:
    lower = text.lower()
    return any(
        token in lower
        for token in [
            "not confirmed",
            "unconfirmed",
            "cannot confirm",
            "can't confirm",
            "not enough evidence to confirm",
            "is not confirmed",
            "are not confirmed",
            "no confirmed",
            "not confirmed by",
        ]
    )


def has_group(text: str, tokens: Sequence[str]) -> bool:
    return any(token in text for token in tokens)


def count_matching_groups(text: str, groups: Sequence[Sequence[str]]) -> int:
    return sum(1 for group in groups if has_group(text, group))


def visual_claim_support_status(claim_text: str, evidence_blob: str) -> Tuple[str, List[str]]:
    lower = claim_text.lower()
    if not evidence_blob.strip():
        return "not_checked", ["No draft visual intake was available for this visual claim."]

    negated_claim = is_visual_absence_claim(lower)
    negative_evidence = has_any(
        evidence_blob,
        [
            "no localized",
            "no superficial",
            "no clear",
            "no clearly",
            "not visible",
            "not evident",
            "not show",
            "without visible",
            "without visible mildew",
            "absent",
            "absence",
        ],
    )

    groups: List[List[str]] = []
    if has_any(lower, ["same grape leaf", "same leaf", "opposite surfaces", "both surfaces"]):
        groups.append(["same-leaf", "same leaf", "upper and lower", "opposite surfaces", "paired views"])
    if has_any(lower, ["corresponding", "both leaf surfaces", "both surfaces"]):
        groups.append(["corresponding", "same-leaf", "upper and lower", "paired views", "both"])
    if has_any(lower, ["brown", "tan-to-brown"]):
        groups.append(["brown", "tan-to-brown"])
    if has_any(lower, ["necrotic", "necrosis"]):
        groups.append(["necrotic", "necrosis"])
    if has_any(lower, ["lesion", "lesions", "spot", "spots"]):
        groups.append(["lesion", "lesions", "spot", "spots", "discoloration", "damage"])
    if has_any(lower, ["yellow", "chlorotic", "chlorosis"]):
        groups.append(["yellow", "chlorotic", "chlorosis", "yellow-margined"])
    if has_any(lower, ["red", "reddish"]):
        groups.append(["red", "reddish", "reddish-brown"])
    if has_any(lower, ["black", "dark"]):
        groups.append(["black", "dark", "black-brown"])
    if has_any(lower, ["white", "gray", "grey", "white-gray", "white-grey"]):
        groups.append(["white", "gray", "grey", "white-gray", "white-grey"])
    if has_any(lower, ["margin", "margins", "edge", "edges"]):
        groups.append(["margin", "margins", "margined", "edge", "edges"])
    if has_any(lower, ["angular", "vein-bounded", "vein-limited"]):
        groups.append(["angular", "vein-bounded", "vein-limited"])
    if "round" in lower:
        groups.append(["round"])
    if "irregular" in lower:
        groups.append(["irregular"])
    if "square" in lower:
        groups.append(["square"])
    if has_any(lower, ["entire leaf", "whole leaf", "cover the leaf", "covering the leaf"]):
        groups.append(["entire leaf", "whole leaf", "widespread", "covering the leaf"])
    if "vein" in lower or "midrib" in lower:
        groups.append(["vein", "veins", "midrib"])
        if has_any(lower, ["associated", "near", "nearby", "along", "following", "bounded", "limited"]):
            groups.append(["associated", "near", "nearby", "along", "following", "bounded", "limited"])
    if has_any(lower, ["upper", "adaxial"]):
        groups.append(["upper", "adaxial"])
    if has_any(lower, ["underside", "lower", "abaxial"]):
        groups.append(["underside", "lower", "abaxial"])
    if has_any(lower, ["cottony", "downy", "sporulation"]):
        groups.append(["cottony", "downy", "sporulation"])
    if has_any(lower, ["powdery", "white-gray", "white gray", "webby"]):
        groups.append(["powdery", "white-gray", "white gray", "webby", "colonies"])
    if has_any(lower, ["oily", "oil spot", "oil-spot"]):
        groups.append(["oily", "oil spot", "oil-spot"])

    if negated_claim:
        target_groups = [group for group in groups if not any(token in group for token in ["no ", "not "])]
        target_matches = count_matching_groups(evidence_blob, target_groups)
        if negative_evidence and target_matches >= max(1, min(2, len(target_groups))):
            return "partially_supported", [
                "The draft visual intake supports a not-visible statement, but absence from field imagery remains image-limited."
            ]
        if negative_evidence or target_matches:
            return "partially_supported", [
                "The draft visual intake supports an absence/visibility statement, but absence from a field photo remains image-limited."
            ]
        return "not_checked", ["The absence claim needs clearer draft visual intake evidence."]

    if not groups:
        if claim_text.lower() in evidence_blob:
            return "fully_supported", []
        return "not_checked", ["No specific deterministic visual feature group matched this claim."]

    matches = count_matching_groups(evidence_blob, groups)
    if matches == len(groups):
        return "fully_supported", []
    if matches >= max(1, len(groups) - 1):
        return "partially_supported", ["Most, but not all, visual feature groups were found in the draft visual intake."]
    if matches:
        return "partially_supported", ["Only weak visual feature overlap was found in the draft visual intake."]
    return "not_checked", ["The visual claim was not clearly repeated in the draft visual intake."]


def visual_claim_has_memory_support(claim_text: str, evidence_blob: str) -> bool:
    token_candidates = [
        "necrotic",
        "brown",
        "yellow",
        "margin",
        "lesion",
        "spot",
        "powdery",
        "cottony",
        "sporulation",
        "oil",
        "angular",
        "vein",
        "upper",
        "lower",
        "adaxial",
        "abaxial",
    ]
    hits = [token for token in token_candidates if token in claim_text and token in evidence_blob]
    return len(hits) >= 1 or claim_text in evidence_blob


def deterministic_chat_claim_support(
    claim: Dict[str, Any],
    *,
    selected_pages: Sequence[Dict[str, Any]],
    memory: Dict[str, Any] | None,
    draft_memory_update: Dict[str, Any] | None,
    assistant_message: str,
    index: int,
) -> Dict[str, Any] | None:
    claim_text = str(claim.get("claim") or "").strip()
    if not claim_text:
        return None
    lower = claim_text.lower()
    claim_type = _normalize_claim_type(claim.get("claim_type"))
    risk_level = _normalize_risk_level(claim.get("risk_level"), claim=claim_text, claim_type=claim_type)
    evidence_blob = support_evidence_blob(memory, assistant_message, draft_memory_update)
    refs: List[str] = []
    missing: List[str] = []
    support_status = "not_checked"
    action = "human_review" if risk_level == "high" else "keep"

    if claim_type == "visual_observation":
        refs = visual_evidence_refs(memory, draft_memory_update)
        support_status, missing = visual_claim_support_status(
            lower,
            visual_evidence_blob(memory, draft_memory_update),
        )
        if support_status == "fully_supported":
            action = "keep"
        elif support_status == "partially_supported":
            action = "keep" if is_visual_absence_claim(lower) else "hedge"
        else:
            action = "ask_followup"

    elif claim_type == "diagnosis":
        refs = matching_page_refs(
            selected_pages,
            "diagnosis_sop",
            "image_and_evidence_sop",
            "powdery_mildew",
            "downy_mildew",
            "others",
        )
        conservative_tokens = [
            "provisional",
            "unresolved",
            "not enough",
            "insufficient",
            "weak",
            "weakly",
            "poorly supported",
            "less supported",
            "more evidence",
            "cannot confirm",
            "not confirm",
        ]
        if is_confirmed_diagnosis_assertion(lower):
            support_status = "no_support"
            action = "remove"
            missing.append("Confirmed diagnosis requires reviewed or human confirmation.")
        elif has_any(lower, ["leading", "likely", "most likely", "diagnosis is", "is the diagnosis"]):
            support_status = "partially_supported"
            action = "hedge"
            missing.append("Ranking a disease requires stronger disease-specific evidence.")
        elif "black rot" in lower and not matching_page_refs(selected_pages, "black_rot", "black rot"):
            support_status = "partially_supported"
            action = "hedge"
            missing.append("Black rot ranking requires a selected black rot disease page or stronger case-specific evidence.")
        elif has_any(lower, conservative_tokens):
            support_status = "fully_supported" if refs else "partially_supported"
            action = "keep" if refs else "hedge"
            if not refs:
                missing.append("No selected diagnosis procedure page was available to support conservative diagnosis language.")
        else:
            support_status = "partially_supported"
            action = "hedge"
            missing.append("Diagnosis claim should remain conservative unless disease-specific evidence is explicit.")

    elif claim_type == "treatment":
        refs = matching_page_refs(selected_pages, "treatment", "source_policy")
        if refs:
            support_status = "partially_supported"
            action = "hedge"
            missing.append("Treatment wording still needs exact reviewed source support.")
        else:
            support_status = "no_support"
            action = "remove"
            missing.append("No selected treatment or source-policy page supports this treatment claim.")

    elif has_any(lower, ["close-up", "close up", "next image", "more evidence", "needed", "useful"]):
        refs = matching_page_refs(selected_pages, "image_and_evidence_sop", "diagnosis_sop")
        support_status = "fully_supported" if refs else "partially_supported"
        action = "keep" if refs else "hedge"
        if not refs:
            missing.append("No selected image-evidence procedure page was available.")

    elif has_any(lower, ["same grape leaf", "same leaf", "both surfaces"]):
        refs = ["user/session image context"]
        support_status = "partially_supported"
        action = "hedge"
        missing.append("Same-leaf pairing is based on user/session context and visual similarity, not an independent plant ID.")

    else:
        support_status = "not_checked"
        action = "human_review" if risk_level == "high" else "keep"
        missing.append("No deterministic support rule matched this claim.")

    return normalize_claim_support(
        {
            **claim,
            "support_status": support_status,
            "evidence_refs": refs,
            "missing_evidence": missing,
            "risk_level": risk_level,
            "recommended_action": action,
        },
        index=index,
        known_claims=[claim],
    )


def deterministic_chat_support(
    claims: Sequence[Dict[str, Any]],
    *,
    selected_pages: Sequence[Dict[str, Any]],
    memory: Dict[str, Any] | None,
    draft_memory_update: Dict[str, Any] | None = None,
    assistant_message: str,
) -> List[Dict[str, Any]]:
    support: List[Dict[str, Any]] = []
    for idx, claim in enumerate(claims, start=1):
        item = deterministic_chat_claim_support(
            claim,
            selected_pages=selected_pages,
            memory=memory,
            draft_memory_update=draft_memory_update,
            assistant_message=assistant_message,
            index=idx,
        )
        if item:
            support.append(item)
    return support


def protect_visual_support_from_draft(
    support: Sequence[Dict[str, Any]],
    *,
    claims: Sequence[Dict[str, Any]],
    selected_pages: Sequence[Dict[str, Any]],
    memory: Dict[str, Any] | None,
    draft_memory_update: Dict[str, Any] | None,
    assistant_message: str,
) -> List[Dict[str, Any]]:
    protected: List[Dict[str, Any]] = []
    claim_by_id = {str(claim.get("claim_id")): claim for claim in claims if claim.get("claim_id")}
    claim_by_text = {str(claim.get("claim")): claim for claim in claims if claim.get("claim")}
    visual_blob = visual_evidence_blob(memory, draft_memory_update)

    for idx, item in enumerate(support, start=1):
        current = dict(item)
        if current.get("claim_type") != "visual_observation":
            protected.append(current)
            continue

        claim = claim_by_id.get(str(current.get("claim_id") or "")) or claim_by_text.get(str(current.get("claim") or ""))
        claim = claim or current
        status, missing = visual_claim_support_status(str(claim.get("claim") or ""), visual_blob)
        if (
            status == "fully_supported"
            or (status == "partially_supported" and is_visual_absence_claim(str(claim.get("claim") or "")))
        ) and current.get("support_status") in {
            "no_support",
            "not_checked",
        }:
            deterministic = deterministic_chat_claim_support(
                claim,
                selected_pages=selected_pages,
                memory=memory,
                draft_memory_update=draft_memory_update,
                assistant_message=assistant_message,
                index=idx,
            )
            if deterministic:
                deterministic["support_source"] = "draft_visual_memory"
                protected.append(deterministic)
                continue

        if status == "fully_supported" and current.get("support_status") == "partially_supported":
            current["support_status"] = "fully_supported"
            current["recommended_action"] = "keep"
            current["evidence_refs"] = visual_evidence_refs(memory, draft_memory_update)
            current["missing_evidence"] = []
            current["support_source"] = "draft_visual_memory"
        elif status == "partially_supported" and current.get("support_status") == "partially_supported":
            current["evidence_refs"] = current.get("evidence_refs") or visual_evidence_refs(memory, draft_memory_update)
            current["missing_evidence"] = current.get("missing_evidence") or missing
        protected.append(current)

    return protected


def decide_retrieval_need(
    *,
    user_message: str,
    route: Dict[str, Any],
    memory: Dict[str, Any] | None = None,
    image_refs: Sequence[str] = (),
) -> Dict[str, Any]:
    text = user_message.lower()
    task_type = str(route.get("task_type") or "")
    treatment_tokens = ["treatment", "management", "spray", "fungicide", "chemical", "rate"]
    source_tokens = ["source", "wiki", "paper", "literature", "evidence", "citation"]

    if image_refs or task_type == "visual_intake_or_diagnosis":
        return {
            "retrieval_decision": "retrieve",
            "retrieval_reason": "Visual diagnosis needs the wiki diagnostic procedure and disease evidence pages.",
            "must_retrieve": True,
        }
    if any(token in text for token in treatment_tokens):
        return {
            "retrieval_decision": "retrieve",
            "retrieval_reason": "Treatment or management claims require reviewed source-policy context.",
            "must_retrieve": True,
        }
    if task_type in {"knowledge_management", "data_management"} or any(token in text for token in source_tokens):
        return {
            "retrieval_decision": "retrieve",
            "retrieval_reason": f"{task_type or 'This request'} needs selected project or wiki context.",
            "must_retrieve": True,
        }
    if task_type == "grape_leaf_chat":
        return {
            "retrieval_decision": "retrieve",
            "retrieval_reason": "Grape leaf questions should stay grounded in wiki disease and procedure pages.",
            "must_retrieve": False,
        }
    if memory and any(memory.get(key) for key in ["summary", "current_diagnosis", "evidence_present"]):
        return {
            "retrieval_decision": "no_retrieve",
            "retrieval_reason": "The request can likely be answered from current session memory.",
            "must_retrieve": False,
        }
    return {
        "retrieval_decision": "no_retrieve",
        "retrieval_reason": "No domain, source, treatment, or visual-diagnosis cue was detected.",
        "must_retrieve": False,
    }


def extract_atomic_claims(
    *,
    backend: Any,
    user_message: str,
    assistant_message: str,
    memory_update: Dict[str, Any] | None,
    route: Dict[str, Any],
    max_output_tokens: int = 1000,
) -> Tuple[List[Dict[str, Any]], Any | None]:
    if is_echo_backend(backend):
        return [], None
    prompt = f"""You are the claim extraction stage for GopherEye's Chat Agent.

Extract only independent factual, diagnostic, treatment, visual-observation,
or system-behavior claims that would matter for correctness. Do not extract
small talk or purely stylistic text.

Return ONLY valid JSON:
{{
  "claims": [
    {{
      "claim_id": "claim_001",
      "claim": "one independent claim",
      "claim_type": "visual_observation|diagnosis|treatment|source_fact|system_behavior|data|other",
      "risk_level": "low|medium|high"
    }}
  ]
}}

High risk includes diagnosis labels, treatment/management advice, confirmed
status, ground-truth claims, and single-surface sufficiency decisions.

User message:
{user_message}

Route JSON:
{compact_json(route, 1600)}

Draft assistant_message:
{assistant_message}

Draft memory_update JSON:
{compact_json(memory_update or {}, 5000)}
"""
    fallback = {"claims": []}
    parsed, response = call_json_object(
        backend,
        prompt,
        fallback=fallback,
        max_output_tokens=max_output_tokens,
    )
    items = _extract_claims_payload(parsed) or parsed.get("items", [])
    claims = []
    for idx, item in enumerate(items, start=1):
        normalized = normalize_claim(item, index=idx)
        if normalized:
            claims.append(normalized)
    return claims[:16], response


def check_claim_support(
    *,
    backend: Any,
    claims: Sequence[Dict[str, Any]],
    selected_pages: Sequence[Dict[str, Any]],
    memory: Dict[str, Any] | None,
    route: Dict[str, Any],
    assistant_message: str,
    draft_memory_update: Dict[str, Any] | None = None,
    max_output_tokens: int = 1600,
) -> Tuple[Dict[str, Any], Any | None]:
    if not claims:
        return {
            "claim_support": [],
            "overall_support_status": "not_checked",
            "needs_refinement": False,
            "needs_human_review": False,
            "usefulness_score": 3,
        }, None

    page_blocks = []
    for page in selected_pages:
        path = page.get("path")
        title = page.get("title")
        page_blocks.append(
            f"[PAGE path={path} title={title}]\n{trim_text(page.get('text') or '', 1600)}\n[/PAGE]"
        )
    selected_context = "\n\n".join(page_blocks) or "(no selected pages)"

    if is_echo_backend(backend):
        support = deterministic_chat_support(
            claims,
            selected_pages=selected_pages,
            memory=memory,
            draft_memory_update=draft_memory_update,
            assistant_message=assistant_message,
        )
        support = enforce_chat_support_policies(support, selected_pages)
        return build_support_summary(support), None

    prompt = f"""You are the claim-support critic for GopherEye's Chat Agent.

Decide whether each claim is supported by the selected pages, the draft
memory_update, the compact session memory, and the draft answer. Do not use
outside facts.

Return ONLY valid JSON:
{{
  "claim_support": [
    {{
      "claim_id": "claim_001",
      "claim": "same claim text",
      "claim_type": "visual_observation|diagnosis|treatment|source_fact|system_behavior|data|other",
      "support_status": "fully_supported|partially_supported|no_support|not_checked",
      "evidence_refs": ["wiki/path.md or memory field"],
      "missing_evidence": [],
      "risk_level": "low|medium|high",
      "recommended_action": "keep|hedge|remove|ask_followup|human_review"
    }}
  ],
  "overall_support_status": "fully_supported|partially_supported|no_support|not_checked",
  "needs_refinement": true,
  "needs_human_review": false,
  "usefulness_score": 1
}}

Hard rules:
- For visual_observation claims, treat Draft memory_update visual_intakes and
  evidence_present as the primary current-turn image evidence. Do not mark a
  visual observation unsupported just because it is absent from previous session
  memory.
- Treatment claims require a selected treatment/source-policy page.
- Confirmed diagnosis claims without reviewed/human confirmation are no_support.
- Claims that say a disease is "not confirmed" or "unconfirmed" are
  conservative differential statements, not confirmed diagnosis assertions.
- Single-surface sufficiency claims must be supported by image_and_evidence_sop
  and visible evidence.
- no_support + high risk => remove or ask_followup.
- partially_supported diagnosis => hedge.

Claims JSON:
{compact_json(list(claims), 4000)}

Route JSON:
{compact_json(route, 1600)}

Draft memory_update JSON:
{compact_json(draft_memory_update or {}, 6000)}

Previous session memory JSON:
{compact_json(memory or {}, 2500)}

Draft assistant_message:
{assistant_message}

Selected context pages:
{selected_context}
"""
    fallback = {"claim_support": []}
    parsed, response = call_json_object(
        backend,
        prompt,
        fallback=fallback,
        max_output_tokens=max_output_tokens,
    )
    support_items = _extract_support_payload(parsed)
    support: List[Dict[str, Any]] = []
    for idx, item in enumerate(support_items, start=1):
        normalized = normalize_claim_support(item, index=idx, known_claims=claims)
        if normalized:
            support.append(normalized)
    if not support:
        support = deterministic_chat_support(
            claims,
            selected_pages=selected_pages,
            memory=memory,
            draft_memory_update=draft_memory_update,
            assistant_message=assistant_message,
        )
        for item in support:
            item.setdefault("support_source", "deterministic_fallback")
    support = protect_visual_support_from_draft(
        support,
        claims=claims,
        selected_pages=selected_pages,
        memory=memory,
        draft_memory_update=draft_memory_update,
        assistant_message=assistant_message,
    )
    support = enforce_chat_support_policies(support, selected_pages)
    summary = build_support_summary(support)
    return summary, response


def enforce_chat_support_policies(
    support: Sequence[Dict[str, Any]],
    selected_pages: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    paths = [str(page.get("path") or "").lower() for page in selected_pages]
    has_treatment_context = any("/treatment/" in f"/{path}" or "source_policy" in path for path in paths)
    has_image_sop = any("image_and_evidence_sop" in path for path in paths)

    out: List[Dict[str, Any]] = []
    for item in support:
        current = dict(item)
        claim_text = current.get("claim", "").lower()
        claim_type = current.get("claim_type")
        if claim_type == "treatment" and not has_treatment_context:
            current["support_status"] = "no_support"
            current["recommended_action"] = "remove"
            current["missing_evidence"] = _string_list(current.get("missing_evidence")) + [
                "No selected treatment or source-policy page supports this treatment claim."
            ]
        if claim_type == "visual_observation" and is_visual_absence_claim(claim_text):
            if current.get("support_status") == "fully_supported":
                current["support_status"] = "partially_supported"
            if current.get("recommended_action") in {"hedge", "remove", "ask_followup", "human_review"}:
                current["recommended_action"] = "keep"
            missing = _string_list(current.get("missing_evidence"))
            note = "The draft visual intake supports a not-visible statement, but absence from field imagery remains image-limited."
            if note not in missing:
                missing.append(note)
            current["missing_evidence"] = missing
        if claim_type == "diagnosis" and is_unconfirmed_diagnosis_statement(claim_text):
            if current.get("support_status") in {"no_support", "not_checked"}:
                current["support_status"] = "partially_supported"
                current["recommended_action"] = "keep"
                current["missing_evidence"] = [
                    item for item in _string_list(current.get("missing_evidence"))
                    if "confirmed diagnosis requires" not in item.lower()
                ]
        if claim_type == "diagnosis" and is_confirmed_diagnosis_assertion(claim_text):
            current["support_status"] = "no_support"
            current["recommended_action"] = "remove"
            current["missing_evidence"] = _string_list(current.get("missing_evidence")) + [
                "Confirmed diagnosis requires reviewed or human confirmation."
            ]
        if ("single surface" in claim_text or "opposite side" in claim_text) and not has_image_sop:
            if current.get("support_status") == "fully_supported":
                current["support_status"] = "partially_supported"
            current["recommended_action"] = "hedge"
            current["missing_evidence"] = _string_list(current.get("missing_evidence")) + [
                "Single-surface sufficiency should be checked against image_and_evidence_sop."
            ]
        out.append(current)
    return out


def claim_already_hedged(item: Dict[str, Any]) -> bool:
    text = str(item.get("claim") or "").lower()
    return has_any(
        text,
        [
            "may",
            "might",
            "could",
            "possible",
            "provisional",
            "provisionally",
            "unconfirmed",
            "not confirmed",
            "less favored",
            "less likely",
            "not enough",
            "insufficient",
            "unclear",
            "uncertain",
            "not clearly",
            "no clear",
            "no ",
            "without ",
            "not visible",
            "not evident",
            "would",
            "cannot",
            "needs",
            "need",
        ],
    )


def build_support_summary(support: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    statuses = [item.get("support_status") for item in support]
    if "no_support" in statuses:
        overall = "no_support"
    elif "partially_supported" in statuses:
        overall = "partially_supported"
    elif statuses and all(status == "fully_supported" for status in statuses):
        overall = "fully_supported"
    else:
        overall = "not_checked"
    needs_refinement = any(
        item.get("recommended_action") in {"remove", "ask_followup", "human_review"}
        or (
            item.get("recommended_action") == "hedge"
            and not claim_already_hedged(item)
        )
        for item in support
    )
    needs_refinement = needs_refinement or any(
        item.get("risk_level") == "high"
        and item.get("support_status") in {"no_support", "not_checked"}
        for item in support
    )
    needs_human_review = any(
        item.get("recommended_action") == "human_review"
        or (
            item.get("risk_level") == "high"
            and item.get("support_status") in {"no_support", "not_checked"}
        )
        for item in support
    )
    usefulness_score = 5
    if overall == "partially_supported":
        usefulness_score = 4 if not needs_refinement and not needs_human_review else 3
    elif overall in {"no_support", "not_checked"}:
        usefulness_score = 2
    return {
        "claim_support": list(support),
        "overall_support_status": overall,
        "needs_refinement": needs_refinement,
        "needs_human_review": needs_human_review,
        "usefulness_score": usefulness_score,
    }


def build_reflection_record(
    *,
    retrieval_decision: Dict[str, Any],
    retrieval_quality: str,
    support_summary: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "retrieval_decision": retrieval_decision.get("retrieval_decision", "retrieve"),
        "retrieval_reason": retrieval_decision.get("retrieval_reason", ""),
        "retrieval_quality": retrieval_quality,
        "claim_support": support_summary.get("claim_support", []),
        "overall_support_status": support_summary.get("overall_support_status", "not_checked"),
        "usefulness_score": int(support_summary.get("usefulness_score") or 3),
        "needs_human_review": bool(support_summary.get("needs_human_review")),
        "needs_refinement": bool(support_summary.get("needs_refinement")),
    }


def refine_with_claim_support(
    *,
    backend: Any,
    original_prompt: str,
    draft_envelope: Dict[str, Any],
    support_summary: Dict[str, Any],
    max_output_tokens: int = 2400,
) -> Tuple[str | None, Any | None]:
    if is_echo_backend(backend) or not support_summary.get("needs_refinement"):
        return None, None
    prompt = f"""You are the final refinement stage for GopherEye's Chat Agent.

Rewrite the assistant envelope so it follows the claim-support critique.
Keep fully_supported claims. Hedge partially_supported claims. Remove
no_support claims. If a high-risk unsupported claim is needed to answer, ask
one targeted follow-up instead. Do not introduce new factual claims.
For visual observations supported by draft_memory.visual_intakes or
draft_memory.evidence_present, preserve the concrete visible features in
memory_update.visual_intakes and memory_update.evidence_present. Do not replace
supported visual intake with generic "not established" placeholders. If a
diagnosis is too strong, weaken only the diagnosis wording.

Return ONLY valid JSON with the same shape:
{{
  "assistant_message": "English user-facing answer",
  "memory_update": {{ }}
}}

Original task prompt:
{trim_text(original_prompt, 5000)}

Draft assistant envelope JSON:
{compact_json(draft_envelope, 6000)}

Claim support critique JSON:
{compact_json(support_summary, 6000)}
"""
    try:
        response = backend.generate(prompt, max_output_tokens=max_output_tokens)
    except Exception as exc:
        return None, {"reflection_error": f"{type(exc).__name__}: {exc}"}
    return response.text, response


def source_claims_from_research_facts(research: Dict[str, Any]) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    for idx, fact in enumerate(research.get("facts", []) if isinstance(research.get("facts"), list) else [], start=1):
        if not isinstance(fact, dict):
            continue
        claim = str(fact.get("claim") or "").strip()
        if not claim:
            continue
        item = normalize_claim(
            {
                "claim_id": stable_id("source_claim", idx, claim, fact.get("source_url")),
                "claim": claim,
                "claim_type": "source_fact",
                "risk_level": "medium",
                "source_url": fact.get("source_url"),
                "source_title": fact.get("source_title"),
            },
            index=idx,
            prefix="source_claim",
        )
        if item:
            claims.append(item)
    return claims


def extract_source_claims(
    *,
    backend: Any,
    query: str,
    research: Dict[str, Any],
    max_output_tokens: int = 1600,
) -> Tuple[List[Dict[str, Any]], Any | None]:
    fallback_claims = source_claims_from_research_facts(research)
    if is_echo_backend(backend):
        return fallback_claims, None
    prompt = f"""You are the source-claim extraction stage for the GopherEye Wiki Update Agent.

Extract atomic, source-backed claims from the research JSON. Each claim must be
small enough to verify and either add to a wiki page or skip as duplicate.

Return ONLY valid JSON:
{{
  "source_claims": [
    {{
      "claim_id": "source_claim_001",
      "claim": "one atomic source-backed claim",
      "claim_type": "source_fact|treatment|diagnosis|visual_observation|other",
      "source_url": "https://...",
      "source_title": "source title",
      "target_entities": ["downy_mildew", "oil_spots"],
      "risk_level": "low|medium|high"
    }}
  ]
}}

Rules:
- Use claims already supported by the research facts/sources.
- Do not invent source URLs.
- Treatment, chemical, rate, timing, or legal-use claims are high risk.
- Return at most 12 source_claims.

Wiki update query:
{query}

Research JSON:
{compact_json(research, 10000)}
"""
    parsed, response = call_json_object(
        backend,
        prompt,
        fallback={"source_claims": fallback_claims},
        max_output_tokens=max_output_tokens,
    )
    items = _extract_claims_payload(parsed) or parsed.get("items", []) or fallback_claims
    claims: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        normalized = normalize_claim(item, index=idx, prefix="source_claim")
        if normalized:
            claims.append(normalized)
    return claims[:12], response


def verify_source_claims(
    *,
    backend: Any,
    query: str,
    source_claims: Sequence[Dict[str, Any]],
    research: Dict[str, Any],
    max_output_tokens: int = 2000,
) -> Tuple[Dict[str, Any], Any | None]:
    if not source_claims:
        return {
            "claim_support": [],
            "verified_claims": [],
            "unclear_points": ["No source claims were extracted from the research."],
        }, None
    if is_echo_backend(backend):
        support = []
        for idx, claim in enumerate(source_claims, start=1):
            item = normalize_claim_support(
                {
                    **claim,
                    "support_status": "not_checked",
                    "recommended_action": "human_review",
                    "missing_evidence": ["Echo backend did not verify source claims."],
                },
                index=idx,
                known_claims=source_claims,
            )
            if item:
                support.append(item)
        return {
            "claim_support": support,
            "verified_claims": [],
            "unclear_points": ["Run with a real model profile to verify source claims before wiki edits."],
        }, None

    prompt = f"""You are the source-claim verification stage for the GopherEye Wiki Update Agent.

Verify each source claim against the research JSON only. Do not use outside
knowledge. A claim is fully_supported only when the research gives a concrete
source URL and the claim is directly supported by that source summary/fact.

Return ONLY valid JSON:
{{
  "claim_support": [
    {{
      "claim_id": "source_claim_001",
      "claim": "same claim",
      "claim_type": "source_fact|treatment|diagnosis|visual_observation|other",
      "support_status": "fully_supported|partially_supported|no_support|not_checked",
      "source_refs": ["https://..."],
      "source_quality": "extension|university|government|peer_reviewed|official|unknown",
      "missing_evidence": [],
      "risk_level": "low|medium|high",
      "recommended_action": "keep|hedge|remove|ask_followup|human_review"
    }}
  ],
  "unclear_points": []
}}

Hard rules:
- partially_supported or no_support claims must not be written to wiki.
- Treatment/rate/legal-use claims require authoritative current support.
- If a source URL is missing, the claim is not fully_supported.

Wiki update query:
{query}

Source claims JSON:
{compact_json(list(source_claims), 6000)}

Research JSON:
{compact_json(research, 10000)}
"""
    parsed, response = call_json_object(
        backend,
        prompt,
        fallback={"claim_support": []},
        max_output_tokens=max_output_tokens,
    )
    support: List[Dict[str, Any]] = []
    for idx, item in enumerate(_extract_support_payload(parsed), start=1):
        normalized = normalize_claim_support(item, index=idx, known_claims=source_claims)
        if normalized:
            if not normalized.get("evidence_refs") and normalized.get("source_url"):
                normalized["evidence_refs"] = [normalized["source_url"]]
            support.append(normalized)
    if not support:
        for idx, claim in enumerate(source_claims, start=1):
            normalized = normalize_claim_support(
                {
                    **claim,
                    "support_status": "not_checked",
                    "recommended_action": "human_review",
                    "missing_evidence": ["Source verifier did not return a usable record."],
                },
                index=idx,
                known_claims=source_claims,
            )
            if normalized:
                support.append(normalized)
    verified = [
        item for item in support
        if item.get("support_status") == "fully_supported"
        and item.get("recommended_action") in {"keep", "hedge"}
        and not item.get("conflicts_with_wiki")
    ]
    return {
        "claim_support": support,
        "verified_claims": verified,
        "unclear_points": _string_list(parsed.get("unclear_points") if isinstance(parsed, dict) else None, max_items=12),
    }, response
