from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.mneme.agent.contracts import AnswerMode


class CapabilityMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability_id: str
    tool_name: str
    answer_modes: frozenset[AnswerMode]
    evidence_type: str
    requires_knowledge_base: bool = True
    can_answer_directly: bool = False


class CapabilityExclusion(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability_id: str
    reason: str


class CapabilityProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent: AnswerMode
    eligible_capability_ids: list[str] = Field(default_factory=list)
    selected_capability_ids: list[str] = Field(default_factory=list)
    selected_tool_names: list[str] = Field(default_factory=list)
    excluded_capabilities: list[CapabilityExclusion] = Field(default_factory=list)
    exclusion_reason: str | None = None
    requires_tool: bool = False

    def trace_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class CapabilityIndex:
    def __init__(self, capabilities: Iterable[CapabilityMetadata]):
        self._capabilities = tuple(capabilities)

    def project(
        self,
        *,
        answer_mode: AnswerMode,
        has_knowledge_base: bool,
    ) -> CapabilityProjection:
        eligible: list[CapabilityMetadata] = []
        excluded: list[CapabilityExclusion] = []

        for capability in self._capabilities:
            reason = self._exclusion_reason(
                capability,
                answer_mode=answer_mode,
                has_knowledge_base=has_knowledge_base,
            )
            if reason:
                excluded.append(
                    CapabilityExclusion(
                        capability_id=capability.capability_id,
                        reason=reason,
                    )
                )
            else:
                eligible.append(capability)

        requires_tool = answer_mode != "general_chat"
        exclusion_reason = None
        if not eligible:
            exclusion_reason = (
                "intent_allows_direct_answer"
                if not requires_tool
                else "no_eligible_capability"
            )

        return CapabilityProjection(
            intent=answer_mode,
            eligible_capability_ids=[item.capability_id for item in eligible],
            selected_capability_ids=[item.capability_id for item in eligible],
            selected_tool_names=[item.tool_name for item in eligible],
            excluded_capabilities=excluded,
            exclusion_reason=exclusion_reason,
            requires_tool=requires_tool,
        )

    @staticmethod
    def _exclusion_reason(
        capability: CapabilityMetadata,
        *,
        answer_mode: AnswerMode,
        has_knowledge_base: bool,
    ) -> str | None:
        if answer_mode not in capability.answer_modes:
            return "intent_mismatch"
        if capability.requires_knowledge_base and not has_knowledge_base:
            return "knowledge_base_required"
        return None
