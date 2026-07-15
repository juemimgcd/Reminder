from dataclasses import dataclass

from app.mneme.agent.capabilities import CapabilityProjection
from app.mneme.agent.tools.base import ToolMetadata
from app.mneme.agent.tools.registry import get_tool_metadata


@dataclass(frozen=True)
class ToolPolicyDecision:
    allowed: bool
    required: bool
    reason: str
    metadata: ToolMetadata | None = None


def evaluate_tool_call(
    *,
    projection: CapabilityProjection,
    tool_name: str,
) -> ToolPolicyDecision:
    candidate = get_tool_metadata(tool_name)
    if candidate is None:
        return ToolPolicyDecision(
            False,
            projection.requires_tool,
            f"unknown backend tool: {tool_name}",
        )
    if candidate.capability_id not in projection.selected_capability_ids:
        return ToolPolicyDecision(
            False,
            projection.requires_tool,
            f"tool {tool_name} is outside the projected capability set",
            candidate,
        )
    return ToolPolicyDecision(
        True,
        projection.requires_tool,
        "tool belongs to the projected capability set",
        candidate,
    )
