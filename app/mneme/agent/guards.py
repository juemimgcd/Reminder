from dataclasses import dataclass


class AgentRunAbortedError(RuntimeError):
    pass


class AgentRunLimitError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentRunLimits:
    timeout_seconds: float = 90.0
    max_model_loops: int = 4
    max_tool_calls: int = 3
    max_identical_tool_calls: int = 2
