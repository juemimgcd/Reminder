from dataclasses import dataclass

from app.mneme.agent.contracts import AnswerMode
from app.mneme.agent.tools.base import ToolMetadata
from app.mneme.agent.tools.registry import get_tool_for_answer_mode, get_tool_metadata


@dataclass(frozen=True)
class ToolPolicyDecision:
    allowed: bool
    required: bool
    reason: str
    metadata: ToolMetadata | None = None


def evaluate_tool_call(*, answer_mode: AnswerMode, tool_name: str) -> ToolPolicyDecision:
    expected = get_tool_for_answer_mode(answer_mode)
    candidate = get_tool_metadata(tool_name)
    if expected is None:
        return ToolPolicyDecision(False, False, "general chat does not expose backend tools")
    if candidate is None:
        return ToolPolicyDecision(False, True, f"unknown backend tool: {tool_name}", expected)
    if candidate.name != expected.name:
        return ToolPolicyDecision(False, True, f"tool {tool_name} is not eligible for {answer_mode}", expected)
    return ToolPolicyDecision(True, True, "tool matches the user-selected capability", candidate)
