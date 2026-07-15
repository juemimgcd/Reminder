from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.mneme.agent.capabilities import CapabilityMetadata
from app.mneme.agent.contracts import AnswerMode
from app.mneme.agent.actions import ToolApprovalPolicy, ToolRiskLevel


class ToolErrorKind(str, Enum):
    RETRYABLE = "retryable"
    BUSINESS = "business"
    UNAVAILABLE = "unavailable"
    ABORTED = "aborted"
    APPROVAL_REQUIRED = "approval_required"


class ToolScope(str, Enum):
    TRUSTED_REQUEST = "trusted_request"


class ToolMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    capability_id: str
    answer_modes: frozenset[AnswerMode]
    evidence_type: str
    requires_knowledge_base: bool = True
    can_answer_directly: bool = False
    read_only: bool = True
    risk_level: ToolRiskLevel = ToolRiskLevel.READ
    approval_policy: ToolApprovalPolicy = ToolApprovalPolicy.NEVER
    must_produce_evidence: bool = True
    scope: ToolScope = ToolScope.TRUSTED_REQUEST
    timeout_seconds: float = 60.0

    def capability_metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            capability_id=self.capability_id,
            tool_name=self.name,
            answer_modes=self.answer_modes,
            evidence_type=self.evidence_type,
            requires_knowledge_base=self.requires_knowledge_base,
            can_answer_directly=self.can_answer_directly,
        )

    def openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The question to answer within the server-provided trusted scope.",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        }
