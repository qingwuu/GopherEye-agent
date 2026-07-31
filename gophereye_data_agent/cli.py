from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from src.gophereye_runtime.utils import read_json, safe_print, write_json

from . import __version__
from .agents_runtime import agents_sdk_status
from .executor import execute_plan, summarize_job_result
from .language_prompt import build_language_prompt_plan
from .mcp_server import mcp_status, run_mcp_server
from .sample_import import import_image_samples
from .paths import normalize_path, root_relative
from .planner import make_plan
from .schemas import DataOperation, JsonPatchAction, OperationPlan, OperationType, TargetSelector


app = typer.Typer(help="Independent GopherEye Data Agent CLI.")
console = Console()
CLI_DEFAULT_WORKSPACE_ROOT = Path("gophereye_data_workspace")
CLI_DEFAULT_JOB_ROOT = Path("gophereye_data_workspace/runs")


def print_json(value: object) -> None:
    safe_print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def print_job_summary(result: object) -> None:
    print_json(summarize_job_result(result))  # type: ignore[arg-type]


def parse_sample_ids(sample_ids: str | None, pair_ids: str | None = None) -> list[str] | None:
    selected_ids = sample_ids or pair_ids
    return [item.strip() for item in selected_ids.split(",") if item.strip()] if selected_ids else None


def run_import_samples_command(
    image_root: Path,
    *,
    sample_ids: str | None,
    pair_ids: str | None,
    workspace_root: Path,
    copy_images: bool,
    overwrite: bool,
) -> None:
    result = import_image_samples(
        normalize_path(image_root),
        workspace_root=normalize_path(workspace_root),
        sample_ids=parse_sample_ids(sample_ids, pair_ids),
        copy_images=copy_images,
        overwrite=overwrite,
    )
    print_json(result)


@app.command()
def doctor() -> None:
    """Show local optional dependency status."""
    modules = [
        ("OpenAI Agents SDK", "agents", agents_sdk_status()),
        ("MCP", "mcp", mcp_status()),
        ("Typer", "typer", None),
        ("Pydantic", "pydantic", None),
        ("Ultralytics YOLO", "ultralytics", None),
        ("Albumentations", "albumentations", None),
        ("FiftyOne", "fiftyone", None),
        ("Label Studio SDK", "label_studio_sdk", None),
        ("Roboflow", "roboflow", None),
        ("Hugging Face Hub", "huggingface_hub", None),
        ("MLflow", "mlflow", None),
        ("DVC", "dvc", None),
        ("lakeFS", "lakefs", None),
        ("LanceDB", "lancedb", None),
        ("DuckDB", "duckdb", None),
    ]
    table = Table(title=f"GopherEye Data Agent {__version__}")
    table.add_column("Tool")
    table.add_column("Module")
    table.add_column("Available")
    table.add_column("Note")
    for label, module, status in modules:
        available = importlib.util.find_spec(module) is not None
        note = ""
        if status and not status.get("available"):
            note = str(status.get("error") or "")
        table.add_row(label, module, "yes" if available else "no", note)
    console.print(table)


@app.command("schema")
def schema_command() -> None:
    """Print the operation plan JSON schema."""
    print_json(OperationPlan.model_json_schema())


@app.command("import-samples")
def import_samples(
    image_root: Annotated[Path, typer.Argument(help="Root containing numbered sample folders or image files, e.g. images/.")],
    sample_ids: Annotated[str | None, typer.Option(help="Comma-separated sample folder/file ids, e.g. 1,2.")] = None,
    pair_ids: Annotated[str | None, typer.Option(help="Deprecated alias for --sample-ids.", hidden=True)] = None,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root to create or update.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    copy_images: Annotated[bool, typer.Option(help="Copy images into the workspace. Default references original files.")] = False,
    overwrite: Annotated[bool, typer.Option(help="Overwrite existing manifest rows for the same sample ids.")] = True,
) -> None:
    """Import leaf image samples into the dataset manifest."""
    run_import_samples_command(
        image_root,
        sample_ids=sample_ids,
        pair_ids=pair_ids,
        workspace_root=workspace_root,
        copy_images=copy_images,
        overwrite=overwrite,
    )


@app.command("import-pairs", hidden=True, deprecated=True)
def import_pairs(
    image_root: Annotated[Path, typer.Argument(help="Root containing numbered sample folders or image files, e.g. images/.")],
    sample_ids: Annotated[str | None, typer.Option(help="Comma-separated sample folder/file ids, e.g. 1,2.")] = None,
    pair_ids: Annotated[str | None, typer.Option(help="Deprecated alias for --sample-ids.")] = None,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root to create or update.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    copy_images: Annotated[bool, typer.Option(help="Copy images into the workspace. Default references original files.")] = False,
    overwrite: Annotated[bool, typer.Option(help="Overwrite existing manifest rows for the same sample ids.")] = True,
) -> None:
    """Deprecated alias for import-samples."""
    run_import_samples_command(
        image_root,
        sample_ids=sample_ids,
        pair_ids=pair_ids,
        workspace_root=workspace_root,
        copy_images=copy_images,
        overwrite=overwrite,
    )


@app.command("auto")
def auto(
    image_root: Annotated[Path, typer.Argument(help="Root containing numbered sample folders or image files, e.g. images/.")],
    sample_ids: Annotated[str | None, typer.Option(help="Comma-separated sample folder/file ids, e.g. 1,2.")] = None,
    pair_ids: Annotated[str | None, typer.Option(help="Deprecated alias for --sample-ids.", hidden=True)] = None,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
    max_items: Annotated[int, typer.Option(help="Max manifest rows to process after import.")] = 50,
    label: Annotated[bool, typer.Option(help="Create grape disease label proposals and update manifest.")] = True,
    label_provider: Annotated[str, typer.Option(help="openai, anthropic, claude, or heuristic.")] = "openai",
    label_model: Annotated[str | None, typer.Option(help="LLM labeler model name.")] = None,
    embed: Annotated[bool, typer.Option(help="Compute image embeddings.")] = True,
    augment: Annotated[bool, typer.Option(help="Create image augmentations.")] = True,
    export_ls: Annotated[bool, typer.Option("--export-label-studio/--no-export-label-studio", help="Export Label Studio task JSON.")] = True,
    segment_backend: Annotated[str, typer.Option(help="none or yolo.")] = "none",
    yolo_model: Annotated[str, typer.Option(help="YOLO model selector: local, official, a local .pt path, or an Ultralytics model name.")] = "local",
    count_per_image: Annotated[int, typer.Option(help="Augmented variants per image.")] = 1,
) -> None:
    """Import image samples and run the lightweight Data Agent automation in one command."""
    ids = parse_sample_ids(sample_ids, pair_ids)
    workspace = normalize_path(workspace_root)
    import_result = import_image_samples(normalize_path(image_root), workspace_root=workspace, sample_ids=ids)
    operations: list[DataOperation] = []
    if segment_backend != "none":
        operations.append(
            DataOperation(
                operation_type=OperationType.SEGMENTATION,
                description="Auto segmentation.",
                params={"backend": segment_backend, "model": str(yolo_model)},
            )
        )
    if label:
        label_params = {"provider": label_provider}
        if label_model:
            label_params["model"] = label_model
        operations.append(
            DataOperation(
                operation_type=OperationType.GRAPE_DISEASE_LABELING,
                description="Auto grape disease label proposals.",
                params=label_params,
            )
        )
    if embed:
        operations.append(
            DataOperation(
                operation_type=OperationType.EMBEDDING,
                description="Auto image embeddings.",
                params={"backend": "color_histogram", "persist_vector_index": True},
            )
        )
    if augment:
        operations.append(
            DataOperation(
                operation_type=OperationType.AUGMENTATION,
                description="Auto image augmentation.",
                params={"count_per_image": count_per_image},
            )
        )
    if export_ls:
        operations.append(
            DataOperation(
                operation_type=OperationType.EXPORT_LABEL_STUDIO,
                description="Auto Label Studio export.",
            )
        )
    result = execute_plan(
        make_manual_plan(
            "Auto import and process image samples",
            selector=TargetSelector(source="dataset", max_items=max_items),  # type: ignore[arg-type]
            operations=operations,
        ),
        workspace_root=workspace,
        job_root=normalize_path(job_root),
    )
    summary = summarize_job_result(result)
    summary["import"] = import_result
    summary["manifest_csv"] = import_result.get("manifest_csv")
    summary["manifest_jsonl"] = import_result.get("manifest_jsonl")
    print_json(summary)


@app.command()
def ask(
    prompt: Annotated[str, typer.Argument(help="Natural-language request, including image path, operations, and optional platform push.")],
    planner: Annotated[str, typer.Option(help="rule, openai, or anthropic.")] = "rule",
    model: Annotated[str | None, typer.Option(help="Planner model name.")] = None,
    push_to: Annotated[str, typer.Option(help="auto, none, fiftyone, label-studio, or roboflow.")] = "auto",
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
    apply: Annotated[bool, typer.Option(help="Apply manifest modification writes when prompt includes modify actions.")] = False,
) -> None:
    """Run a full language-prompted Data Agent workflow."""
    workspace = normalize_path(workspace_root)
    plan, import_results = build_language_prompt_plan(
        prompt,
        planner=planner,
        model=model,
        workspace_root=workspace,
        push_to=push_to,
    )
    result = execute_plan(
        plan,
        apply=apply,
        workspace_root=workspace,
        job_root=normalize_path(job_root),
    )
    summary = summarize_job_result(result)
    summary["prompt"] = prompt
    summary["imports"] = import_results
    summary["plan"] = plan.model_dump()
    print_json(summary)


@app.command()
def plan(
    prompt: Annotated[str, typer.Argument(help="Natural-language data operation request.")],
    planner: Annotated[str, typer.Option(help="rule, openai, or anthropic.")] = "rule",
    model: Annotated[str | None, typer.Option(help="Planner model name.")] = None,
    out: Annotated[Path | None, typer.Option(help="Optional JSON output path.")] = None,
) -> None:
    """Create an operation plan without executing it."""
    operation_plan = make_plan(prompt, planner=planner, model=model)
    if out:
        write_json(normalize_path(out), operation_plan.model_dump())
        console.print(f"Wrote {root_relative(normalize_path(out))}")
    print_json(operation_plan.model_dump())


@app.command()
def run(
    prompt: Annotated[str, typer.Argument(help="Natural-language data operation request.")],
    planner: Annotated[str, typer.Option(help="rule, openai, or anthropic.")] = "rule",
    model: Annotated[str | None, typer.Option(help="Planner model name.")] = None,
    apply: Annotated[bool, typer.Option(help="Apply modifying operations. Default is dry-run.")] = False,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
) -> None:
    """Plan and execute a Data Agent run."""
    operation_plan = make_plan(prompt, planner=planner, model=model)
    result = execute_plan(
        operation_plan,
        apply=apply,
        workspace_root=normalize_path(workspace_root),
        job_root=normalize_path(job_root),
    )
    print_job_summary(result)


@app.command()
def apply(
    plan_path: Annotated[Path, typer.Argument(help="Path to operation_plan.json.")],
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
) -> None:
    """Apply a saved operation plan."""
    raw = read_json(normalize_path(plan_path))
    operation_plan = OperationPlan.model_validate(raw)
    result = execute_plan(
        operation_plan,
        apply=True,
        workspace_root=normalize_path(workspace_root),
        job_root=normalize_path(job_root),
    )
    print_job_summary(result)


@app.command()
def modify(
    json_pointer: Annotated[str, typer.Argument(help="JSON pointer, e.g. /corrections/group_id.")],
    value: Annotated[str, typer.Argument(help="String value to write.")],
    file: Annotated[str, typer.Option(help="manifest. Other values are accepted for backward compatibility.")] = "manifest",
    source: Annotated[str, typer.Option(help="Target source.")] = "dataset",
    max_items: Annotated[int, typer.Option(help="Max targets.")] = 50,
    apply: Annotated[bool, typer.Option(help="Apply writes. Default is dry-run.")] = False,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
) -> None:
    """Build and run a focused dataset manifest modification plan."""
    selector = TargetSelector(source=source, max_items=max_items)  # type: ignore[arg-type]
    action = JsonPatchAction(file=file, json_pointer=json_pointer, value=value, reason="CLI modify command.")  # type: ignore[arg-type]
    operation_plan = make_manual_plan(
        "CLI modify command",
        selector=selector,
        operations=[
            DataOperation(
                operation_type=OperationType.MODIFY_MANIFEST,
                description="CLI manifest modification.",
                patch_actions=[action],
            )
        ],
    )
    result = execute_plan(
        operation_plan,
        apply=apply,
        workspace_root=normalize_path(workspace_root),
        job_root=normalize_path(job_root),
    )
    print_job_summary(result)


@app.command()
def segment(
    source: Annotated[str, typer.Option(help="Target source.")] = "dataset",
    backend: Annotated[str, typer.Option(help="auto or yolo.")] = "auto",
    model: Annotated[str | None, typer.Option(help="YOLO model selector: local, official, a local .pt path, or an Ultralytics model name. Defaults to local.")] = None,
    max_items: Annotated[int, typer.Option(help="Max targets.")] = 50,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
) -> None:
    """Run segmentation on selected targets."""
    params = {"backend": backend}
    if model:
        params["model"] = model
    result = execute_plan(
        make_manual_plan(
            "CLI segmentation command",
            selector=TargetSelector(source=source, max_items=max_items),  # type: ignore[arg-type]
            operations=[
                DataOperation(
                    operation_type=OperationType.SEGMENTATION,
                    description="CLI segmentation.",
                    params=params,
                )
            ],
        ),
        workspace_root=normalize_path(workspace_root),
        job_root=normalize_path(job_root),
    )
    print_job_summary(result)


@app.command()
def label(
    source: Annotated[str, typer.Option(help="Target source.")] = "dataset",
    provider: Annotated[str, typer.Option(help="openai, anthropic, claude, or heuristic.")] = "openai",
    model: Annotated[str | None, typer.Option(help="LLM labeler model name.")] = None,
    max_items: Annotated[int, typer.Option(help="Max targets.")] = 50,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
) -> None:
    """Create grape disease label proposals."""
    result = execute_plan(
        make_manual_plan(
            "CLI grape disease labeling command",
            selector=TargetSelector(source=source, max_items=max_items),  # type: ignore[arg-type]
            operations=[
                DataOperation(
                    operation_type=OperationType.GRAPE_DISEASE_LABELING,
                    description="CLI grape disease label proposals.",
                    params={"provider": provider, **({"model": model} if model else {})},
                )
            ],
        ),
        workspace_root=normalize_path(workspace_root),
        job_root=normalize_path(job_root),
    )
    print_job_summary(result)


@app.command()
def embed(
    source: Annotated[str, typer.Option(help="Target source.")] = "dataset",
    max_items: Annotated[int, typer.Option(help="Max targets.")] = 50,
    persist_vector_index: Annotated[bool, typer.Option(help="Try to persist vectors to LanceDB.")] = False,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
) -> None:
    """Compute image embeddings."""
    result = execute_plan(
        make_manual_plan(
            "CLI embedding command",
            selector=TargetSelector(source=source, max_items=max_items),  # type: ignore[arg-type]
            operations=[
                DataOperation(
                    operation_type=OperationType.EMBEDDING,
                    description="CLI image embeddings.",
                    params={"backend": "color_histogram", "persist_vector_index": persist_vector_index},
                )
            ],
        ),
        workspace_root=normalize_path(workspace_root),
        job_root=normalize_path(job_root),
    )
    print_job_summary(result)


@app.command()
def augment(
    source: Annotated[str, typer.Option(help="Target source.")] = "dataset",
    max_items: Annotated[int, typer.Option(help="Max targets.")] = 50,
    count_per_image: Annotated[int, typer.Option(help="Augmented variants per image.")] = 3,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
) -> None:
    """Create augmented image derivatives."""
    result = execute_plan(
        make_manual_plan(
            "CLI augmentation command",
            selector=TargetSelector(source=source, max_items=max_items),  # type: ignore[arg-type]
            operations=[
                DataOperation(
                    operation_type=OperationType.AUGMENTATION,
                    description="CLI image augmentation.",
                    params={"count_per_image": count_per_image},
                )
            ],
        ),
        workspace_root=normalize_path(workspace_root),
        job_root=normalize_path(job_root),
    )
    print_job_summary(result)


@app.command("export-label-studio")
def export_label_studio(
    source: Annotated[str, typer.Option(help="Target source.")] = "dataset",
    max_items: Annotated[int, typer.Option(help="Max targets.")] = 50,
    workspace_root: Annotated[Path, typer.Option(help="GopherEye Data Agent workspace root.")] = CLI_DEFAULT_WORKSPACE_ROOT,
    job_root: Annotated[Path, typer.Option(help="Data Agent run root.")] = CLI_DEFAULT_JOB_ROOT,
) -> None:
    """Export selected targets as Label Studio task JSON."""
    result = execute_plan(
        make_manual_plan(
            "CLI Label Studio export command",
            selector=TargetSelector(source=source, max_items=max_items),  # type: ignore[arg-type]
            operations=[
                DataOperation(
                    operation_type=OperationType.EXPORT_LABEL_STUDIO,
                    description="CLI Label Studio export.",
                )
            ],
        ),
        workspace_root=normalize_path(workspace_root),
        job_root=normalize_path(job_root),
    )
    print_job_summary(result)


@app.command("mcp-server")
def mcp_server() -> None:
    """Expose Data Agent planning tools over MCP when mcp is installed."""
    run_mcp_server()


def make_manual_plan(prompt: str, *, selector: TargetSelector, operations: list[DataOperation]) -> OperationPlan:
    from src.gophereye_runtime.utils import now_utc, stable_id

    return OperationPlan(
        plan_id=stable_id("plan", prompt, now_utc()),
        user_prompt=prompt,
        created_at=now_utc(),
        planner="manual",
        target_selector=selector,
        operations=operations,
    )
