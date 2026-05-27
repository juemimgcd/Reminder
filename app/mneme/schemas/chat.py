from typing import Literal

from pydantic import BaseModel, Field


QueryType = Literal[
    "general_chat",
    "kb_qa",
    "memory_query",
    "profile_query",
    "analysis_query",
    "action_request",
]


class QueryRouteDecision(BaseModel):
    query_type: QueryType = Field(..., description="Router-selected query type")
    requires_retrieval: bool = Field(..., description="Whether the query should enter retrieval")
    target_pipeline: str = Field(..., description="Selected downstream pipeline")
    confidence: str = Field(..., description="high / medium / low")
    reason: str = Field(..., description="Short explanation for the routing decision")


class ChatQueryRequest(BaseModel):
    question: str = Field(..., description="User question")
    knowledge_base_id: str = Field(..., description="Knowledge base ID")
    top_k: int = Field(default=4, ge=1, le=10, description="Recall size")
    session_id: str | None = Field(default=None, description="Optional session ID")


class ChatSourceItem(BaseModel):
    source_id: str
    knowledge_base_id: str | None = None
    document_id: str
    chunk_id: str
    page_no: int | None = None
    text: str


class ChatCitationItem(BaseModel):
    source_id: str = Field(..., description="Stable source ID, for example S1")
    document_id: str = Field(..., description="Source document ID")
    chunk_id: str = Field(..., description="Source chunk ID")
    page_no: int | None = Field(default=None, description="Source page number")
    quote: str = Field(..., description="Quoted evidence text")
    reason: str = Field(..., description="Why this evidence supports the answer")
    validation_status: str | None = Field(default=None, description="valid / invalid")
    quote_found: bool | None = Field(default=None, description="Whether quote exists in source text")
    validation_reason: str | None = Field(default=None, description="Citation validation detail")


class RetrievalDebugData(BaseModel):
    route: dict | None = None
    query_terms: list[str] = Field(default_factory=list)
    lexical_backend: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    vector_candidates: list[dict] = Field(default_factory=list)
    lexical_candidates: list[dict] = Field(default_factory=list)
    memory_candidates: list[dict] = Field(default_factory=list)
    fused_candidates: list[dict] = Field(default_factory=list)
    final_context: list[dict] = Field(default_factory=list)
    answer_debug: dict | None = None


class ChatQueryData(BaseModel):
    answer: str
    sources: list[ChatSourceItem]
    citations: list[ChatCitationItem]
    confidence: str
    uncertainty: str | None = None
    route: QueryRouteDecision | None = None
    debug: RetrievalDebugData | None = None


class EvidenceCitationDraft(BaseModel):
    source_id: str = Field(..., description="Model-selected source ID")
    quote: str = Field(..., description="Model-selected evidence text")
    reason: str = Field(..., description="Reason for the citation")


class EvidenceAnswerDraft(BaseModel):
    answer: str = Field(..., description="Final evidence-grounded answer")
    citations: list[EvidenceCitationDraft] = Field(default_factory=list)
    confidence: str = Field(..., description="high / medium / low")
    uncertainty: str | None = Field(default=None, description="Remaining uncertainty")


class ContextItem(BaseModel):
    recall_type: str = Field(..., description="vector / keyword / memory")
    score: float = Field(..., description="Normalized recall score")
    vector_score: float | None = Field(default=None)
    keyword_score: float | None = Field(default=None)
    memory_score: float | None = Field(default=None)
    fusion_score: float | None = Field(default=None)
    rerank_score: float | None = Field(default=None)
    exact_match_count: int = Field(default=0)
    recall_ranks: dict[str, int] = Field(default_factory=dict)
    rerank_reasons: list[str] = Field(default_factory=list)
    knowledge_base_id: str | None = Field(default=None)
    document_id: str = Field(...)
    chunk_id: str = Field(...)
    page_no: int | None = Field(default=None)
    text: str = Field(...)
    source_chunk_ids: list[str] = Field(default_factory=list)
    source_page_nos: list[int] = Field(default_factory=list)
    merged_chunk_count: int = Field(default=1)
    memory_entry_id: str | None = Field(default=None)
    entry_name: str | None = Field(default=None)
    matched_terms: list[str] = Field(default_factory=list)
    section_id: str | None = Field(default=None, description="Owning section ID")
    section_title: str | None = Field(default=None, description="Current section title")
    section_level: int | None = Field(default=None, description="Markdown heading level")
    section_path: str | None = Field(default=None, description="Resolved section path")
    section_summary: str | None = Field(default=None, description="Section summary")
    section_chunk_index: int | None = Field(default=None, description="Chunk index inside the section")
