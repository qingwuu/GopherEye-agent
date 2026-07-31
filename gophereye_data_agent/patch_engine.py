from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from src.gophereye_runtime.utils import read_json, stable_id, write_json

from .manifest_store import read_manifest, write_manifest
from .paths import DEFAULT_WORKSPACE_ROOT, normalize_path, root_relative
from .schemas import InstanceTarget, JsonPatchAction, OperationResult
from .storage import write_instance_audit
from .targets import INSTANCE_FILES


def decode_pointer(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer}")
    if pointer == "/":
        return [""]
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer.lstrip("/").split("/")]


def set_nested(value: Any, pointer: str, new_value: Any) -> None:
    parts = decode_pointer(pointer)
    node = value
    for part in parts[:-1]:
        if isinstance(node, dict):
            node = node.setdefault(part, {})
        elif isinstance(node, list):
            node = node[int(part)]
        else:
            raise ValueError(f"Cannot descend into {type(node).__name__} at {part}")
    last = parts[-1]
    if isinstance(node, dict):
        node[last] = new_value
    elif isinstance(node, list):
        idx = len(node) if last == "-" else int(last)
        if idx == len(node):
            node.append(new_value)
        else:
            node[idx] = new_value
    else:
        raise ValueError(f"Cannot set value on {type(node).__name__}")


def add_to_list(value: Any, pointer: str, new_value: Any) -> None:
    parts = decode_pointer(pointer)
    node = value
    for part in parts:
        if isinstance(node, dict):
            node = node.setdefault(part, [])
        elif isinstance(node, list):
            node = node[int(part)]
        else:
            raise ValueError(f"Cannot descend into {type(node).__name__} at {part}")
    if not isinstance(node, list):
        raise ValueError(f"Target is not a list: {pointer}")
    node.append(new_value)


def remove_key(value: Any, pointer: str) -> None:
    parts = decode_pointer(pointer)
    node = value
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    last = parts[-1]
    if isinstance(node, dict):
        node.pop(last, None)
    elif isinstance(node, list):
        node.pop(int(last))
    else:
        raise ValueError(f"Cannot remove from {type(node).__name__}")


def file_path_for_action(target: InstanceTarget, action: JsonPatchAction, workspace_root: Path = DEFAULT_WORKSPACE_ROOT) -> Path | None:
    if not target.instance_dir:
        return None
    instance_dir = normalize_path(target.instance_dir)
    if action.file == "custom":
        if not action.custom_file:
            raise ValueError("custom_file is required when action.file is custom")
        return instance_dir / action.custom_file
    filename = INSTANCE_FILES[action.file]
    return instance_dir / filename


def apply_action(value: dict[str, Any], action: JsonPatchAction) -> dict[str, Any]:
    updated = copy.deepcopy(value)
    if action.op == "set":
        set_nested(updated, action.json_pointer, action.value)
    elif action.op == "add_to_list":
        add_to_list(updated, action.json_pointer, action.value)
    elif action.op == "remove_key":
        remove_key(updated, action.json_pointer)
    else:
        raise ValueError(f"Unsupported patch op: {action.op}")
    return updated


def patch_instances(
    targets: list[InstanceTarget],
    actions: list[JsonPatchAction],
    *,
    job_dir: Path,
    apply: bool,
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
) -> OperationResult:
    if not actions:
        return OperationResult(
            operation_type="modify_instance_json",
            status="skipped",
            message="No patch actions were provided.",
            targets_seen=len(targets),
        )
    if any(target.source.get("kind") == "manifest_row" for target in targets):
        return patch_manifest_rows(targets, actions, job_dir=job_dir, apply=apply, workspace_root=workspace_root)

    changed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for target in targets:
        for action in actions:
            try:
                path = file_path_for_action(target, action, workspace_root=workspace_root)
                if path is None or not path.exists():
                    errors.append({"instance_id": target.instance_id, "action": action.model_dump(), "error": "target file missing"})
                    continue
                before = read_json(path)
                if not isinstance(before, dict):
                    errors.append({"instance_id": target.instance_id, "path": root_relative(path), "error": "target file is not an object"})
                    continue
                after = apply_action(before, action)
                backup_path = job_dir / "backups" / target.instance_id / path.name
                if apply:
                    write_json(backup_path, before)
                    write_json(path, after)
                    write_instance_audit(
                        path.parent,
                        {
                            "event_id": stable_id("event", "gophereye_data_agent_patch", target.instance_id, action.model_dump()),
                            "event_type": "gophereye_data_agent_patch",
                            "instance_id": target.instance_id,
                            "file": path.name,
                            "json_pointer": action.json_pointer,
                            "op": action.op,
                            "reason": action.reason,
                            "backup_path": root_relative(backup_path),
                        },
                    )
                changed.append(
                    {
                        "instance_id": target.instance_id,
                        "file": root_relative(path),
                        "json_pointer": action.json_pointer,
                        "op": action.op,
                        "applied": apply,
                    }
                )
            except Exception as exc:
                errors.append({"instance_id": target.instance_id, "action": action.model_dump(), "error": str(exc)})

    status = "ok" if not errors else "partial" if changed else "failed"
    return OperationResult(
        operation_type="modify_instance_json",
        status="ok" if status in {"ok", "partial"} else "failed",
        message=f"{len(changed)} patch actions {'applied' if apply else 'planned'}; {len(errors)} errors.",
        targets_seen=len(targets),
        details={"changed": changed, "errors": errors},
    )


def patch_manifest_rows(
    targets: list[InstanceTarget],
    actions: list[JsonPatchAction],
    *,
    job_dir: Path,
    apply: bool,
    workspace_root: Path,
) -> OperationResult:
    rows = read_manifest(workspace_root)
    target_ids = {target.instance_id for target in targets}
    changed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    updated_rows = []
    for row in rows:
        if str(row.get("instance_id")) not in target_ids:
            updated_rows.append(row)
            continue
        current = copy.deepcopy(row)
        try:
            for action in actions:
                current = apply_action(current, action)
            changed.append(
                {
                    "instance_id": row.get("instance_id"),
                    "file": root_relative(workspace_root / "dataset_manifest.jsonl"),
                    "actions": len(actions),
                    "applied": apply,
                }
            )
        except Exception as exc:
            errors.append({"instance_id": row.get("instance_id"), "error": str(exc)})
            current = row
        updated_rows.append(current)

    if apply and changed:
        write_json(job_dir / "backups" / "dataset_manifest.before.json", rows)
        write_manifest(workspace_root, updated_rows)

    status = "ok" if not errors else "failed" if not changed else "ok"
    return OperationResult(
        operation_type="modify_manifest",
        status=status,
        message=f"{len(changed)} manifest rows {'updated' if apply else 'planned'}; {len(errors)} errors.",
        targets_seen=len(targets),
        artifacts=[root_relative(workspace_root / "dataset_manifest.csv") or str(workspace_root / "dataset_manifest.csv")],
        details={"changed": changed, "errors": errors},
    )
