from app.mneme.agent.tools.base import ToolMetadata

MEMORY_SEARCH_METADATA = ToolMetadata(
    name="memory_search",
    description="Answer a question using memory evidence from the current private knowledge base.",
    capability_id="tool:memory_search",
    answer_modes=frozenset({"memory_query"}),
    evidence_type="memory_records",
)
