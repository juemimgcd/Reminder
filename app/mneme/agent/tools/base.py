from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.mneme.agent.contracts import AnswerMode


class ToolErrorKind(str, Enum):
    RETRYABLE = "retryable"
    BUSINESS = "business"
    UNAVAILABLE = "unavailable"
    ABORTED = "aborted"


class ToolScope(str, Enum):
    TRUSTED_REQUEST = "trusted_request"


class ToolMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    answer_mode: AnswerMode
    requires_knowledge_base: bool = True
    read_only: bool = True
    must_produce_evidence: bool = True
    scope: ToolScope = ToolScope.TRUSTED_REQUEST
    timeout_seconds: float = 60.0

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
