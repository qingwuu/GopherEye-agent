from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import now_utc, read_jsonl, timestamp_id, write_json, write_jsonl

from .paths import DEFAULT_AGENT_ARTIFACT_ROOT, DEFAULT_JOB_ROOT, root_relative


def ensure_runtime_dirs(job_root: Path = DEFAULT_JOB_ROOT, artifact_root: Path = DEFAULT_AGENT_ARTIFACT_ROOT) -> None:
    for path in [job_root, artifact_root]:
        path.mkdir(parents=True, exist_ok=True)


def new_job_id(prefix: str = "dagent") -> str:
    return f"{prefix}_{timestamp_id()}_{uuid.uuid4().hex[:8]}"


def create_job_dir(job_root: Path = DEFAULT_JOB_ROOT, job_id: str | None = None) -> Path:
    ensure_runtime_dirs(job_root=job_root)
    path: Path | None = None
    for _ in range(5):
        job = job_id or new_job_id()
        path = job_root / job
        try:
            path.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            if job_id:
                raise
            path = None
    if path is None:
        raise FileExistsError(f"Could not create a unique Data Agent job directory under {job_root}")
    for child in ["artifacts"]:
        (path / child).mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    rows = read_jsonl(path)
    rows.append(row)
    write_jsonl(path, rows)


def write_job_json(job_dir: Path, name: str, value: Any) -> Path:
    path = job_dir / name
    write_json(path, value)
    return path


def write_audit_event(job_dir: Path, event: dict[str, Any]) -> None:
    event = {"created_at": now_utc(), **event}
    append_jsonl(job_dir / "audit_events.jsonl", event)


def write_instance_audit(instance_dir: Path, event: dict[str, Any]) -> None:
    event = {"created_at": now_utc(), **event}
    append_jsonl(instance_dir / "audit_events.jsonl", event)


def safe_json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def artifact_ref(path: Path) -> str:
    return root_relative(path) or str(path)
