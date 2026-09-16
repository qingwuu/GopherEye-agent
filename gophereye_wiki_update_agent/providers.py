from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from .config import ModelProfile


@dataclass
class ModelResponse:
    text: str
    usage: Dict[str, Any] = field(default_factory=dict)
    backend_meta: Dict[str, Any] = field(default_factory=dict)


class ModelBackend:
    def __init__(self, profile: ModelProfile):
        self.profile = profile

    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 1600,
        web_search: bool = False,
        max_web_uses: int = 5,
        allowed_domains: Sequence[str] = (),
    ) -> ModelResponse:
        raise NotImplementedError


class EchoBackend(ModelBackend):
    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 1600,
        web_search: bool = False,
        max_web_uses: int = 5,
        allowed_domains: Sequence[str] = (),
    ) -> ModelResponse:
        if "Return ONLY a JSON array of page IDs" in prompt:
            return ModelResponse(text="[]", backend_meta={"echo": True})
        if '"operations"' in prompt and "Wiki update operations" in prompt:
            payload = {
                "source_summary": "Echo profile did not perform web search.",
                "operations": [],
                "unclear_points": ["Run with an OpenAI or Anthropic profile to update the wiki."],
            }
            return ModelResponse(text=json.dumps(payload), backend_meta={"echo": True})
        payload = {
            "query": "echo",
            "source_summary": "Echo profile did not perform web search.",
            "facts": [],
            "sources": [],
            "unclear_points": ["Run with an OpenAI or Anthropic profile for live web research."],
        }
        return ModelResponse(text=json.dumps(payload), backend_meta={"echo": True})


class OpenAIResponsesBackend(ModelBackend):
    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 1600,
        web_search: bool = False,
        max_web_uses: int = 5,
        allowed_domains: Sequence[str] = (),
    ) -> ModelResponse:
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass

        from openai import OpenAI

        api_key = os.getenv(self.profile.api_key_env or "OPENAI_API_KEY")
        client = OpenAI(api_key=api_key or None)
        content = [{"type": "input_text", "text": prompt}]
        request: Dict[str, Any] = {
            "model": self.profile.model,
            "input": [{"role": "user", "content": content}],
            "max_output_tokens": max_output_tokens,
        }

        tool_type = self.profile.web_search_tool or "web_search_preview"
        attempted_tools: List[str] = []
        errors: List[str] = []
        tool_variants = [tool_type]
        if web_search and tool_type != "web_search":
            tool_variants.append("web_search")

        if not web_search:
            response = client.responses.create(**request)
            return _openai_response_to_model_response(response, {"web_search": False})

        for candidate_tool in tool_variants:
            attempted_tools.append(candidate_tool)
            try:
                response = client.responses.create(
                    **request,
                    tools=[{"type": candidate_tool, "search_context_size": "low"}],
                )
                return _openai_response_to_model_response(
                    response,
                    {
                        "web_search": True,
                        "web_search_tool": candidate_tool,
                        "allowed_domains_requested": list(allowed_domains),
                        "allowed_domains_supported": False,
                    },
                )
            except Exception as exc:
                errors.append(f"{candidate_tool}: {exc}")

        raise RuntimeError("OpenAI web search request failed: " + " | ".join(errors))


class AnthropicMessagesBackend(ModelBackend):
    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 1600,
        web_search: bool = False,
        max_web_uses: int = 5,
        allowed_domains: Sequence[str] = (),
    ) -> ModelResponse:
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass

        from anthropic import Anthropic

        api_key = os.getenv(self.profile.api_key_env or "ANTHROPIC_API_KEY")
        client = Anthropic(api_key=api_key or None)
        messages: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
        tools = None
        if web_search:
            tool: Dict[str, Any] = {
                "type": self.profile.web_search_tool or "web_search_20250305",
                "name": "web_search",
                "max_uses": max_web_uses,
            }
            if allowed_domains:
                tool["allowed_domains"] = list(allowed_domains)
            tools = [tool]

        texts: List[str] = []
        usage: Dict[str, Any] = {}
        meta: Dict[str, Any] = {
            "web_search": web_search,
            "web_search_tool": (tools or [{}])[0].get("type") if tools else None,
            "allowed_domains_requested": list(allowed_domains),
            "allowed_domains_supported": bool(allowed_domains) if tools else False,
            "pause_turns": 0,
        }
        for _ in range(3):
            request: Dict[str, Any] = {
                "model": self.profile.model,
                "max_tokens": max_output_tokens,
                "messages": messages,
            }
            if tools:
                request["tools"] = tools
            response = client.messages.create(**request)
            texts.extend(_anthropic_text_blocks(response.content))
            if getattr(response, "usage", None) is not None:
                usage = (
                    response.usage.model_dump()
                    if hasattr(response.usage, "model_dump")
                    else dict(response.usage)
                )
            if getattr(response, "stop_reason", None) != "pause_turn":
                break
            meta["pause_turns"] += 1
            messages.append({"role": "assistant", "content": _anthropic_blocks_to_dicts(response.content)})

        return ModelResponse(text="\n".join(texts).strip(), usage=usage, backend_meta=meta)


def _openai_response_to_model_response(response: Any, meta: Dict[str, Any]) -> ModelResponse:
    text = getattr(response, "output_text", None) or ""
    usage = {}
    if getattr(response, "usage", None) is not None:
        usage = response.usage.model_dump() if hasattr(response.usage, "model_dump") else dict(response.usage)
    return ModelResponse(text=text.strip(), usage=usage, backend_meta=meta)


def _anthropic_text_blocks(blocks: Any) -> List[str]:
    texts: List[str] = []
    for block in blocks or []:
        if getattr(block, "type", None) == "text":
            texts.append(getattr(block, "text", ""))
        elif isinstance(block, dict) and block.get("type") == "text":
            texts.append(str(block.get("text") or ""))
    return texts


def _anthropic_blocks_to_dicts(blocks: Any) -> List[Dict[str, Any]]:
    values: List[Dict[str, Any]] = []
    for block in blocks or []:
        if hasattr(block, "model_dump"):
            values.append(block.model_dump(exclude_none=True))
        elif isinstance(block, dict):
            values.append(block)
        else:
            values.append({"type": getattr(block, "type", "text"), "text": str(block)})
    return values


def create_backend(profile: ModelProfile) -> ModelBackend:
    if profile.provider == "echo":
        return EchoBackend(profile)
    if profile.provider == "openai_responses":
        return OpenAIResponsesBackend(profile)
    if profile.provider == "anthropic_messages":
        return AnthropicMessagesBackend(profile)
    raise ValueError(f"Unsupported provider type: {profile.provider}")
