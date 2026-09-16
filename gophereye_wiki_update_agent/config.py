from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


AGENT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = AGENT_DIR / "models.example.json"


@dataclass(frozen=True)
class ModelProfile:
    name: str
    provider: str
    model: str
    api_key_env: str | None = None
    web_search_tool: str | None = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelConfig:
    default_profile: str
    profiles: Dict[str, ModelProfile]

    def get_profile(self, name: str | None) -> ModelProfile:
        profile_name = name or self.default_profile
        try:
            return self.profiles[profile_name]
        except KeyError as exc:
            valid = ", ".join(sorted(self.profiles))
            raise ValueError(f"Unknown model profile '{profile_name}'. Valid profiles: {valid}") from exc


def load_model_config(path: str | Path | None = None) -> ModelConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    profiles: Dict[str, ModelProfile] = {}
    known_keys = {"provider", "model", "api_key_env", "web_search_tool"}
    for name, item in raw.get("profiles", {}).items():
        if not isinstance(item, dict):
            raise ValueError(f"Profile '{name}' must be an object")
        extra = {key: value for key, value in item.items() if key not in known_keys}
        profiles[name] = ModelProfile(
            name=name,
            provider=str(item["provider"]),
            model=str(item["model"]),
            api_key_env=item.get("api_key_env"),
            web_search_tool=item.get("web_search_tool"),
            extra=extra,
        )
    if not profiles:
        raise ValueError(f"No model profiles found in {config_path}")
    default_profile = str(raw.get("default_profile") or next(iter(profiles)))
    if default_profile not in profiles:
        raise ValueError(f"default_profile '{default_profile}' is not in profiles")
    return ModelConfig(default_profile=default_profile, profiles=profiles)
