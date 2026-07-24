from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .config import ModelProfile
from .image_io import image_ref_to_anthropic_block, image_ref_to_data_url


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
        image_refs: Sequence[str] = (),
        max_output_tokens: int = 900,
    ) -> ModelResponse:
        raise NotImplementedError

    def _check_images(self, image_refs: Sequence[str]) -> None:
        if image_refs and not self.profile.supports_images:
            raise ValueError(
                f"Profile '{self.profile.name}' is not configured for image inputs. "
                "Use a vision-capable profile or set supports_images=true after verifying the model."
            )


class EchoBackend(ModelBackend):
    def generate(
        self,
        prompt: str,
        *,
        image_refs: Sequence[str] = (),
        max_output_tokens: int = 900,
    ) -> ModelResponse:
        text = {
            "assistant_message": (
                "Echo backend received the request. Select a real profile such as "
                "openai_frontier, anthropic_frontier, kimi, or qwen_local for model output."
            ),
            "agent_trace": {
                "task_type": "echo",
                "selected_agent_path": ["router", "echo"],
                "needs_follow_up": False,
            },
            "memory_update": {
                "summary": "Echo test run; no model diagnosis was performed.",
                "user_goal": None,
                "current_diagnosis": None,
                "known_image_updates": [],
                "visual_intakes": [],
                "evidence_present": [],
                "evidence_missing": [],
                "recommended_next_image": None,
                "allowed_follow_up_questions": [],
                "open_questions": [],
            },
        }
        return ModelResponse(text=json.dumps(text, ensure_ascii=False))


class OpenAIResponsesBackend(ModelBackend):
    def generate(
        self,
        prompt: str,
        *,
        image_refs: Sequence[str] = (),
        max_output_tokens: int = 900,
    ) -> ModelResponse:
        self._check_images(image_refs)
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass

        from openai import OpenAI

        api_key = os.getenv(self.profile.api_key_env or "OPENAI_API_KEY")
        client = OpenAI(api_key=api_key or None)

        content: List[Dict[str, Any]] = [{"type": "input_text", "text": prompt}]
        for image_ref in image_refs:
            content.append({"type": "input_image", "image_url": image_ref_to_data_url(image_ref)})

        response = client.responses.create(
            model=self.profile.model,
            input=[{"role": "user", "content": content}],
            max_output_tokens=max_output_tokens,
        )
        text = getattr(response, "output_text", None) or ""
        usage = {}
        if getattr(response, "usage", None) is not None:
            usage = response.usage.model_dump() if hasattr(response.usage, "model_dump") else dict(response.usage)
        return ModelResponse(text=text.strip(), usage=usage)


class OpenAIChatCompatibleBackend(ModelBackend):
    def generate(
        self,
        prompt: str,
        *,
        image_refs: Sequence[str] = (),
        max_output_tokens: int = 900,
    ) -> ModelResponse:
        self._check_images(image_refs)
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass

        from openai import OpenAI

        api_key = os.getenv(self.profile.api_key_env or "OPENAI_API_KEY")
        client = OpenAI(api_key=api_key or None, base_url=self.profile.base_url)

        if image_refs:
            content: Any = [{"type": "text", "text": prompt}]
            for image_ref in image_refs:
                content.append({"type": "image_url", "image_url": {"url": image_ref_to_data_url(image_ref)}})
        else:
            content = prompt

        response = client.chat.completions.create(
            model=self.profile.model,
            messages=[{"role": "user", "content": content}],
            max_tokens=max_output_tokens,
            temperature=0,
        )
        choice = response.choices[0]
        text = choice.message.content or ""
        usage = {}
        if getattr(response, "usage", None) is not None:
            usage = response.usage.model_dump() if hasattr(response.usage, "model_dump") else dict(response.usage)
        return ModelResponse(text=text.strip(), usage=usage)


class AnthropicMessagesBackend(ModelBackend):
    def generate(
        self,
        prompt: str,
        *,
        image_refs: Sequence[str] = (),
        max_output_tokens: int = 900,
    ) -> ModelResponse:
        self._check_images(image_refs)
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass

        from anthropic import Anthropic

        api_key = os.getenv(self.profile.api_key_env or "ANTHROPIC_API_KEY")
        client = Anthropic(api_key=api_key or None)

        content: List[Dict[str, Any]] = []
        for idx, image_ref in enumerate(image_refs, start=1):
            content.append({"type": "text", "text": f"Image {idx}:"})
            content.append(image_ref_to_anthropic_block(image_ref))
        content.append({"type": "text", "text": prompt})

        response = client.messages.create(
            model=self.profile.model,
            max_tokens=max_output_tokens,
            messages=[{"role": "user", "content": content}],
        )
        texts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                texts.append(getattr(block, "text", ""))
        usage = {}
        if getattr(response, "usage", None) is not None:
            usage = response.usage.model_dump() if hasattr(response.usage, "model_dump") else dict(response.usage)
        return ModelResponse(text="\n".join(texts).strip(), usage=usage)


class LocalWikiBackend(ModelBackend):
    def generate(
        self,
        prompt: str,
        *,
        image_refs: Sequence[str] = (),
        max_output_tokens: int = 900,
    ) -> ModelResponse:
        repo_root = Path(__file__).resolve().parents[2]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from src.single_model_wiki.core import run_model_with_images

        local_provider = self.profile.local_provider or "qwen-vl"
        text = run_model_with_images(
            prompt,
            provider=local_provider,
            model=self.profile.model,
            image_refs=image_refs,
            max_new_tokens=max_output_tokens,
        )
        return ModelResponse(text=text.strip(), backend_meta={"local_provider": local_provider})


def create_backend(profile: ModelProfile) -> ModelBackend:
    if profile.provider == "echo":
        return EchoBackend(profile)
    if profile.provider == "openai_responses":
        return OpenAIResponsesBackend(profile)
    if profile.provider == "openai_chat_compatible":
        return OpenAIChatCompatibleBackend(profile)
    if profile.provider == "anthropic_messages":
        return AnthropicMessagesBackend(profile)
    if profile.provider == "local_wiki":
        return LocalWikiBackend(profile)
    raise ValueError(f"Unsupported provider type: {profile.provider}")
