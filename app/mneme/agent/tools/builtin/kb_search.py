from app.mneme.agent.tools.base import ToolMetadata

KB_SEARCH_METADATA = ToolMetadata(
    name="kb_search",
    description="Answer a question using evidence retrieved from the current private knowledge base.",
    answer_mode="kb_qa",
)
