from app.mneme.agent.tools.base import ToolMetadata

KB_SEARCH_METADATA = ToolMetadata(
    name="kb_search",
    description="Answer a question using evidence retrieved from the current private knowledge base.",
    capability_id="tool:kb_search",
    answer_modes=frozenset({"kb_qa"}),
    evidence_type="document_chunks",
)
