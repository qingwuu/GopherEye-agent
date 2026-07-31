from __future__ import annotations

from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import normalize_repo_path, root_relative as runtime_root_relative


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE_ROOT = REPO_ROOT / "gophereye_data_workspace"
DEFAULT_JOB_ROOT = DEFAULT_WORKSPACE_ROOT / "runs"
DEFAULT_AGENT_ARTIFACT_ROOT = DEFAULT_WORKSPACE_ROOT / "agent_artifacts"
DEFAULT_YOLO_SEG_MODEL = REPO_ROOT / "model" / "yolo_grape.pt"


def normalize_path(path_text: str | Path) -> Path:
    return normalize_repo_path(REPO_ROOT, path_text)


def root_relative(path: str | Path | None) -> str | None:
    return runtime_root_relative(REPO_ROOT, path)


def jsonable_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return root_relative(Path(path))


def optional_import(module_name: str) -> Any | None:
    try:
        module = __import__(module_name)
    except Exception:
        return None
    return module
