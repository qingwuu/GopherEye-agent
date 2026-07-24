from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from Frontier_model.frontier_agents.config import load_model_config
    from Frontier_model.frontier_agents.pipeline import FRONTIER_DIR, run_frontier_turn
else:
    from .frontier_agents.config import load_model_config
    from .frontier_agents.pipeline import FRONTIER_DIR, run_frontier_turn


DEFAULT_CASES_PATH = FRONTIER_DIR / "examples" / "eval_cases.example.jsonl"
DEFAULT_RUNS_DIR = FRONTIER_DIR / "runs"


def safe_print(text: str) -> None:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    else:
        print(text)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_no}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"JSONL row must be an object at {path}:{line_no}")
        rows.append(item)
    return rows


def run_benchmark(
    *,
    cases_path: Path,
    profiles: Iterable[str],
    config_path: str | None,
    selection_mode: str,
    output_dir: Path,
    max_output_tokens: int,
) -> Dict[str, Any]:
    config = load_model_config(config_path)
    cases = read_jsonl(cases_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("frontier_benchmark_%Y%m%d_%H%M%S", time.gmtime())
    profile_names = list(profiles) or [config.default_profile]
    results = []

    for case in cases:
        case_id = str(case.get("case_id") or f"case_{len(results) + 1}")
        message = str(case["message"])
        image_refs = case.get("image_refs") or []
        if not isinstance(image_refs, list):
            raise ValueError(f"case {case_id}: image_refs must be a list")
        for profile_name in profile_names:
            started = time.perf_counter()
            session_id = f"{run_id}_{case_id}_{profile_name}"
            try:
                result = run_frontier_turn(
                    message,
                    session_id=session_id,
                    profile_name=profile_name,
                    config_path=config_path,
                    selection_mode=selection_mode,
                    image_refs=[str(ref) for ref in image_refs],
                    image_context="current",
                    max_output_tokens=max_output_tokens,
                )
                error = None
            except Exception as exc:
                result = None
                error = str(exc)
            elapsed = round(time.perf_counter() - started, 3)
            results.append(
                {
                    "case_id": case_id,
                    "profile": profile_name,
                    "elapsed_seconds": elapsed,
                    "error": error,
                    "parsed_json": bool(result and result.get("parsed_json")),
                    "envelope_valid": bool(result and result.get("envelope_valid")),
                    "envelope_schema": result.get("envelope_schema") if result else None,
                    "envelope_fallback_used": bool(result and result.get("envelope_fallback_used")),
                    "envelope_validation_errors": result.get("envelope_validation_errors") if result else None,
                    "assistant_message": result.get("assistant_message") if result else None,
                    "route": result.get("route") if result else None,
                    "context_label": result.get("context_label") if result else None,
                    "memory": result.get("short_term_memory") if result else None,
                    "selected_pages": result.get("selected_pages") if result else None,
                    "usage": result.get("usage") if result else None,
                }
            )

    summary = {
        "run_id": run_id,
        "cases_path": str(cases_path),
        "profiles": profile_names,
        "num_cases": len(cases),
        "num_results": len(results),
        "num_errors": sum(1 for item in results if item["error"]),
        "num_parsed_json": sum(1 for item in results if item["parsed_json"]),
        "results": results,
    }
    out_path = output_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["output_path"] = str(out_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare frontier model profiles on shared GopherEye cases.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--profile", action="append", default=[], help="Profile to run. Repeat for multiple profiles.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--selection-mode", choices=["keyword", "model", "full", "none"], default="keyword")
    parser.add_argument("--output-dir", default=str(DEFAULT_RUNS_DIR))
    parser.add_argument("--max-output-tokens", type=int, default=900)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = run_benchmark(
        cases_path=Path(args.cases),
        profiles=args.profile,
        config_path=args.config,
        selection_mode=args.selection_mode,
        output_dir=Path(args.output_dir),
        max_output_tokens=args.max_output_tokens,
    )
    if args.json:
        safe_print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    safe_print(f"run_id: {summary['run_id']}")
    safe_print(f"output_path: {summary['output_path']}")
    safe_print(f"results: {summary['num_results']}")
    safe_print(f"errors: {summary['num_errors']}")
    safe_print(f"parsed_json: {summary['num_parsed_json']}")


if __name__ == "__main__":
    main()
