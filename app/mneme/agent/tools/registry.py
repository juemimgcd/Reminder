from app.mneme.agent.contracts import AnswerMode
from app.mneme.agent.tools.base import ToolMetadata
from app.mneme.agent.tools.builtin import (
    GROWTH_ANALYSIS_METADATA,
    KB_SEARCH_METADATA,
    MEMORY_SEARCH_METADATA,
    PROFILE_GET_METADATA,
)

TOOL_CATALOG: dict[str, ToolMetadata] = {
    item.name: item
    for item in (
        KB_SEARCH_METADATA,
        MEMORY_SEARCH_METADATA,
        PROFILE_GET_METADATA,
        GROWTH_ANALYSIS_METADATA,
    )
}

ANSWER_MODE_TOOL_NAMES: dict[AnswerMode, str | None] = {
    "kb_qa": KB_SEARCH_METADATA.name,
    "memory_query": MEMORY_SEARCH_METADATA.name,
    "profile_query": PROFILE_GET_METADATA.name,
    "analysis_query": GROWTH_ANALYSIS_METADATA.name,
    "general_chat": None,
}


def get_tool_metadata(tool_name: str) -> ToolMetadata | None:
    return TOOL_CATALOG.get(tool_name)


def get_tool_for_answer_mode(answer_mode: AnswerMode) -> ToolMetadata | None:
    tool_name = ANSWER_MODE_TOOL_NAMES[answer_mode]
    return TOOL_CATALOG.get(tool_name) if tool_name else None
