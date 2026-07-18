from dataclasses import dataclass

Labels = tuple[tuple[str, str], ...]
MetricRows = tuple[tuple[Labels, int | float], ...]


def labels(**values: str) -> Labels:
    return tuple(sorted(values.items()))


@dataclass(frozen=True)
class OperationalMetrics:
    inbox_backlog: int
    dead_letters: int
    oldest_inbox_age_seconds: float
    projection_lag_seconds: float
    failed_runs: int
    stale_runs: int
    model_retries: int
    model_fallbacks: int
    governance_actions: dict[str, int]
    answer_runs: MetricRows = ()
    phase_duration_ms_count: MetricRows = ()
    phase_duration_ms_sum: MetricRows = ()
    insufficient_evidence: MetricRows = ()
    answer_tokens: MetricRows = ()
    answer_cost: MetricRows = ()
    role_attempts: MetricRows = ()
    role_duration_ms_sum: MetricRows = ()


def _line(name: str, value: int | float, metric_labels: Labels = ()) -> str:
    suffix = ""
    if metric_labels:
        rendered = ",".join(f'{key}="{value}"' for key, value in metric_labels)
        suffix = f"{{{rendered}}}"
    return f"{name}{suffix} {value}"


def render_metrics(metrics: OperationalMetrics) -> str:
    lines = [
        _line("memory_agent_inbox_backlog", metrics.inbox_backlog),
        _line("memory_agent_dead_letters", metrics.dead_letters),
        _line("memory_agent_oldest_inbox_age_seconds", metrics.oldest_inbox_age_seconds),
        _line("memory_agent_projection_lag_seconds", metrics.projection_lag_seconds),
        _line("memory_agent_failed_runs", metrics.failed_runs),
        _line("memory_agent_stale_runs", metrics.stale_runs),
        _line("memory_agent_model_retries_total", metrics.model_retries),
        _line("memory_agent_model_fallbacks_total", metrics.model_fallbacks),
    ]
    families = (
        ("memory_agent_answer_runs_total", metrics.answer_runs),
        ("memory_agent_answer_phase_duration_ms_count", metrics.phase_duration_ms_count),
        ("memory_agent_answer_phase_duration_ms_sum", metrics.phase_duration_ms_sum),
        ("memory_agent_evidence_insufficient_total", metrics.insufficient_evidence),
        ("memory_agent_answer_tokens_total", metrics.answer_tokens),
        ("memory_agent_answer_cost_total", metrics.answer_cost),
        ("memory_agent_role_attempts_total", metrics.role_attempts),
        ("memory_agent_role_duration_ms_sum", metrics.role_duration_ms_sum),
    )
    for name, rows in families:
        lines.extend(_line(name, value, metric_labels) for metric_labels, value in rows)
    lines.extend(
        _line("memory_agent_governance_actions_total", count, labels(action=action))
        for action, count in sorted(metrics.governance_actions.items())
    )
    return "\n".join(lines) + "\n"
