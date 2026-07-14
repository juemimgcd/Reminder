from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel


class RetrievalScope(BaseModel):
    owner_id: int
    knowledge_base_id: str


class RetrievedEvidence(BaseModel):
    evidence_id: str
    source_type: Literal["document", "memory"]
    source_id: str
    content: str
    score: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DocumentSearchHit:
    chunk_id: str
    document_id: str
    content: str
    metadata: dict[str, Any]
