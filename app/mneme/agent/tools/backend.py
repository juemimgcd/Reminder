import asyncio
from typing import Any

from app.mneme.agent.capabilities import CapabilityProjection
from app.mneme.agent.orchestrator import is_retryable_external_error
from app.mneme.agent.runtime_context import AgentRunContext
from app.mneme.agent.tools.base import ToolErrorKind
from app.mneme.agent.tools.contracts import BackendToolResult
from app.mneme.agent.tools.policy import evaluate_tool_call
from app.mneme.agent.tools.primitives import analyze_growth, get_profile, search_knowledge_base, search_memory
from app.mneme.agent.tools.registry import TOOL_CATALOG, get_tool_metadata
from app.mneme.utils.exceptions import BusinessException

TOOL_EXECUTORS = {
    "kb_search": search_knowledge_base,
    "memory_search": search_memory,
    "profile_get": get_profile,
    "growth_analysis": analyze_growth,
}


def get_backend_tool_schemas(projection: CapabilityProjection) -> list[dict[str, Any]]:
    return [
        TOOL_CATALOG[tool_name].openai_schema()
        for tool_name in projection.selected_tool_names
        if tool_name in TOOL_CATALOG
    ]


async def execute_backend_tool(
    *,
    projection: CapabilityProjection,
    tool_name: str,
    arguments: dict[str, Any],
    fallback_question: str,
    top_k: int,
    context: AgentRunContext,
) -> BackendToolResult:
    metadata = get_tool_metadata(tool_name)
    if metadata is None:
        return BackendToolResult.error(
            tool_name=tool_name,
            kind=ToolErrorKind.UNAVAILABLE,
            message=f"Backend capability is unavailable: {tool_name}",
        )
    decision = evaluate_tool_call(projection=projection, tool_name=tool_name)
    if not decision.allowed:
        return BackendToolResult.error(
            tool_name=tool_name,
            kind=ToolErrorKind.UNAVAILABLE,
            message=decision.reason,
        )
    if decision.approval_required:
        return BackendToolResult.error(
            tool_name=tool_name,
            kind=ToolErrorKind.APPROVAL_REQUIRED,
            message=f"Write capability requires an approved proposal before execution: {tool_name}",
        )
    if context.is_aborted():
        return BackendToolResult.error(
            tool_name=tool_name,
            kind=ToolErrorKind.ABORTED,
            message="Agent run was aborted before backend tool execution.",
        )

    query = str(arguments.get("query") or fallback_question).strip() or fallback_question
    executor = TOOL_EXECUTORS[tool_name]
    try:
        async with asyncio.timeout(metadata.timeout_seconds):
            return await executor(
                query=query,
                top_k=top_k,
                context=context,
            )
    except BusinessException as exc:
        return BackendToolResult.error(
            tool_name=tool_name,
            kind=ToolErrorKind.BUSINESS,
            message=exc.message,
        )
    except TimeoutError:
        return BackendToolResult.error(
            tool_name=tool_name,
            kind=ToolErrorKind.RETRYABLE,
            message=f"Backend capability timed out: {tool_name}",
        )
    except Exception as exc:
        kind = ToolErrorKind.RETRYABLE if is_retryable_external_error(exc) else ToolErrorKind.UNAVAILABLE
        return BackendToolResult.error(
            tool_name=tool_name,
            kind=kind,
            message=f"Backend capability failed: {tool_name}",
        )
