from app.mneme.agent.tools.base import ToolMetadata

MEMORY_SEARCH_METADATA = ToolMetadata(
    name="memory_search",
    description="Answer a question using memory evidence from the current private knowledge base.",
    answer_mode="memory_query",
)
