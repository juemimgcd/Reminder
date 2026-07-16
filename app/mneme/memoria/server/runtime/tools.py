from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.mneme.memoria.actions import WRITE_ACTION_CATALOG
from app.mneme.memoria.server.retrieval.contracts import RetrievedEvidence
from app.mneme.memoria.server.runtime.contracts import (
    RetrievalPlan,
    RetrievalRequest,
    ToolExecutionContext,
)
from app.mneme.memoria.server.runtime.ports import EvidenceRetriever

ToolStatus = Literal["completed", "approval_required", "rejected", "failed", "budget_exceeded"]


class ToolRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    risk_level: str
    source_type: str | None = None


@dataclass(frozen=True)
class ToolExecution:
    trace: dict[str, Any]
    observation: dict[str, Any]
    evidence: tuple[RetrievedEvidence, ...] = ()


READ_TOOL_DEFINITIONS: dict[str, ToolDefinition] = {
    item.name: item
    for item in (
        ToolDefinition(
            name="search_documents",
            description="Search documents in the current owner and knowledge-base scope.",
            risk_level="read",
            source_type="document",
        ),
        ToolDefinition(
            name="search_memories",
            description="Search governed memory in the current owner scope.",
            risk_level="read",
            source_type="memory",
        ),
        ToolDefinition(
            name="search_profile",
            description="Search governed profile evidence in the current owner scope.",
            risk_level="read",
            source_type="profile",
        ),
        ToolDefinition(
            name="search_relations",
            description="Search governed relation evidence in the current owner scope.",
            risk_level="read",
            source_type="relation",
        ),
    )
}


def available_tool_specs(context: ToolExecutionContext) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for definition in READ_TOOL_DEFINITIONS.values():
        if _source_allowed(context.plan, definition.source_type or ""):
            specs.append(
                {
                    "name": definition.name,
                    "risk_level": definition.risk_level,
                    "description": definition.description,
                    "arguments": {"query": "non-empty string", "top_k": "optional integer 1..10"},
                }
            )
    if context.allow_action_proposals:
        for definition in WRITE_ACTION_CATALOG.values():
            specs.append(
                {
                    "name": definition.name,
                    "risk_level": definition.risk_level.value,
                    "description": definition.description,
                    "arguments": {
                        "summary": "non-empty user-visible proposal summary",
                        "arguments": "bounded JSON object for later review",
                    },
                }
            )
    return specs


class ScopedToolExecutor:
    def __init__(self, retriever: EvidenceRetriever) -> None:
        self._retriever = retriever

    async def execute(
        self,
        request: ToolRequest,
        *,
        context: ToolExecutionContext,
        tool_call_id: str,
    ) -> ToolExecution:
        if request.name in WRITE_ACTION_CATALOG:
            if not context.allow_action_proposals:
                definition = WRITE_ACTION_CATALOG[request.name]
                return _terminal_execution(
                    tool_call_id=tool_call_id,
                    name=request.name,
                    risk_level=definition.risk_level.value,
                    status="rejected",
                    message="action proposals require a durable chat session",
                )
            return _action_proposal(request, tool_call_id=tool_call_id)
        definition = READ_TOOL_DEFINITIONS.get(request.name)
        if definition is None:
            return _terminal_execution(
                tool_call_id=tool_call_id,
                name=request.name,
                risk_level="unknown",
                status="rejected",
                message="unknown tool",
            )
        if not _source_allowed(context.plan, definition.source_type or ""):
            return _terminal_execution(
                tool_call_id=tool_call_id,
                name=request.name,
                risk_level=definition.risk_level,
                status="rejected",
                message="tool is outside the selected answer-mode scope",
            )
        query = request.arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return _terminal_execution(
                tool_call_id=tool_call_id,
                name=request.name,
                risk_level=definition.risk_level,
                status="rejected",
                message="query is required",
            )
        query = query.strip()[:8000]
        requested_top_k = request.arguments.get("top_k", context.top_k)
        if isinstance(requested_top_k, bool) or not isinstance(requested_top_k, int):
            requested_top_k = context.top_k
        top_k = max(1, min(requested_top_k, context.top_k, 10))
        plan = _single_source_plan(definition.source_type or "")
        try:
            evidence = await self._retriever.retrieve(
                RetrievalRequest(
                    request_id=context.request_id,
                    owner_id=context.owner_id,
                    knowledge_base_id=context.knowledge_base_id,
                    mode=context.mode,
                    question=query,
                    top_k=top_k,
                    plan=plan,
                )
            )
        except Exception:
            return _terminal_execution(
                tool_call_id=tool_call_id,
                name=request.name,
                risk_level=definition.risk_level,
                status="failed",
                message="tool dependency failed",
            )
        bounded = tuple(evidence[:top_k])
        trace = {
            "tool_call_id": tool_call_id,
            "name": request.name,
            "risk_level": definition.risk_level,
            "status": "completed",
            "result_count": len(bounded),
        }
        return ToolExecution(
            trace=trace,
            observation={**trace, "message": "scoped evidence search completed"},
            evidence=bounded,
        )


def budget_exceeded_execution(request: ToolRequest, *, tool_call_id: str) -> ToolExecution:
    risk_level = (
        WRITE_ACTION_CATALOG[request.name].risk_level.value
        if request.name in WRITE_ACTION_CATALOG
        else READ_TOOL_DEFINITIONS.get(
            request.name,
            ToolDefinition(request.name, "", "unknown"),
        ).risk_level
    )
    return _terminal_execution(
        tool_call_id=tool_call_id,
        name=request.name,
        risk_level=risk_level,
        status="budget_exceeded",
        message="tool-call budget exhausted",
    )


def bounded_observations(observations: list[dict[str, Any]], *, max_chars: int) -> str:
    encoded = json.dumps(observations, ensure_ascii=False, separators=(",", ":"))
    return encoded[: max(0, max_chars)]


def _action_proposal(request: ToolRequest, *, tool_call_id: str) -> ToolExecution:
    definition = WRITE_ACTION_CATALOG[request.name]
    summary = request.arguments.get("summary")
    arguments = request.arguments.get("arguments", {})
    if not isinstance(summary, str) or not summary.strip() or not isinstance(arguments, dict):
        return _terminal_execution(
            tool_call_id=tool_call_id,
            name=request.name,
            risk_level=definition.risk_level.value,
            status="rejected",
            message="proposal summary and arguments object are required",
        )
    summary = " ".join(summary.split())[:2000]
    try:
        encoded_arguments = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        encoded_arguments = ""
    if not encoded_arguments or len(encoded_arguments) > 8000:
        return _terminal_execution(
            tool_call_id=tool_call_id,
            name=request.name,
            risk_level=definition.risk_level.value,
            status="rejected",
            message="proposal arguments are invalid or too large",
        )
    trace = {
        "tool_call_id": tool_call_id,
        "name": request.name,
        "risk_level": definition.risk_level.value,
        "status": "approval_required",
        "summary": summary,
        "arguments": arguments,
        "apply_enabled": False,
    }
    return ToolExecution(
        trace=trace,
        observation={
            "tool_call_id": tool_call_id,
            "name": request.name,
            "status": "approval_required",
            "message": "proposal recorded for user approval; no mutation was executed",
        },
    )


def _terminal_execution(
    *,
    tool_call_id: str,
    name: str,
    risk_level: str,
    status: ToolStatus,
    message: str,
) -> ToolExecution:
    trace = {
        "tool_call_id": tool_call_id,
        "name": name,
        "risk_level": risk_level,
        "status": status,
    }
    return ToolExecution(trace=trace, observation={**trace, "message": message})


def _source_allowed(plan: RetrievalPlan, source_type: str) -> bool:
    return {
        "document": plan.document,
        "memory": plan.memory,
        "profile": plan.profile,
        "relation": plan.relations,
    }.get(source_type, False)


def _single_source_plan(source_type: str) -> RetrievalPlan:
    return RetrievalPlan(
        document=source_type == "document",
        memory=source_type == "memory",
        profile=source_type == "profile",
        relations=source_type == "relation",
        max_expansions=0,
    )
