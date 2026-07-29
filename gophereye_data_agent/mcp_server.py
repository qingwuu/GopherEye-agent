from __future__ import annotations

from typing import Any

from .planner import make_plan


def mcp_status() -> dict[str, Any]:
    try:
        __import__("mcp")
    except Exception as exc:
        return {"available": False, "error": str(exc)}
    return {"available": True}


def run_mcp_server() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:
        raise RuntimeError("mcp is not installed. Install mcp to expose Data Agent tools over MCP.") from exc

    mcp = FastMCP("gophereye-data-agent")

    @mcp.tool()
    def create_operation_plan(user_prompt: str) -> dict[str, Any]:
        """Create a strict GopherEye Data Agent operation plan."""
        return make_plan(user_prompt, planner="rule").model_dump()

    @mcp.resource("gophereye-data-agent://schema/operation-plan")
    def operation_plan_schema() -> dict[str, Any]:
        from .schemas import OperationPlan

        return OperationPlan.model_json_schema()

    mcp.run()
