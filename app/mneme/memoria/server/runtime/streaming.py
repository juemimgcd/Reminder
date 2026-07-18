def phase_event_name(phase: str, status: str) -> str | None:
    return {
        ("retrieve", "started"): "retrieval.started",
        ("generate", "started"): "answer.started",
        ("citations", "completed"): "citation.resolved",
    }.get((phase, status))


def answer_chunks(answer: str, *, size: int = 160) -> list[str]:
    return [answer[index : index + size] for index in range(0, len(answer), size)]
