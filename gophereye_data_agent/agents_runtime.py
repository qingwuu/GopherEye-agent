from __future__ import annotations

from typing import Any

from .planner import make_plan


def agents_sdk_status() -> dict[str, Any]:
    try:
        __import__("agents")
    except Exception as exc:
        return {"available": False, "error": str(exc)}
    return {"available": True}


def build_agents_sdk_manager() -> Any:
    try:
        from agents import Agent, function_tool
    except Exception as exc:
        raise RuntimeError("openai-agents is not installed. Install openai-agents to use this adapter.") from exc

    @function_tool
    def create_operation_plan(user_prompt: str) -> dict[str, Any]:
        """Create a GopherEye Data Agent operation plan from a user prompt."""
        return make_plan(user_prompt, planner="rule").model_dump()

    return Agent(
        name="GopherEye Data Agent Manager",
        instructions=(
            "Coordinate data operations by creating operation plans. "
            "Do not write files directly; use tools and the local executor."
        ),
        tools=[create_operation_plan],
    )
