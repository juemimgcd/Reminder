"""Track an ephemeral retrieval plan and evidence coverage for one answer run.

The model proposes requirements and judges relevance. The runtime validates the
references and preserves unresolved requirements; this is not proof of entailment.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1, le=8)
    question: str = Field(min_length=1, max_length=300)
    status: Literal["supported", "missing", "conflicting"]
    evidence_ids: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_support(self) -> "EvidenceRequirement":
        if not self.question.strip():
            raise ValueError("requirement question cannot be blank")
        if self.status == "supported" and not self.evidence_ids:
            raise ValueError("supported requirements need evidence references")
        return self


class RetrievalAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements: list[EvidenceRequirement] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_ids(self) -> "RetrievalAssessment":
        if len({item.id for item in self.requirements}) != len(self.requirements):
            raise ValueError("requirement IDs must be unique")
        return self

    def reconcile(
        self,
        previous: "RetrievalAssessment | None",
        *,
        visible_evidence_ids: set[str],
    ) -> "RetrievalAssessment":
        """Do not let a later step silently discard an unanswered subquestion."""
        merged = {item.id: item for item in previous.requirements} if previous else {}
        for item in self.requirements:
            if not set(item.evidence_ids) <= visible_evidence_ids:
                raise ValueError("assessment references evidence outside the current context")
            old = merged.get(item.id)
            if old is not None and old.question != item.question:
                raise ValueError("requirement IDs must retain their original questions")
            merged[item.id] = item
        # Previously supported requirements must still have visible support.
        requirements = []
        for item in merged.values():
            if not set(item.evidence_ids) <= visible_evidence_ids:
                item = item.model_copy(update={"status": "missing", "evidence_ids": []})
            requirements.append(item)
        return RetrievalAssessment(requirements=sorted(requirements, key=lambda item: item.id))

    @property
    def sufficient(self) -> bool:
        return all(item.status == "supported" for item in self.requirements)

    @property
    def missing_count(self) -> int:
        return sum(item.status != "supported" for item in self.requirements)

    def covered_by(self, cited_ids: set[str]) -> bool:
        return self.sufficient and all(
            cited_ids.intersection(item.evidence_ids) for item in self.requirements
        )
