from typing import Literal

from pydantic import BaseModel, Field, SecretStr

AnswerMode = Literal[
    "kb_qa",
    "memory_query",
    "profile_query",
    "analysis_query",
    "general_chat",
]


class ModelInvocationConfig(BaseModel):
    provider: str
    base_url: str
    model_name: str
    api_key: SecretStr = Field(exclude=True)
    temperature: float = 0.0
