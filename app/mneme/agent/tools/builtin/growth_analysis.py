from app.mneme.agent.tools.base import ToolMetadata

GROWTH_ANALYSIS_METADATA = ToolMetadata(
    name="growth_analysis",
    description="Analyze recent themes, progress, blockers, and next actions from private memory entries.",
    capability_id="tool:growth_analysis",
    answer_modes=frozenset({"analysis_query"}),
    evidence_type="growth_metrics",
)
