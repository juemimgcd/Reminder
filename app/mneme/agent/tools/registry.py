from app.mneme.agent.capabilities import CapabilityIndex, CapabilityProjection
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

CAPABILITY_INDEX = CapabilityIndex(
    item.capability_metadata() for item in TOOL_CATALOG.values()
)


def get_tool_metadata(tool_name: str) -> ToolMetadata | None:
    return TOOL_CATALOG.get(tool_name)


def project_capabilities(
    *,
    answer_mode: AnswerMode,
    knowledge_base_id: str | None,
) -> CapabilityProjection:
    return CAPABILITY_INDEX.project(
        answer_mode=answer_mode,
        has_knowledge_base=bool(knowledge_base_id),
    )
